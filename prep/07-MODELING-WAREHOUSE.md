# Data modelling & warehouse architecture

The JD says *"data warehouses, data warehouse technical architectures"* and
*"architecture principles, guidelines and standards."* At Platform Engineer III this is
where they test whether you're an engineer who writes pipelines or an engineer who
designs platforms.

---

## 1. Layered architecture — the answer to "how do you structure a warehouse?"

```
Landing / Raw      immutable, schema-on-read, exactly as the source gave it,
                   partitioned by ingest date. NEVER transformed. This is your replay tape.
Staging            typed, deduplicated, renamed to house conventions, 1:1 with source objects.
                   Light cleaning only — no business logic.
Core / Integration conformed dimensions + facts. Business logic lives here. Star schema
                   (or Data Vault where auditability/multi-source integration dominates).
Marts / Semantic   consumer-shaped, denormalised, aggregated. One mart per domain or per
                   consuming team. Metrics defined once.
```

**Why the raw layer is non-negotiable:**
> "Raw is immutable and never transformed, because the day a business rule turns out to
> have been wrong for six months, the only thing that saves you is being able to replay.
> If you transform on ingest, that history is gone and the answer to 'can you restate it?'
> is no. It's cheap — GCS and BigQuery long-term storage cost almost nothing next to the
> cost of not being able to."

Mention **medallion (bronze/silver/gold)** as the same idea with Databricks vocabulary,
so you're fluent in either client's language.

---

## 2. Kimball vs Inmon vs Data Vault vs One Big Table

| | Shape | Strength | Cost |
|---|---|---|---|
| **Kimball (dimensional)** | star/snowflake: facts + conformed dims, bottom-up by business process | fast to value, analyst-friendly, performant | conformance discipline required or you get silos |
| **Inmon (CIF)** | 3NF enterprise warehouse → departmental marts, top-down | single version of truth, integrity | slow, expensive, big up-front modelling |
| **Data Vault 2.0** | hubs (business keys) / links (relationships) / satellites (attributes + history) | auditable, non-destructive, parallel loads, absorbs source change | many joins, needs a mart layer on top, steep learning curve |
| **One Big Table / wide denormalised** | one flat or nested table per subject | cheapest to query in columnar stores, no join shuffle | duplication, restatement is expensive, poor for changing dimensions |

**Your position (say it this way):**
> "In BigQuery I default to **Kimball with a pragmatic twist** — star schema in the core
> layer, but in the marts I denormalise dimension attributes onto the fact, or nest them,
> because columnar scan cost beats join shuffle cost and storage is cheap. I'd reach for
> Data Vault when the driver is auditability and integrating many changing sources — a
> regulated client — not because it's fashionable. And I'd deliberately avoid the
> everything-in-one-big-table pattern for anything with slowly changing attributes,
> because restating history in a wide table is painful."

---

## 3. Facts and dimensions

**Fact types:** **transaction** (one row per event, additive), **periodic snapshot**
(state at regular intervals — daily balance), **accumulating snapshot** (one row per
process instance with milestone columns updated as it progresses — order → ship → deliver).
**Factless fact** (an event with no measure — attendance, promotion exposure).

**Measure additivity:** **additive** (revenue — sums across all dims), **semi-additive**
(account balance — sums across accounts, not across time; use last-value over time),
**non-additive** (ratios, percentages — you must re-derive from numerator and denominator,
**never average an average**). Non-additive measures are a favourite interviewer probe:
> "You never store a ratio and sum it. `fct_paid_performance_daily` stores spend, clicks
> and conversions; CPA and ROAS are derived at query time, so any aggregation level is
> correct by construction."

**Grain** — declare it first, before columns. *"The grain of `fct_paid_performance_daily`
is one row per **ad per day**."* An interviewer asking "what's the grain?" is testing
whether you think in models or in tables.

**Surrogate vs natural keys** — surrogate (hash or generated) decouples from source system
change and supports SCD2 (the same natural key appears many times). In BigQuery,
`FARM_FINGERPRINT(CONCAT(...))` or `TO_HEX(MD5(...))` gives a deterministic hash key —
deterministic matters because it makes reloads idempotent and lets you build dimensions in
parallel without a sequence generator.

**SCD types:** 0 (never changes) · **1 overwrite** · **2 history rows with
valid_from/valid_to/is_current** · 3 (previous-value column) · 4 (history table) ·
6 (1+2+3 hybrid). Know 1 and 2 cold; name the others to show range.

**Junk dimension** (roll several low-cardinality flags into one dim), **degenerate
dimension** (an ID like order_number living on the fact with no dim table), **role-playing
dimension** (date dim aliased as order_date/ship_date), **bridge table** (many-to-many,
e.g. a customer in multiple segments, with an allocation factor).

**Late-arriving dimension / early-arriving fact** — a fact arrives before its dimension
row exists. Options: reject to a quarantine table, or **insert an inferred dimension
member** ("unknown" row with the natural key, later updated). Never let the fact join to
NULL silently, because that's where your `-1`/NULL skew comes from.

---

## 4. Data lake / lakehouse / warehouse

- **Warehouse** — structured, schema-on-write, curated, expensive per TB, fast SQL.
- **Lake** — any format, schema-on-read, cheap, needs governance or it becomes a swamp.
- **Lakehouse** — open table formats (**Iceberg**, Delta, Hudi) on object storage giving
  ACID transactions, time travel, schema evolution and partition evolution on top of lake
  economics. On GCP: **BigLake / BigQuery managed Iceberg tables** + **Dataplex** for
  governance.

**"Why would a client want a lakehouse?"**
> "Two reasons that are actually about risk, not technology: **format lock-in** — Iceberg
> in GCS can be read by BigQuery, Spark, Trino and Snowflake, so the warehouse becomes a
> replaceable compute layer — and **cost at the raw tier**, where you keep years of data
> you rarely query. I'd still curate marts into native BigQuery storage, because that's
> where the performance and the governance features are strongest."

---

## 5. ETL vs ELT — have the crisp version ready

> "ETL transforms before loading, which made sense when compute was the scarce, expensive
> resource and the warehouse was a fixed-size appliance you protected. ELT loads raw and
> transforms inside the warehouse, which is right when compute is elastic and separated
> from storage — you keep the raw data for replay, transformations become version-controlled
> SQL that analysts can read and test, and you're not maintaining a separate transformation
> cluster. My default on GCP is ELT into BigQuery with dbt or Dataform.
> I still use ETL-shaped processing — Dataflow before the warehouse — in three cases:
> **PII that must be masked or tokenised before it lands**, **streaming with event-time
> windowing**, and **formats or protocols BigQuery can't read directly**."

That last sentence is the one that makes it a senior answer rather than a slogan.

---

## 6. Designing for the interview: the "principles" answer

If asked *"what principles do you apply when designing a data platform?"*, don't
improvise. Use six:

1. **Idempotency everywhere** — a re-run must be a no-op, not a duplicate.
2. **Immutable raw, derived everything else** — every table is either landed or rebuildable.
3. **Declare the grain before the columns.**
4. **Fail loudly, never silently** — zero rows is a failure, not a success.
5. **Config over code** — onboarding a source is a YAML entry, not a new file.
6. **Cost is a design constraint, not an afterthought** — partition filters, guardrails,
   and knowing what the top 10 queries cost.

Then attach one example to each from your own project. That's a memorable answer and
almost nobody gives one.

---

## 7. Naming & standards (the "guidelines and standards" line in the JD)

- Layer prefixes: `raw_` / `stg_` / `int_` / `dim_` / `fct_` / `agg_` / `rpt_`.
- Snake case everywhere; no reserved words; no abbreviations that aren't in a glossary.
- Dates: `_date` suffix for DATE, `_at` suffix for TIMESTAMP, everything stored in **UTC**,
  converted at the presentation layer only. Timezone bugs are a top-three source of
  "the numbers don't match" tickets.
- Booleans: `is_` / `has_` prefix.
- Every table has: an owner, a description, a declared grain in the description, freshness
  expectation, and a partition + cluster spec.
- **PR review for SQL**, same as code. Models live in git, deploy through CI.
