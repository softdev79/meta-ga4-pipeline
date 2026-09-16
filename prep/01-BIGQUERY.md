# BigQuery — the round-2 deep dive

BigQuery is the centre of gravity for this JD. Expect 10–15 minutes on it minimum.

---

## 1. Architecture — the answer that separates seniors from juniors

**Q: "How does BigQuery actually execute a query?"**

> BigQuery separates storage from compute and connects them with a petabit network.
> Storage is **Colossus**, Google's distributed file system, holding data in
> **Capacitor**, a columnar format. Compute is **Dremel**, which turns a query into a
> multi-level serving tree — a root node that fans the query out to mixers and then to
> leaf nodes, each reading a column shard. Intermediate results move through
> **in-memory shuffle** rather than hitting disk. The unit of compute is a **slot**,
> a virtual CPU; slots are scheduled dynamically across stages, which is why the same
> query can take very different wall-clock times under different concurrency.
> Between them is **Jupiter**, the network — that's what makes decoupling viable at all.

Four nouns: **Colossus, Capacitor, Dremel, Jupiter**, plus **slots** and **shuffle**.
If you say those six words in a coherent sentence you are ahead of most candidates.

**Follow-up: "Why does columnar matter?"** — because you only pay for and read the
columns you touch, and same-type values compress far better adjacent to each other.
This is also exactly why `SELECT *` is the cardinal sin: it defeats the whole design.

---

## 2. Partitioning vs clustering — near-guaranteed question

| | Partitioning | Clustering |
|---|---|---|
| Columns | **1** | up to **4**, **order matters** |
| Types | ingestion time, DATE/TIMESTAMP/DATETIME, INT64 range | most scalar types |
| Limit | **10,000 partitions** per table | no count limit |
| Effect | **physical split** into separate segments — pruning is guaranteed and shown pre-run | **sorts/co-locates rows inside each partition** into blocks |
| Cost estimate | dry-run shows reduced bytes | dry-run shows the **full** scan — savings only known after execution |
| Best for | the time dimension you always filter on | high-cardinality filter/join columns |

**The sentence that wins it:**

> "Partition on the column you filter every single time — almost always a date. Cluster
> on the high-cardinality columns you filter or join on next. The key practical
> difference is that partition pruning is *guaranteed and visible in the dry run*,
> whereas clustering savings are *probabilistic and only visible after the query runs* —
> so I can't use clustering alone to enforce a cost guardrail."

**Common traps they'll test:**
- Clustering column order matters — filtering on the *second* clustering column alone
  gives far less benefit than the first. It's a sort key prefix, like a composite index.
- A partition filter with a **non-constant** expression (`WHERE date_col >= (SELECT MAX(d) FROM t)`)
  may not prune. Use a literal or a scripting variable.
- `require_partition_filter = TRUE` is the guardrail that stops an analyst from
  full-scanning a 40 TB table by accident.
- **`LIMIT` does not reduce bytes billed.** Neither does the cached-results-off case.
  Interviewers love this one.
- BigQuery **auto-reclusters** in the background, for free. You don't maintain it.

---

## 3. Cost control — they will ask, because clients ask

Give a layered answer, cheapest lever first:

**Query-level**
1. Never `SELECT *`; name columns.
2. Constant partition filter; cluster on join/filter keys.
3. `--dry_run` / `maximum_bytes_billed` before anything expensive.
4. `APPROX_COUNT_DISTINCT` instead of `COUNT(DISTINCT)` when ±1% is acceptable.
5. A CTE referenced 3 times is **executed 3 times** — materialise it into a temp table.
6. Filter *before* the join, not after. Push predicates down.
7. Prefer nested/repeated (`ARRAY<STRUCT>`) over a join when the child rows are always
   read with the parent — no shuffle at all.

**Table-level**
8. Partition expiry on staging tables; long-term storage (untouched 90 days) is ~50% cheaper automatically.
9. **Batch loads are free**; streaming inserts are not. Micro-batch when latency allows.
10. Materialised views for repeated aggregates — BigQuery rewrites the query to use them
    automatically and keeps them incrementally fresh.
11. BI Engine for dashboard hotspots.

**Org-level**
12. **On-demand vs editions (capacity)**: on-demand bills $/TB scanned, editions bill
    slot-hours with autoscaling and a baseline. Rule of thumb: predictable, heavy,
    concurrent workloads → editions (cost becomes a ceiling, not a variable);
    spiky/exploratory → on-demand.
13. Custom quotas per project/user, reservations with slot assignments to stop the
    finance team's Looker refresh starving the nightly load.
14. Labels on jobs/datasets → chargeback via `INFORMATION_SCHEMA.JOBS`.

**The pro move:** mention `INFORMATION_SCHEMA.JOBS_BY_PROJECT`.
> "I'd start by querying `INFORMATION_SCHEMA.JOBS_BY_PROJECT` for the last 30 days
> ordered by `total_bytes_billed` — cost problems are almost always a handful of
> queries, not a broad inefficiency. Fix the top 10 and you've usually got 80% of it."

```sql
SELECT user_email, query, total_bytes_billed/POW(1024,4) AS tb, total_slot_ms
FROM `region-us`.INFORMATION_SCHEMA.JOBS_BY_PROJECT
WHERE creation_time > TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 30 DAY)
  AND job_type = 'QUERY' AND state = 'DONE'
ORDER BY total_bytes_billed DESC LIMIT 20;
```

---

## 4. Loading data — know all five paths and when each wins

| Path | Use when | Notes |
|---|---|---|
| **Batch load** (`bq load`, `LoadJob`) | scheduled bulk from GCS | **free**, ACID per job, supports schema autodetect |
| **Storage Write API** | high-throughput streaming, exactly-once needed | replaces legacy `insertAll`; **stream offsets give exactly-once**; cheaper |
| **Legacy streaming inserts** | old code | at-least-once, streaming buffer quirks |
| **External / BigLake tables** | data must stay in GCS/Parquet; federated query | no ingest cost, slower, no partition pruning unless Hive-partitioned; BigLake adds fine-grained security |
| **Data Transfer Service** | SaaS sources (GA4, Ads, S3, Redshift) | zero code, schedule-driven |

**Trap:** rows in the **streaming buffer** are not immediately visible to DML
(`UPDATE`/`DELETE`) and `_PARTITIONTIME` is NULL until flushed. If a candidate has done
real streaming into BQ, they know this. Say it and you sound like you've been burned.

---

## 5. MERGE, idempotency and restatement — your home turf

**Q: "How do you handle late-arriving or restated source data?"**

> Two things have to be true: the load must be **idempotent**, and the window must be
> wide enough to catch restatement. In my Meta Ads pipeline the platform revises
> attributed conversions for up to **28 days** after the fact, so an append-only load
> produces duplicate rows per ad per day and every downstream `SUM` silently inflates.
> I land each run into a staging table and then `MERGE` into the target on the business
> key `(ad_id, date_start)`, and the DAG deliberately re-reads a trailing 28-day window
> every run. That makes a re-run a no-op instead of a corruption, which means I can
> backfill or replay without thinking about it.

```sql
MERGE `mart.stg_meta_ad_insights_daily` T
USING `staging.meta_insights_20260916` S
ON  T.ad_id = S.ad_id AND T.date_start = S.date_start
WHEN MATCHED THEN UPDATE SET spend = S.spend, impressions = S.impressions, ...
WHEN NOT MATCHED THEN INSERT ROW;
```

**Follow-ups to be ready for:**
- *"Why not just DELETE + INSERT for the window?"* — works, and it's cheaper to reason
  about, but it's two statements and non-atomic unless wrapped in a transaction;
  `MERGE` is a single atomic statement. DELETE+INSERT is a perfectly defensible choice
  at high volume where MERGE's join gets expensive.
- *"What's the cost profile of MERGE?"* — it scans both sides. Partition-filter the
  target inside the `ON` clause so you MERGE against 28 partitions, not the whole table.
  This is the single biggest MERGE optimisation and it's worth volunteering.
- *"How do you make the whole DAG idempotent?"* — write to the partition of
  `{{ ds_nodash }}` with `WRITE_TRUNCATE`, never `CURRENT_DATE()`. See `04-COMPOSER-AIRFLOW.md`.

---

## 6. Slowly Changing Dimensions in BigQuery

**SCD Type 1** — overwrite. `MERGE ... WHEN MATCHED THEN UPDATE`.
**SCD Type 2** — history rows with `valid_from` / `valid_to` / `is_current`:

```sql
MERGE `dim.customer` T
USING `staging.customer` S
ON T.customer_id = S.customer_id AND T.is_current = TRUE
WHEN MATCHED AND T.hash_diff != S.hash_diff THEN
  UPDATE SET valid_to = CURRENT_TIMESTAMP(), is_current = FALSE
WHEN NOT MATCHED THEN
  INSERT (customer_id, attrs, valid_from, valid_to, is_current)
  VALUES (S.customer_id, S.attrs, CURRENT_TIMESTAMP(), NULL, TRUE);
```

**The gotcha they may probe:** a single `MERGE` cannot both close the old row *and*
insert the new version for the same key in one pass — BigQuery will reject it or you'll
silently lose the new version. The standard fix is **two statements** (close, then
insert) or a `UNION ALL` trick in the USING clause that duplicates changed rows.
**dbt snapshots exist precisely to hide this.** Saying that is a 5/5 answer.

`hash_diff` = `TO_HEX(MD5(TO_JSON_STRING(...)))` over tracked columns — compares many
columns cheaply and survives column additions gracefully.

---

## 7. Nested and repeated data — the "do you actually know BigQuery" test

BigQuery is not a relational database wearing a hat. `ARRAY<STRUCT>` is first class.

```sql
-- GA4 export: one row per event, params in a repeated STRUCT
SELECT
  event_name,
  (SELECT value.string_value FROM UNNEST(event_params) WHERE key = 'page_location') AS page,
  (SELECT value.int_value    FROM UNNEST(event_params) WHERE key = 'ga_session_id') AS session_id
FROM `project.analytics_123.events_*`
WHERE _TABLE_SUFFIX BETWEEN '20260101' AND '20260131';
```

- `UNNEST` in the `FROM` = **CROSS JOIN** (drops parent rows with empty arrays);
  `LEFT JOIN UNNEST(...)` preserves them. **This is a classic silent-row-loss bug.**
- The correlated-subquery-over-UNNEST form above extracts one key without fanning out.
- `_TABLE_SUFFIX` on wildcard tables prunes the shards — always constrain it.
- **When to nest vs normalise:** nest when the child is always read with the parent
  (order lines, event params). Normalise when the child is queried independently or
  updated at a different cadence.

---

## 8. Performance debugging

**Q: "A query that used to take 2 minutes now takes 40. Walk me through it."**

> I'd open the **execution graph / query plan** and look at stages by slot-ms. Four
> usual suspects, in order:
> 1. **Shuffle/skew** — one stage where max worker time ≫ avg. Usually a join key with
>    a dominant value, often NULL or a `-1` default. Fix: filter the junk key, or split
>    the hot key out and union it back.
> 2. **Data growth without pruning** — someone dropped the partition filter, or the
>    filter stopped being constant. Check `total_bytes_processed` trend in
>    `INFORMATION_SCHEMA.JOBS`.
> 3. **Slot contention** — the query didn't change, the neighbours did. `total_slot_ms`
>    flat but elapsed time up = queuing. Fix with reservations/assignments.
> 4. **A CTE now referenced several times**, or a self-join that materialises twice.
>
> I'd also check whether results used to come from **cache** — a change in a downstream
> tool that appends a comment or timestamp to the SQL silently kills cache hits.

That last point is a genuinely senior observation. Keep it in your pocket.

**Other perf levers:** `JOIN` order — BigQuery will broadcast a small side automatically,
but putting the **largest table first** still helps the optimiser; avoid
self-joins for row comparisons (use window functions); `QUALIFY` instead of a
subquery-wrapped `ROW_NUMBER` filter.

---

## 9. Security — the five layers (they may ask, since IAM is "good to have")

1. **IAM** at org/project/dataset/table/column level.
   Analysts need `bigquery.jobUser` **on the project** (to run jobs, billed there) +
   `bigquery.dataViewer` **on the dataset**. Giving `dataViewer` without `jobUser` is
   the classic "I can see it but can't query it" ticket.
2. **Authorized views / authorized datasets / routines** — the view's service identity
   reads the base table; the user only gets the view. Lets you share a filtered slice
   without granting the underlying table.
3. **Column-level security**: policy tags from Dataplex/Data Catalog taxonomy +
   `Fine-Grained Reader`; **dynamic data masking** returns a hash/nullified value instead
   of denying the query.
4. **Row access policies** — `CREATE ROW ACCESS POLICY ... FILTER USING (region = SESSION_USER()...)`.
5. **CMEK**, **VPC Service Controls** (perimeter — stops exfiltration to another project),
   **Cloud Audit Logs** (`data_access` logs must be explicitly enabled and cost money).

---

## 10. Things that are new-ish and make you sound current

- **BigQuery Editions** (Standard/Enterprise/Enterprise Plus) + autoscaling slots — replaced flat-rate.
- **BigLake / Iceberg tables** — open format in GCS with BigQuery-grade governance;
  the answer to "we want lakehouse, not lock-in."
- **BigQuery ML** — `CREATE MODEL ... OPTIONS(model_type='...')`; trains in-warehouse
  with SQL. Good "AI/ML background" JD nod: forecasting with ARIMA_PLUS, `ML.PREDICT`.
- **Gemini in BigQuery / `AI.GENERATE_TEXT` / `ML.GENERATE_EMBEDDING`** and **vector
  search** (`VECTOR_SEARCH`, vector indexes) — the Gen AI hook in the JD. Even a one-line
  awareness answer differentiates: *"for RAG over warehouse data I'd embed with
  `ML.GENERATE_EMBEDDING` and use a vector index rather than standing up a separate store."*
- **Data Canvas / continuous queries** — BQ can now run a continuously executing query
  over streaming data. Nice-to-know.

---

## 11. Twelve rapid answers to have ready

1. **BigQuery vs Cloud SQL vs Bigtable vs Spanner vs Firestore** — OLAP warehouse /
   relational OLTP (regional, managed MySQL-Postgres) / wide-column NoSQL for
   high-throughput low-latency key lookups and time series / globally-consistent
   horizontally-scaling relational OLTP / document store for app/mobile state.
2. **Slot** — unit of compute, a virtual CPU. Queries queue on slot availability.
3. **Why is my query free?** — cached results (24h, exact SQL, no non-deterministic
   functions, underlying tables unchanged), or metadata-only (`SELECT COUNT(*)` on some
   tables, `INFORMATION_SCHEMA`).
4. **Time travel** — 7 days (configurable 2–7) via `FOR SYSTEM_TIME AS OF`; plus
   **fail-safe** 7 more days recoverable only by Support. *"That's my undo for a bad MERGE."*
5. **Table snapshot vs clone** — snapshot is read-only point-in-time, cheap (delta storage);
   clone is writable, also delta-billed. Both beat `CREATE TABLE AS SELECT` copies.
6. **Views vs materialised views vs table functions** — logical/no storage-no cost benefit;
   precomputed + auto-rewrite + incremental refresh (restrictions: no outer joins,
   limited aggregates); parameterised view (TVF).
7. **`ARRAY_AGG` / `STRUCT` / `UNNEST`** — the denormalisation toolkit.
8. **Scripting & procedures** — `DECLARE`, `BEGIN...EXCEPTION WHEN ERROR THEN`,
   `CREATE PROCEDURE`; useful for multi-statement transactional loads.
9. **Quotas that bite** — 1,500 table-modify operations/day per table (so don't run a
   MERGE per file), 10,000 partitions/table, 6-hour query timeout.
10. **Sharded (`events_20260101`) vs partitioned** — partitioned is strictly better
    (metadata pressure, no wildcard cost); GA4 exports arrive sharded, so you
    consolidate on ingest.
11. **`INFORMATION_SCHEMA`** — JOBS, TABLE_STORAGE, PARTITIONS, COLUMN_FIELD_PATHS.
    The observability layer people forget exists.
12. **Reservation vs on-demand switch** — you can assign different workloads (ETL vs BI)
    to different reservations so one can't starve the other.
