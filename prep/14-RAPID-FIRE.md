# Rapid fire — 150 questions, one-line answers

Cover the right column. If an answer takes more than 15 seconds to recall, flag it and
come back. These are the questions where hesitation costs you, not depth.

## BigQuery (1–35)

1. What is BigQuery? → Serverless, columnar, petabyte-scale OLAP warehouse; storage and compute separated.
2. Storage engine / format / query engine / network? → Colossus / Capacitor / Dremel / Jupiter.
3. What's a slot? → The unit of compute — a virtual CPU. Queries queue on slot availability.
4. Partitioning types? → Ingestion time, DATE/TIMESTAMP/DATETIME column, INT64 range.
5. Max partitions per table? → 10,000. Max clustering columns? 4.
6. Partitioning vs clustering in one line? → Physical split with guaranteed, pre-visible pruning vs sorted co-location whose saving is only known after the run.
7. Does `LIMIT` reduce cost? → **No.** Bytes scanned is set by columns and partitions read.
8. How do you stop a runaway query cost? → `maximum_bytes_billed`, `require_partition_filter`, custom quotas, dry run.
9. On-demand vs editions? → $/TB scanned vs slot-hours with autoscaling; editions for predictable heavy concurrent workloads.
10. Time travel window? → 7 days (configurable 2–7), plus 7 days fail-safe via Support.
11. Snapshot vs clone? → Read-only point-in-time vs writable; both delta-billed.
12. View vs materialised view? → Logical, no storage vs precomputed, incrementally refreshed, auto query-rewrite.
13. When can't you use a materialised view? → Outer joins, some aggregates, non-deterministic functions, UNION.
14. External vs BigLake table? → Both query data in place; BigLake adds fine-grained security and better performance.
15. Cheapest way to load data? → Batch load jobs from GCS — **free**.
16. Exactly-once streaming into BQ? → Storage Write API with stream offsets, or staging + MERGE on a business key.
17. Streaming buffer gotcha? → Rows aren't immediately available to DML; `_PARTITIONTIME` is NULL until flushed.
18. How to dedupe? → `QUALIFY ROW_NUMBER() OVER (PARTITION BY k ORDER BY ts DESC) = 1`.
19. How to upsert? → `MERGE` — and partition-filter the target in the `ON` clause.
20. How to implement SCD2? → `valid_from`/`valid_to`/`is_current` + hash_diff; two statements, or a dbt snapshot.
21. `COUNT(DISTINCT)` too slow? → `APPROX_COUNT_DISTINCT` (HyperLogLog++), ~1% error.
22. Why avoid `SELECT *`? → Columnar storage bills per column read; it defeats the whole design.
23. CTE referenced 3 times? → Executed 3 times. Materialise into a temp table.
24. Nested/repeated types? → `STRUCT` (record) and `ARRAY` (repeated); `UNNEST` to flatten.
25. `UNNEST` in FROM vs `LEFT JOIN UNNEST`? → Cross join (drops empty-array parents) vs preserves them.
26. Wildcard tables? → `events_*` + `_TABLE_SUFFIX` filter — always constrain the suffix.
27. Where do you find query cost history? → `INFORMATION_SCHEMA.JOBS_BY_PROJECT`.
28. Column-level security? → Policy tags from a Dataplex taxonomy + Fine-Grained Reader; dynamic masking as the softer option.
29. Row-level security? → `CREATE ROW ACCESS POLICY ... FILTER USING (...)`.
30. Analyst can see the table but can't query? → Missing `bigquery.jobUser` on the project.
31. Authorized view? → The view's identity reads the base table; the user only gets the view.
32. BigQuery ML? → Train models in SQL: `CREATE MODEL`, `ML.PREDICT`, `ML.EVALUATE`; ARIMA_PLUS, KMEANS, boosted trees.
33. Vector search in BQ? → `ML.GENERATE_EMBEDDING` + `VECTOR_SEARCH` with a vector index.
34. BQ vs Bigtable? → OLAP scans vs low-latency high-throughput key/range lookups on a wide-column store.
35. BQ vs Cloud SQL vs Spanner? → Analytics vs regional managed relational OLTP vs globally-consistent horizontally-scaling relational OLTP.

## Dataflow / Beam (36–60)

36. Beam vs Dataflow? → Programming model vs Google's managed runner for it.
37. The Beam one-liner? → **Batch is streaming over a bounded PCollection.**
38. PCollection? → Distributed immutable dataset; bounded or unbounded.
39. ParDo? → Per-element transform; the map/flatMap primitive, implemented as a DoFn.
40. DoFn lifecycle? → `setup` → `start_bundle` → `process` → `finish_bundle` → `teardown`.
41. Where do you open a BigQuery client in a DoFn? → `setup` — once per worker, not per element.
42. Why prefer Combine over GroupByKey? → Combine lifts a combiner to the map side; GBK shuffles all values.
43. Side input? → A small PCollection broadcast to every worker for lookups. Watch the memory.
44. Side output? → Tagged outputs — how you build a dead-letter path.
45. Window types? → Fixed, sliding, session, global.
46. Sliding window cost trap? → An element belongs to `size/period` windows — 24h/1min = 1,440× state and output.
47. Watermark? → The runner's belief about event-time progress.
48. Trigger? → Decides *when* a window emits a pane — early, on-time, late.
49. Allowed lateness? → How long after the watermark late data is still accepted; then it's dropped.
50. Accumulating vs discarding panes? → Each pane restates the full result vs each pane is a delta.
51. GroupByKey on unbounded data without windowing? → Fails — the global window never closes.
52. Streaming Engine? → Moves shuffle and window state off worker VMs into the service. Always enable it.
53. Dataflow Shuffle? → The batch equivalent — service-side shuffle.
54. FlexRS? → Cheaper batch on preemptible VMs with up to 6h scheduling delay.
55. Drain vs Cancel vs Update? → Flush open windows then stop / stop immediately losing in-flight / in-place code swap with state migration.
56. Classic vs Flex template? → Graph staged at build time with ValueProviders vs Docker image with the graph built at launch.
57. Fusion? → Dataflow merges adjacent steps into one stage; break it with a Reshuffle when one element fans out widely.
58. Hot key fix? → Combine, `withHotKeyFanout`, or salt the key.
59. Dataflow vs Dataproc? → Serverless Beam with event-time semantics vs managed Spark/Hadoop for existing estates.
60. When would you not use Dataflow? → When the transform is expressible in SQL and the data is already landed — ELT in BigQuery is cheaper and simpler.

## Pub/Sub & streaming (61–80)

61. Topic vs subscription? → Fan-out unit vs consumer unit; one message goes to every subscription.
62. Two consumers need the same data? → **Two subscriptions**, not two subscribers on one.
63. Delivery guarantee? → At-least-once by default; exactly-once delivery available per subscription.
64. Ordering? → Off by default; enable ordering and publish with an ordering key.
65. Ordering key downside? → Throughput per key is serialised; a hot key throttles you.
66. Default retention of unacked messages? → 7 days. Topic retention up to 31 days.
67. Replay? → **Seek** to a timestamp or snapshot.
68. Ack deadline? → 10s default, 600s max; client libs auto-extend.
69. Dead-letter topic? → Move a message aside after N delivery attempts. Always configure one.
70. Poison message symptom? → Infinite redelivery that looks like a throughput problem.
71. *The* streaming health metric? → `subscription/oldest_unacked_message_age`.
72. Push vs pull vs StreamingPull? → Pub/Sub calls your HTTPS endpoint / client polls / gRPC long-lived stream.
73. BigQuery subscription? → Pub/Sub writes straight to BigQuery with no Dataflow job at all.
74. Pub/Sub schemas? → Avro/Proto attached to a topic; rejects malformed publishes at the edge.
75. Kafka vs Pub/Sub? → Self-managed, partition-ordered, unbounded retention, huge ecosystem vs serverless, zero-ops, seek-based replay.
76. Event time vs processing time? → When it happened vs when you saw it. Windows are on event time.
77. Lambda vs Kappa architecture? → Parallel batch + speed layers vs a single stream path replayed from the log.
78. CDC on GCP? → **Datastream** (Oracle/MySQL/Postgres/SQL Server → BigQuery/GCS).
79. CDC apply order? → MERGE taking max log sequence number per key, not arrival order.
80. Micro-batch as a compromise? → Pub/Sub → GCS in 5-min windows → free batch load; upgrade to streaming only when latency demands it.

## Airflow / Composer (81–105)

81. What's a DAG? → Tasks + dependencies + a schedule, defined in Python parsed on every scheduler loop.
82. Biggest DAG-file mistake? → Expensive work at module level — it runs on every parse, not every run.
83. `@daily` run firing on the 16th — logical date? → **The 15th.** Airflow runs an interval after it closes.
84. Why `{{ ds }}` not `CURRENT_DATE()`? → Idempotency — the task must produce the same output whenever it runs.
85. Safe default schedule config? → `catchup=False`, `max_active_runs=1`.
86. `start_date = datetime.now()`? → The DAG never becomes eligible. Must be static.
87. XCom? → Small inter-task messages in the metadata DB. Pass a GCS URI, not data.
88. Sensor mode? → `reschedule`, not `poke`, and always set a `timeout`.
89. Modern alternative to sensors? → **Deferrable operators** on the Triggerer — async, frees the worker slot.
90. Trigger rule for cluster teardown? → `all_done`.
91. Pool? → Concurrency limit on a shared resource.
92. Dynamic task mapping? → `.expand()` — fan out tasks at runtime from an upstream list.
93. Datasets / asset scheduling? → Trigger a DAG on data produced by another DAG instead of a cron.
94. SubDagOperator? → Deprecated — use **TaskGroups**.
95. `BigQueryExecuteQueryOperator`? → Deprecated — use **`BigQueryInsertJobOperator`**.
96. Executor in Composer? → Celery (and Kubernetes) on GKE, autoscaling workers.
97. How are DAGs deployed to Composer? → Synced from the environment's GCS bucket; ~1–2 min propagation.
98. Composer cost complaint? → It bills while idle — for a handful of jobs, Cloud Scheduler + Cloud Run or BQ scheduled queries is cheaper.
99. DAG won't run — first four checks? → Paused? static past `start_date`? import errors? scheduler healthy / slots free?
100. Tasks stuck in queued? → Worker saturation, `parallelism`/`worker_concurrency`, exhausted pool, or a poke-sensor army.
101. How do you test DAGs? → DagBag import test in CI asserting zero import errors and required defaults.
102. SLA vs failure alert? → SLA catches "didn't fail, just late" — the failure mode business users actually feel.
103. Secrets in Airflow? → Secret Manager backend, never plaintext Variables, never in the repo.
104. Backfill safely? → Idempotent tasks + `max_active_runs` + a bounded date range; never a year of catchup at once.
105. Airflow alternatives on GCP? → Cloud Workflows, Cloud Scheduler + Cloud Run Jobs, Dataform, Dagster/Prefect.

## SQL (106–125)

106. ROW_NUMBER vs RANK vs DENSE_RANK on 100,100,90? → 1,2,3 / 1,1,3 / 1,1,2.
107. Default window frame with ORDER BY? → `RANGE UNBOUNDED PRECEDING TO CURRENT ROW` — ties collapse. Say `ROWS` if you mean rows.
108. WHERE vs HAVING? → Before vs after aggregation.
109. Query execution order? → FROM → WHERE → GROUP BY → HAVING → SELECT → QUALIFY → ORDER BY → LIMIT.
110. LEFT JOIN turning into INNER JOIN? → A filter on the right table in `WHERE` instead of `ON`.
111. `NOT IN` with a NULL in the subquery? → Returns nothing. Use `NOT EXISTS`.
112. `COUNT(*)` vs `COUNT(col)`? → The second skips NULLs.
113. UNION vs UNION ALL? → Dedupes (shuffle) vs doesn't. Default to UNION ALL.
114. Second highest salary? → `DENSE_RANK() = 2`, and ask whether "second" means distinct value or second row.
115. Gaps and islands pattern? → LAG → flag → running SUM of the flag → GROUP BY.
116. Consecutive-days streak trick? → `date - ROW_NUMBER()` is constant within a streak.
117. Find duplicates? → `GROUP BY key HAVING COUNT(*) > 1`.
118. Find orphan facts? → `LEFT JOIN dim ... WHERE dim.key IS NULL`.
119. Join fan-out risk? → Joining different grains multiplies measures — aggregate to a common grain first.
120. Divide safely? → `SAFE_DIVIDE()` / `NULLIF(denom, 0)`.
121. Fill missing dates? → `GENERATE_DATE_ARRAY` spine + LEFT JOIN.
122. Latest value without a window function? → `ARRAY_AGG(x ORDER BY ts DESC LIMIT 1)[OFFSET(0)]`.
123. Drop a day of data in BigQuery? → Drop the **partition**, don't `DELETE`.
124. DROP vs DELETE vs TRUNCATE? → DDL structure+data / DML filtered rows, rollbackable / DDL all rows, fast.
125. 1NF/2NF/3NF? → Atomic values / no partial dependency on part of a composite key / no transitive dependency.

## Modelling, DQ, governance, ops (126–150)

126. Star vs snowflake? → Denormalised dimensions vs normalised dimension hierarchies (fewer bytes, more joins).
127. Fact types? → Transaction, periodic snapshot, accumulating snapshot, factless.
128. Additive / semi-additive / non-additive? → Sums everywhere / not across time / ratios — re-derive, never average an average.
129. What is grain? → The meaning of one row. Declare it before columns.
130. Surrogate key in BigQuery? → `FARM_FINGERPRINT(CONCAT(...))` — deterministic, so reloads stay idempotent.
131. SCD1 vs SCD2? → Overwrite vs history rows with valid_from/valid_to/is_current.
132. Late-arriving dimension? → Insert an inferred member, or quarantine — never let the fact join to NULL silently.
133. ETL vs ELT? → Transform before vs inside the warehouse; ELT by default, ETL for PII-before-landing, event-time streaming, unreadable formats.
134. Why keep raw immutable? → Replay. The day a business rule turns out to be wrong, it's the only thing that saves you.
135. Medallion layers? → Bronze/silver/gold = raw/staging+core/marts.
136. Six DQ dimensions? → Completeness, uniqueness, validity, accuracy, consistency, timeliness.
137. Gate vs monitor? → Blocking check for "downstream will be wrong" vs alert-only for "this is suspicious".
138. Highest-value single DQ control? → A blocking check between load and marts.
139. What is a data contract? → An enforced agreement on schema, semantics, SLA and ownership, failing in the producer's CI.
140. Dataplex? → Unified governance: catalog, lineage, auto data quality scans, profiling, policy tags.
141. DLP / Sensitive Data Protection? → Discover and classify PII, then mask, bucket or format-preserving tokenise.
142. dbt materialisations? → view, table, incremental, ephemeral.
143. `merge` vs `insert_overwrite` in dbt on BigQuery? → Join on a unique key vs replace whole partitions — cheaper for a partitioned fact.
144. dbt snapshot? → Built-in SCD2 with timestamp or check strategy.
145. Slim CI? → `--select state:modified+ --defer --state <prod manifest>` — build only what changed.
146. Never do what with a service account? → Download a JSON key. Use Workload Identity Federation or impersonation.
147. IAM inheritance? → Additive down the hierarchy; you can't revoke a parent grant at a child (that's deny policies).
148. Terraform state? → Remote GCS backend with versioning; contains secrets in plaintext, never in git.
149. `count` vs `for_each` in Terraform? → `for_each` — `count` reindexes on deletion and destroys the wrong resource.
150. Which metrics would you alert on for a data platform? → Freshness, row-count delta, DQ pass rate — **data-level, not just infrastructure**.
