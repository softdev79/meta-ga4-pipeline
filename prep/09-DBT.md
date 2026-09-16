# dbt (and Dataform) — the "prior ETL tool" requirement

JD: *"Prior Experience in ETL tool such as DBT, Talend Etc."* Expect 5 minutes. If your
hands-on dbt is limited, **say so once and then demonstrate that you understand the model**
— that reads far better than bluffing.

---

## 1. What dbt is, in one paragraph

> "dbt is the **T** in ELT. You write `SELECT` statements as models; dbt handles the DDL,
> builds the dependency graph from `ref()` calls, materialises each model as a view, table,
> incremental table or snapshot, and runs tests and documentation off the same metadata.
> The real value isn't the SQL compilation — it's that transformation becomes **software**:
> version-controlled, code-reviewed, tested in CI, with lineage that's derived rather than
> drawn in a diagram that's six months stale."

**Dataform** is Google's equivalent, now native in BigQuery — same idea, SQLX instead of
Jinja+SQL, no separate infrastructure or licence. *"On a greenfield GCP engagement I'd
seriously consider Dataform because it's free and in-console; I'd choose dbt where the team
already knows it or the client is multi-warehouse, because the ecosystem and the packages
are much deeper."* That's the commercially literate answer.

---

## 2. Core objects

```
models/          .sql files — SELECT statements. ref() and source() build the DAG.
sources.yml      declare raw tables; enables source freshness + lineage from the true origin
snapshots/       SCD Type 2, built in
seeds/           small CSVs versioned in the repo (lookup/mapping tables)
tests/           singular tests (a SQL query that should return zero rows)
macros/          Jinja functions; reusable SQL
analyses/        ad-hoc SQL compiled but not materialised
dbt_project.yml  config: materialisations, tags, schemas, vars, per-folder defaults
packages.yml     dbt_utils, dbt_expectations, codegen, audit_helper
```

**`ref()` is the whole trick:** it resolves to the correct schema per environment **and**
registers the edge in the DAG. Hard-coding a table name breaks both. Say that.

---

## 3. Materialisations — know all four and their trade-offs

| | What it does | Use when |
|---|---|---|
| **view** | `CREATE OR REPLACE VIEW` | cheap, always fresh, light logic; compute cost moves to the reader |
| **table** | full rebuild each run | small-to-medium, complex logic, or the model is read constantly |
| **incremental** | insert/merge only new or changed rows | large fact tables where a full rebuild is too slow or too expensive |
| **ephemeral** | inlined as a CTE, not persisted | small intermediate logic you don't want in the warehouse |

**Incremental in BigQuery — write this:**
```sql
{{ config(
    materialized='incremental',
    incremental_strategy='merge',           -- or 'insert_overwrite' for partitions
    unique_key=['ad_id', 'date_start'],
    partition_by={'field': 'date_start', 'data_type': 'date'},
    cluster_by=['campaign_id'],
    on_schema_change='append_new_columns'
) }}

SELECT * FROM {{ source('meta', 'ad_insights') }}
{% if is_incremental() %}
  WHERE date_start >= DATE_SUB(CURRENT_DATE(), INTERVAL 28 DAY)   -- restatement window
{% endif %}
```

**The senior points to make about this:**
- `is_incremental()` is true only when the model exists *and* it isn't a full refresh.
- **`merge` vs `insert_overwrite`**: merge needs a unique key and does a join;
  `insert_overwrite` **replaces whole partitions** — much cheaper on BigQuery for a
  partitioned fact, and it's the right strategy for a restatement window because you're
  replacing the last 28 partitions wholesale rather than joining against them.
  *This is exactly my pipeline's problem, so I'd use `insert_overwrite` with a dynamic
  partition range.*
- **Incremental models drift.** Late-arriving rows outside the lookback window are never
  picked up, so you need a periodic `--full-refresh` (or a wide-enough window) as a
  reconciliation safety net. Volunteering this is a strong signal — it's the failure mode
  people hit in year two.
- `on_schema_change`: `ignore` / `fail` / `append_new_columns` / `sync_all_columns`.

---

## 4. Tests

**Generic (schema) tests** in YAML: `unique`, `not_null`, `accepted_values`,
`relationships` (referential integrity). Plus packages:
`dbt_utils.expression_is_true`, `dbt_utils.unique_combination_of_columns` (test the grain
of a composite key — very useful), `dbt_expectations.expect_column_values_to_be_between`.

**Singular tests** — a `.sql` file returning rows that *shouldn't* exist:
```sql
-- tests/assert_spend_non_negative.sql
SELECT * FROM {{ ref('fct_paid_performance_daily') }} WHERE spend < 0
```

**Source freshness** — `dbt source freshness` with `warn_after` / `error_after` on a
`loaded_at_field`. This is your "is upstream late" check without writing code.

**Severity**: `error` blocks the build; `warn` reports. `store_failures: true` persists
failing rows to a table so you can triage instead of re-running to see them.

---

## 5. Snapshots (SCD2 for free)

```sql
{% snapshot dim_campaign_snapshot %}
{{ config(target_schema='snapshots', unique_key='campaign_id',
          strategy='timestamp', updated_at='updated_at') }}
SELECT * FROM {{ source('meta', 'campaigns') }}
{% endsnapshot %}
```
`strategy='timestamp'` (needs a reliable `updated_at`) vs `strategy='check'`
(`check_cols` — compares listed columns, use when the source has no reliable timestamp).
dbt maintains `dbt_valid_from` / `dbt_valid_to` / `dbt_scd_id`.

**The catch worth naming:** snapshots only capture state **at the moment they run**. If a
row changes twice between runs you lose the intermediate state. If you need every change,
you need CDC at the source, not snapshots.

---

## 6. Jinja & macros

```sql
{% macro cents_to_currency(col) %}ROUND({{ col }} / 100.0, 2){% endmacro %}

{{ dbt_utils.star(from=ref('stg_orders'), except=['pii_email']) }}
{{ dbt_utils.date_spine(...) }}

-- run a query at compile time to build a dynamic pivot
{% set channels = dbt_utils.get_column_values(ref('stg_spend'), 'channel') %}
{% for c in channels %}
  SUM(IF(channel = '{{ c }}', spend, 0)) AS spend_{{ c }}{% if not loop.last %},{% endif %}
{% endfor %}
```
Also: `{{ var('start_date') }}`, `{{ target.name }}` (dev/prod branching),
**hooks** (`pre_hook` / `post_hook` — e.g. grant statements after a build),
`generate_schema_name` override for environment schemas.

---

## 7. Project structure & deployment

```
staging/     stg_*   1:1 with sources, renaming and casting only, materialized: view
intermediate/ int_*  reusable logic, often ephemeral
marts/       dim_*/fct_*  business-facing, materialized: table/incremental
```
Rules to state: **staging models are the only place that references a source**; models
reference other models only via `ref()`; no model reaches across marts domains.

**CI/CD:**
- `dbt build` = run + test + snapshot + seed in DAG order (better than `run` then `test`,
  because it stops a broken model from feeding its children).
- **Slim CI**: `dbt build --select state:modified+ --defer --state <prod manifest>` —
  build only what changed and its children, deferring everything else to prod. Turns a
  40-minute PR check into three minutes. **Name-dropping Slim CI marks you as someone who
  has run dbt at scale.**
- Orchestrated from Airflow via `BashOperator`/`KubernetesPodOperator`, or **Cosmos**
  (astronomer-cosmos) which renders each dbt model as its own Airflow task — so you get
  per-model retries and visibility instead of one opaque `dbt run` task. Good detail.
- `dbt docs generate` + `--static` → a hosted lineage/documentation site.
- **Exposures** declare downstream dashboards so lineage extends past the warehouse.

---

## 8. Talend / Informatica / Data Fusion — if they ask

> "I've worked primarily code-first — dbt-style SQL and Python — rather than in GUI ETL
> tools, and I'd be straightforward about that. What I'd bring across is that the concepts
> are the same: source connectors, a mapping/transformation layer, a job scheduler, and
> deployment across environments. The differences that matter in practice are **version
> control and code review** — GUI tools store jobs as XML or metadata that diffs badly, so
> peer review and CI are weaker, and the skill is less portable. Where a client already has
> a large Talend or Informatica estate I wouldn't propose replacing it for its own sake;
> I'd wrap it in orchestration and move workloads selectively where there's a payoff."

Honest, non-dismissive, shows architectural judgement. Much better than pretending.

**Data Fusion** specifically (it's in the JD): managed **CDAP**, visual pipeline builder,
100+ connectors, generates Spark that runs on Dataproc under the hood, Wrangler for
interactive prep. **Priced per instance-hour, so it's expensive when idle** — right for
teams that need low-code and many connectors, wrong for a small engineering team that can
write Beam or SQL. Knowing it compiles to Spark on Dataproc is the detail that shows you've
actually looked at it.
