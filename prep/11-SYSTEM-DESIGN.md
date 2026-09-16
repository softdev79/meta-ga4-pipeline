# Scenario & system design

At L2 you'll get one or two of these. They are not looking for the "right" architecture —
they're watching **how you decompose an ambiguous problem**.

---

## The method (use it every time, out loud)

1. **Clarify before designing.** Volume, velocity, latency requirement, who consumes it,
   what happens if it's late vs wrong, budget, existing stack, team skills. *Three
   questions, then move* — asking ten questions reads as stalling.
2. **State the grain and the SLA.** "One row per X per Y, available by 07:00, 99% of days."
3. **Draw the flow left to right**: source → ingest → land → transform → serve, with the
   GCP service on each arrow.
4. **Call out the hard part explicitly** and solve it. Every one of these has one.
5. **Name failure modes and the guardrails**: retries, idempotency, DQ gates, DLQ, alerting.
6. **Cost + a trade-off you consciously accepted.**
7. **What you'd do differently at 100× the volume.**

**The three questions that make you sound senior, whatever the scenario:**
- *"What's the latency requirement, and what decision does it change?"*
- *"What does the business do if this data is wrong vs simply late?"*
- *"Is there an existing estate I should fit into, or is this greenfield?"*

---

## Scenario 1 — Batch: "Ingest data from 50 source systems into BigQuery, daily"

**Clarify:** volumes per source, source types (DB/API/files/SaaS), do they push or do we
pull, is there CDC or only full extracts, PII, SLA.

**Design:**
```
Sources ──► ingestion layer ──► GCS raw (partitioned gs://lake-raw/<src>/dt=YYYY-MM-DD/)
            - RDBMS  → Datastream (CDC) or Dataproc/JDBC extract
            - SaaS   → Data Transfer Service / custom Python connector on Cloud Run
            - Files  → GCS + Storage Transfer Service
                            │
                            ▼
                  BigQuery raw (external or loaded, schema-on-read where volatile)
                            │  batch load = free
                            ▼
                  staging (typed, deduped) ──► core (star schema) ──► marts
                  orchestrated by Composer, transformed with dbt
                            │
                       DQ gates between each layer + dq_results table
```

**The hard part:** *50 sources is a **metadata** problem, not a pipeline problem.*
> "I would not write 50 DAGs. I'd write **one DAG factory driven by a source registry** —
> YAML per source with connection, extract mode, schedule, restatement window, merge keys
> and freshness expectation. Onboarding source 51 becomes a config PR with a code review,
> not a new file. I've run this pattern at roughly 600 generated DAGs; the alternative is
> that a change to retry policy is a 600-file pull request and the drift is guaranteed.
> The cost is parse time, so I keep the factory free of module-level I/O and watch DAG
> parse time as a production metric."

**Failure modes:** a source silently returns zero rows (freshness gate), schema drift
(permissive landing + drift alert), one slow source blocking everything (pools, per-source
DAGs not one monolith), credentials expiring (Secret Manager + alert on auth errors).

**At 100×:** move extract to Dataproc Serverless or parallel Cloud Run jobs, partition the
registry across multiple Composer environments, and consider Datastream for anything
relational rather than scheduled full extracts.

---

## Scenario 2 — Streaming: "Real-time clickstream to dashboards, sub-minute"

**Clarify:** events/sec peak vs average, is ordering required, is exactly-once required or
is approximate fine for dashboards, retention, PII.

**Design:**
```
SDK/gateway ─► Pub/Sub topic (schema attached; ordering key = user_id if needed)
                 ├─► sub A ─► Dataflow (Beam, streaming engine)
                 │             fixed 1-min windows, watermark + allowed lateness 1h
                 │             ├─► BigQuery (Storage Write API) real-time table
                 │             └─► dead-letter table (tagged output)
                 ├─► sub B ─► Cloud Run (operational alerting, <1s)
                 └─► sub C ─► GCS raw archive (Pub/Sub GCS subscription) = replay tape
BigQuery: real-time table (streaming) + daily curated table (batch reprocess from GCS)
Serving: Looker on a materialised view / BI Engine
```

**The hard part: the lambda-vs-kappa question — answer it before they ask.**
> "Streaming gives me speed but I don't want the streamed table to be the system of record,
> because late data and replays make it eventually inconsistent. So I archive raw events to
> GCS from a separate subscription and rebuild a **curated daily table** from that archive
> — the streaming table serves the live dashboard, the batch table is the number finance
> quotes. They're deliberately allowed to differ intraday, and the mart exposes which one
> you're looking at. What I'd avoid is maintaining two full copies of the business logic —
> that's the classic Lambda-architecture tax — so where possible the same dbt model or the
> same Beam pipeline in batch mode produces both."

**Guardrails:** alert on `oldest_unacked_message_age`, DLQ count, and the delta between
the streaming and batch tables — a diverging delta is your early warning that the stream
is dropping data.

---

## Scenario 3 — Debugging: "Half of yesterday's data is missing in BigQuery. The Composer DAG is green. Pub/Sub + Dataflow are in the path. Go."

This exact scenario circulates in GCP interview banks. Structure the answer:

**1. Scope it (5 minutes).**
> "First, is data *missing* or *not visible*? I'd check row counts per partition in
> `INFORMATION_SCHEMA.PARTITIONS` against the source count, and check the streaming buffer —
> rows in the buffer aren't visible to DML and `_PARTITIONTIME` is NULL until flushed.
> And I'd check whether it's uniformly half or a contiguous time range missing — a time
> range points at an outage window, a uniform half points at a partition/key issue."

**2. Walk the path backwards from the sink.**
- **BigQuery**: insert errors table, `INFORMATION_SCHEMA.JOBS` for failed load jobs,
  quota errors (1,500 table modifications/day).
- **Dataflow**: job logs, **elements dropped due to lateness** counter (if allowed lateness
  is an hour and the source was down for two, the replayed events were *correctly*
  discarded — a real and commonly missed root cause), dead-letter sink contents, worker
  restarts, system lag during the window.
- **Pub/Sub**: backlog and `oldest_unacked_message_age` around the window, DLQ topic count,
  subscription expiry, ack deadline expiry rate.
- **Composer**: was the task green but the extract window wrong? A `CURRENT_DATE()` in the
  SQL instead of `{{ ds }}` produces exactly "half a day missing" on a delayed run.
- **Source**: did the producer actually send it? Compare against the source's own counts.

**3. Recover.**
> "If the raw events are still in the Pub/Sub retention window I **seek the subscription**
> back to a timestamp and reprocess. If they've aged out, I replay from the GCS archive
> through the batch path. Either way, recovery only works because the sink is idempotent —
> MERGE on a business key or partition overwrite — so re-processing is a no-op on the rows
> that did land. If the sink weren't idempotent, I'd be choosing between missing data and
> duplicated data, which is the worst place to be at 9 a.m."

**4. Prevent.**
> "The systemic fix isn't the root cause fix — it's that the DAG was green while the data
> was wrong. I'd add a reconciliation check between source count and landed count as a
> **blocking gate** before the marts build, and an alert on the streaming-vs-batch delta.
> Green with missing data is the failure mode that costs clients real money because
> dashboards keep rendering and nobody notices for a week."

**Then the honest closing line:** *"And I'd write it up — what failed, what detected it,
what didn't detect it, and the one control that would have caught it sooner."*

---

## Scenario 4 — Migration: "On-prem Hadoop/Teradata → GCP"

**Why:** capex→opex, fixed cluster capacity blocking month-end, end-of-life support,
ops burden, new ML/streaming needs the old platform can't serve.

**How (say it as six phases):**
1. **Assess** — inventory jobs, tables, lineage and *actual* usage (most estates have 30–50%
   of tables nobody has queried in a year; don't migrate those).
2. **Wave plan** — group by business domain and dependency, lowest-risk wave first to build
   confidence and prove the pattern.
3. **Move data** — `distcp` / Storage Transfer Service for bulk, **Datastream CDC** for
   the delta so you can keep syncing while you rebuild.
4. **Move compute** — lift-and-shift Hive/Spark to **Dataproc** first (fast, low risk),
   then selectively re-platform the high-value or high-cost jobs to BigQuery/Dataflow.
   *"Re-platforming everything up front is how migrations slip a year."*
5. **Parallel run + reconciliation** — both systems live, compare row counts, checksums and
   **business aggregates**, not just counts. This is where HiveQL vs BigQuery SQL semantic
   drift gets caught (NULL handling, implicit casts, division).
6. **Cutover, then optimise and govern** — partitioning, clustering, cost guardrails,
   policy tags, decommission.

**Challenges to name with fixes:** 2M small files → compaction on landing; one tenant =
70% of volume → skew handling; `SELECT *` cost shock on day one →
`require_partition_filter` + `maximum_bytes_billed` + authorized views; stored procedures
and UDFs with no direct equivalent; and the non-technical one — **the team's skills**,
which is why coaching is in this JD.

---

## Scenario 5 — "Design a data platform for a retail client from scratch"

Give the reference architecture, then the sequencing:
```
Ingest:    Datastream (OLTP CDC) · Pub/Sub (events) · Transfer Service (SaaS/files)
Land:      GCS raw (immutable, dt-partitioned) + BigQuery raw
Transform: dbt/Dataform in BigQuery (ELT default) · Dataflow where event-time or PII-before-landing
Orchestrate: Composer, metadata-driven DAG factory
Serve:     BigQuery marts · Looker semantic layer · BI Engine · Analytics Hub for partners
Govern:    Dataplex (catalog, lineage, DQ scans, policy tags) · DLP · audit log export
Platform:  Terraform · Cloud Build · Secret Manager · Workload Identity · Monitoring/SLOs
```
**Then the sequencing sentence, which is what actually impresses:**
> "I wouldn't build all of that first. I'd pick the one business question with the clearest
> owner, build the thin vertical slice end to end — ingest, model, one dashboard, one DQ
> gate — and get it into someone's hands in a few weeks. Platforms that are built
> horizontally, all ingestion first, tend to be six months in before anyone can tell
> whether the model is right."

---

## Scenario 6 — "This BigQuery bill doubled. Find out why."

> "`INFORMATION_SCHEMA.JOBS_BY_PROJECT` for the last 60 days, grouped by day and by
> `user_email`/label, ordered by `total_bytes_billed`. Cost problems are almost always a
> handful of queries, not diffuse inefficiency. The usual culprits: a new dashboard
> refreshing hourly without a materialised view; someone dropped a partition filter or made
> it non-constant so pruning stopped; a scheduled query with `SELECT *` over a wildcard
> table; a MERGE scanning the whole target because the ON clause has no partition
> predicate; or streaming inserts replacing a batch load, which is free.
> Immediate guardrails: `maximum_bytes_billed` at project level, `require_partition_filter`
> on the big tables, custom quotas per user. Then the structural fixes — materialised
> views, BI Engine for the hot dashboards, and evaluating whether the workload is
> predictable enough for editions/slot reservations, which converts cost from a variable
> into a ceiling."
