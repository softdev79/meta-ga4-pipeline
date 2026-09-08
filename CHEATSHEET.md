# One-page cheat sheet — read this in the cab

## The 12 answers you must not fumble

**1. Spark architecture** — Driver (SparkSession, DAGScheduler → stages, TaskScheduler → tasks, Catalyst+Tungsten)
→ Cluster Manager (YARN on Dataproc / K8s) → Executors (JVM, task slots, block manager).
**Application → Job (per action) → Stage (split at every shuffle) → Task (per partition).**

**2. RDD vs DataFrame vs Dataset** — objects/no optimiser · rows+schema/Catalyst+Tungsten/runtime-typed ·
typed JVM objects, **Scala/Java only**. DataFrame = `Dataset[Row]`. Default to DataFrame; drop to RDD only for
custom partitioners or heavy per-partition setup.

**3. Transformations vs actions** — lazy vs triggering. Narrow (`map`, `filter`, `coalesce`) = same stage.
Wide (`groupBy`, `join`, `distinct`, `repartition`, `orderBy`) = **shuffle** = new stage.

**4. `cache()` vs `persist()`** — `cache()` = `persist(MEMORY_AND_DISK)` for DataFrames. Use when a DF feeds
**≥2 actions**. Don't when used once or far bigger than memory. Always `unpersist()`. Lazy until an action.
`checkpoint()` **truncates lineage**; `cache` keeps it.

**5. Lineage & fault tolerance** — RDDs are immutable and record their deterministic transformations, so a lost
partition is **recomputed** from lineage instead of restored from a replica. Hadoop recovers via **3× HDFS block
replication**; Spark via **recomputation** — cheaper storage, but expensive with long chains → checkpoint.

**6. `groupBy` vs `groupByKey`** — `groupByKey` shuffles all values → OOM. `reduceByKey`/`aggregateByKey` use a
**map-side combiner**. DataFrame `groupBy().agg()` already does partial aggregation — it is *not* the bad one.

**7. ROW_NUMBER / RANK / DENSE_RANK** — on `100,100,90`: `1,2,3` · `1,1,3` · `1,1,2`.
Dedupe / competition ranking / **Nth distinct value**. `ROW_NUMBER` needs a tiebreaker to be deterministic.

**8. DROP vs DELETE vs TRUNCATE** — DDL/DML/DDL · structure+data / filtered rows / all rows ·
rollback: only `DELETE` · `TRUNCATE` resets identity, fires no triggers, is fast.
BigQuery: `TRUNCATE` free, `DELETE` costs bytes, dropping a day = dropping a **partition**.

**9. Hive partitioning vs bucketing** — directories on a **low**-cardinality column (pruning) vs
`hash(col) % N` files on a **high**-cardinality column (bucket joins, even sizes).
No hard limit on buckets — size each to **128 MB–1 GB**, power of 2; both sides need the same column & count.

**10. BigQuery partitioning vs clustering** — **1** column, time/int-range, max **4 000** partitions, guaranteed
pruning · up to **4** columns, order matters, sorts within the partition, savings only known after the query.
`require_partition_filter=TRUE` + `maximum_bytes_billed` are the guardrails. **`LIMIT` does not reduce bytes scanned.**

**11. Event time vs processing time** — windows are on **event time**; the **watermark** estimates event-time
progress; **triggers** decide when a window emits (early / on-time / late); **allowed lateness** bounds how long
late data is accepted; past that → dead-letter, never silently drop.

**12. Exactly-once into BigQuery** — Pub/Sub is at-least-once; Dataflow gives exactly-once *processing*;
end-to-end needs an **idempotent sink**: Storage Write API with offsets, or staging + `MERGE` on a business key.

---

## Skew playbook (say it in this order)
1. **Prove it** — Spark UI straggler task, or `groupBy(key).count()`.
2. **AQE**: `spark.sql.adaptive.enabled` + `adaptive.skewJoin.enabled` — free, splits the fat partition.
3. **Broadcast** the small side (`broadcast(df)`) — no shuffle at all.
4. **Salt**: random salt on the fact + **explode the dimension across every salt value**, join on `(key, salt)`.
   *Forgetting to replicate the dimension silently drops rows.*
5. **Isolate** the hot key, broadcast-join it, `union` back.
6. **Ask if the key is junk** — NULL/`-1`/`''` defaults cause half of real "skew".

## OOM / GC triage
`executor.memory` (heap) vs `memoryOverhead` (off-heap: shuffle, netty, Python workers) → 3–5 cores per executor →
`spark.sql.shuffle.partitions` / `files.maxPartitionBytes` → stop `collect()`ing to the driver →
check spill & skew in the UI **before** touching GC flags.

## BigQuery cost levers
No `SELECT *` · partition filter with a constant · cluster on filter/join columns · `--dry_run` ·
`APPROX_COUNT_DISTINCT` · materialised views + BI Engine · batch load (free) over streaming inserts ·
nested/repeated instead of joins · custom quotas + `maximum_bytes_billed` · repeated CTEs re-execute → temp table.

## BigQuery security — 5 layers
IAM (dataset/table/column; `jobUser` + `dataViewer` for analysts) → authorized views/datasets →
column-level policy tags (Dataplex/Data Catalog) + dynamic masking → row access policies →
CMEK + VPC Service Controls + audit logs.

## Airflow idempotency
Write to the partition of **`{{ ds_nodash }}`** with `WRITE_TRUNCATE`, never `CURRENT_DATE()`.
Sensors in `mode='reschedule'` with a `timeout`. `catchup=False` + `max_active_runs=1`.
A DQ gate between load and marts. Ephemeral Dataproc: create → submit → delete with `trigger_rule='all_done'`.

## Shell one-liners they ask for
```bash
sed '$d' f.txt                      # delete last line     (head -n -1 f.txt)
sed '1d' f.txt                      # delete header        (tail -n +2 f.txt)
cut -d',' -f1,3 f.csv               # extract columns      (awk -F',' '{print $1","$3}')
grep ' ERROR ' app.log | awk -F'[][]' '{print $2}' | sort | uniq -c | sort -rn | head -5
gcloud storage cp -r /exports gs://lake-raw/orders/dt=2024-01-15/
hadoop distcp -m 50 hdfs://nn1:8020/user/hive/warehouse/sales gs://lake-raw/sales
```

## SQL patterns (write from memory)
```sql
-- dedupe / latest version
QUALIFY ROW_NUMBER() OVER (PARTITION BY id ORDER BY updated_at DESC) = 1
-- top-N per group
DENSE_RANK() OVER (PARTITION BY g ORDER BY x DESC) <= 3
-- running total
SUM(v) OVER (ORDER BY d ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW)
-- gaps & islands / sessionisation
LAG(ts) OVER w  ->  new-session flag  ->  SUM(flag) OVER w  ->  GROUP BY (key, session_no)
-- anti-join (find orphans)
FROM a LEFT JOIN b USING (k) WHERE b.k IS NULL
```
Trap: a `WHERE` filter on the right table turns a `LEFT JOIN` into an `INNER JOIN` — put it in `ON`.
Default window frame with `ORDER BY` and no frame clause is `RANGE`, not `ROWS`.

## The migration story (3 min, with numbers)
**Why:** capex→opex · fixed YARN capacity blocking month-end · CDH end-of-life · ops burden · new ML/streaming needs.
**How:** assess → wave plan → `distcp`/Transfer Service + Datastream CDC → **lift-and-shift Hive/Spark to Dataproc**,
then selectively re-platform to BigQuery/Dataflow → **parallel run + reconciliation (counts, checksums, business
aggregates)** → cutover → optimise & govern.
**Challenges:** 2M small files → compaction; one merchant = 70 % of volume → AQE + broadcast; `SELECT *` cost shock
→ `require_partition_filter` + authorized views; HiveQL vs BigQuery SQL semantics drift caught by the parallel run.

## Answer template that scores a 3
**Define** → **Contrast with the alternative** → **Example from your project, with a number** →
**Trade-off / when you wouldn't**.

## Ask them
Migration engagement or steady-state platform? · Java-first or Python-first? · BigQuery ELT or Dataproc ETL? ·
How is data quality enforced? · What pages the on-call most often?
