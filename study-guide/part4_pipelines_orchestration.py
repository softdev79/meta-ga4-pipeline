"""Chapters: pipeline patterns; Airflow orchestration; dbt."""

from content_helpers import c, ch, h2, h3, p, ul, ol, code, co, tbl, cards, flow

BLOCKS = [
    # ------------------------------------------------------------------ patterns
    ch("Building Reliable Pipelines: Core Patterns",
       "The design patterns that make pipelines safe to re-run, cheap to operate and easy to "
       "debug. You've seen what happens without them at 3 a.m."),
    h2("Idempotency: the number one principle"),
    p("A pipeline is <b>idempotent</b> if running it once or five times for the same input "
      "period produces the same result. Then reruns, retries and backfills are safe, and "
      "'Force OK and pray' is never needed."),
    tbl([
        ["Non-idempotent (dangerous)", "Idempotent (safe)"],
        ["INSERT INTO sales SELECT ... (every rerun duplicates rows)",
         "DELETE the target partition, then INSERT, in one transaction"],
        ["Append files with random names", "Overwrite the partition dt=2024-03-10/"],
        ["Use NOW() / CURRENT_DATE inside logic",
         "Use the run's logical date passed in as a parameter"],
        ["Increment counters", "MERGE on a business key"],
    ], [1, 1]),
    code("sql", r"""
-- Partition overwrite pattern (run_date is a parameter, never CURRENT_DATE)
BEGIN;
DELETE FROM mart.daily_sales WHERE sales_date = :run_date;
INSERT INTO mart.daily_sales (sales_date, store_id, revenue, orders)
SELECT CAST(order_ts AS DATE), store_id, SUM(amount), COUNT(*)
FROM   silver.orders
WHERE  CAST(order_ts AS DATE) = :run_date
GROUP  BY 1, 2;
COMMIT;
""", "idempotent daily load"),
    co("bridge", "Think of %%ODATE. A Control-M job ordered for 20240310 that you re-run on "
                 "the 12th must still process the 10th's data. Airflow's <b>logical date</b> is "
                 "the same idea, and passing it in instead of reading the clock is what makes "
                 "pipelines idempotent and backfillable."),
    h2("Full vs incremental loads"),
    tbl([
        ["Strategy", "How", "Pros", "Cons"],
        ["Full refresh", "Reload everything each run", "Simple, always consistent",
         "Slow and costly at scale"],
        ["Incremental (watermark)", "Load rows where updated_at > last high-water mark",
         "Fast, cheap", "Misses hard deletes; needs a reliable updated_at"],
        ["Incremental (partition)", "Reprocess only the run date's partition(s)",
         "Idempotent, easy backfills", "Late data needs a lookback window"],
        ["CDC (change data capture)", "Read the database's transaction log",
         "Captures inserts, updates AND deletes, low source load", "More infrastructure "
                                                                   "(Debezium, Kafka)"],
    ], [1.3, 1.9, 1.4, 1.6]),
    code("python", r'''
from datetime import datetime, timezone

import psycopg   # psycopg 3


def incremental_extract(src_dsn: str, wh_dsn: str, table: str) -> int:
    with psycopg.connect(wh_dsn) as wh:
        row = wh.execute(
            "SELECT last_value FROM etl.watermarks WHERE table_name = %s", (table,)
        ).fetchone()
        last = row[0] if row else datetime(1970, 1, 1, tzinfo=timezone.utc)

        with psycopg.connect(src_dsn) as src:
            rows = src.execute(
                f"SELECT * FROM {table} WHERE updated_at > %s ORDER BY updated_at",
                (last,),
            ).fetchall()
        if not rows:
            return 0

        load_into_staging(wh, table, rows)          # e.g. COPY into staging.<table>
        merge_staging_into_target(wh, table)        # MERGE on primary key (idempotent)
        new_mark = max(r.updated_at for r in rows)  # assumes a row_factory with attributes
        wh.execute(
            """INSERT INTO etl.watermarks (table_name, last_value) VALUES (%s, %s)
               ON CONFLICT (table_name) DO UPDATE SET last_value = EXCLUDED.last_value""",
            (table, new_mark),
        )
        # all three writes commit together when the 'with' block exits
    return len(rows)
''', "watermark-based incremental extract"),
    co("warn", ["Advance the watermark <b>only after</b> the load commits, in the same "
                "transaction if possible. Otherwise a crash between the two silently loses data.",
                "Use <b>&gt;</b> with a small overlap (e.g. last - 5 minutes) plus MERGE to "
                "tolerate clock skew and long-running source transactions."]),
    h2("Change Data Capture (CDC)"),
    flow([
        ("Postgres / MySQL", "WAL / binlog"),
        ("Debezium", "Kafka Connect source"),
        ("Kafka topic", "insert/update/delete events"),
        ("Sink", "S3 / Snowflake / BigQuery"),
        ("MERGE", "apply ops in order by LSN"),
    ]),
    p("Log-based CDC reads the database's write-ahead log. Each event carries "
      "<font face='Mono'>op</font> (c/u/d), <font face='Mono'>before</font> and "
      "<font face='Mono'>after</font> images and a log position. Managed options include AWS "
      "DMS, GCP Datastream, Fivetran and Airbyte."),
    h2("Backfills, late data and reprocessing"),
    ul("<b>Backfill</b>: run the pipeline for historical intervals (e.g. after fixing a bug or "
       "adding a column). Only safe if tasks are idempotent and parameterised by date.",
       "<b>Late-arriving data</b>: events that show up after their period was processed. "
       "Handle them with a <b>lookback window</b> (reprocess the last N days each run) or "
       "event-time watermarks in streaming.",
       "<b>Late-arriving dimensions</b>: a fact arrives before its customer row exists. Insert "
       "an 'unknown' / inferred member row (key -1) and update it when the dimension arrives."),
    h2("Schema evolution, bad records and retries"),
    ul("<b>Schema drift</b>: sources add, remove or retype columns. Detect it (compare against "
       "the expected schema), allow additive changes automatically, and alert on breaking ones. "
       "<b>Data contracts</b> make the expected schema explicit and owned by the producer.",
       "<b>Dead-letter queue (DLQ)</b>: route records that fail parsing or validation to a "
       "quarantine table or topic with the error reason, instead of failing the whole batch or "
       "silently dropping them.",
       "<b>Retries</b>: retry transient errors (network, throttling) with backoff. Don't retry "
       "deterministic errors (bad SQL, schema mismatch); fail fast and alert.",
       "<b>Audit columns</b>: add _loaded_at, _source_file and _batch_id to every raw row for "
       "traceability. This is your data 'sysout'."),
    cards("Pipeline patterns", [
        ("What does idempotent mean for a pipeline?",
         "Running it multiple times for the same input/interval gives the same final state: no "
         "duplicates, no drift. It makes retries and backfills safe."),
        ("Two common ways to make a load idempotent?",
         "1) Delete-then-insert (or overwrite) the target partition for the run date in one "
         "transaction. 2) MERGE/upsert on a business key."),
        ("Why shouldn't pipeline logic use CURRENT_DATE?",
         "Reruns and backfills would process the wrong period. Pass the logical/run date in as a "
         "parameter instead."),
        ("Watermark incremental load: main weakness?",
         "It can't see hard deletes and depends on a trustworthy updated_at. Late commits can be "
         "missed without an overlap window."),
        ("What is CDC and why is log-based CDC preferred?",
         "Change Data Capture streams inserts, updates and deletes. Log-based CDC (reading the "
         "WAL/binlog, e.g. Debezium) captures deletes, has minimal source load and preserves "
         "order."),
        ("What is a backfill?",
         "Running a pipeline for past intervals to populate or correct historical data. It "
         "requires idempotent, date-parameterised tasks."),
        ("How do you handle late-arriving facts?",
         "Reprocess a lookback window (e.g. last 3 days) each run, or use event-time "
         "windows/watermarks in streaming; MERGE to avoid duplicates."),
        ("What is a dead-letter queue?",
         "A place (table, topic, bucket) where invalid records are sent along with error "
         "details, so the good records keep flowing and the bad ones can be inspected and "
         "replayed."),
        ("What is a data contract?",
         "An explicit, versioned agreement between data producer and consumer about schema, "
         "semantics, quality and SLAs, enforced in CI or at ingestion."),
        ("Late-arriving dimension: what do you do?",
         "Load the fact with an inferred/'unknown' dimension member (e.g. key -1 or a "
         "placeholder row), then update it when the real dimension record arrives."),
    ]),

    # ------------------------------------------------------------------ airflow
    ch("Orchestration with Apache Airflow",
       "This is your home turf. Learn the Python API and the vocabulary, and you'll be "
       "ahead of most candidates."),
    h2("Architecture"),
    tbl([
        ["Component", "Role", "Control-M analogue"],
        ["Scheduler", "Parses DAGs, decides what runs when, queues tasks",
         "Control-M Server (scheduling engine)"],
        ["Executor", "How tasks run: Local, Celery, Kubernetes",
         "Agent dispatch model"],
        ["Workers", "Processes or pods that execute tasks", "Agents / agentless hosts"],
        ["Metadata DB", "Postgres/MySQL: DAG runs, task states, history",
         "Control-M/EM database"],
        ["Webserver / API server", "UI: grid, graph, logs, triggers, clear/mark",
         "Control-M Web / Monitoring domain"],
        ["DAG folder / bundles", "Python files defining workflows",
         "Job definitions (Planning domain / Automation API JSON)"],
        ["Triggerer", "Runs deferrable (async) sensors efficiently", "(no direct equivalent)"],
    ], [1.2, 2.4, 2]),
    h2("Side by side: a Control-M flow and the same flow in Airflow"),
    code("json", r"""
{
  "DWH_ORDERS_DAILY": {
    "Type": "Folder",
    "ControlmServer": "ctm-prod",
    "Application": "DWH",
    "RunAs": "etluser",
    "When": { "WeekDays": ["MON","TUE","WED","THU","FRI"], "FromTime": "0200" },

    "WAIT_ORDERS_FILE": {
      "Type": "Job:FileWatcher:Create",
      "Path": "/data/in/orders_%%ODATE.csv",
      "Host": "etl-agent-01"
    },
    "LOAD_ORDERS": {
      "Type": "Job:Command",
      "Command": "python /opt/etl/load_orders.py --date %%ODATE",
      "Host": "etl-agent-01",
      "DB_SLOT": { "Type": "Resource:Semaphore", "Quantity": "1" }
    },
    "BUILD_MART": {
      "Type": "Job:Command",
      "Command": "dbt build --select marts.sales --vars '{run_date: %%ODATE}'",
      "Host": "etl-agent-01"
    },
    "flow": { "Type": "Flow", "Sequence": ["WAIT_ORDERS_FILE", "LOAD_ORDERS", "BUILD_MART"] }
  }
}
""", "Control-M Automation API (jobs-as-code), simplified"),
    code("python", r"""
from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.bash import BashOperator
from airflow.sensors.filesystem import FileSensor

default_args = {
    "owner": "data-eng",
    "retries": 3,                                   # like Control-M rerun settings
    "retry_delay": timedelta(minutes=5),
    "retry_exponential_backoff": True,
    "email_on_failure": True,
    "email": ["dataops@example.com"],
}

with DAG(
    dag_id="dwh_orders_daily",                      # = Folder
    start_date=datetime(2024, 1, 1),
    schedule="0 2 * * 1-5",                         # = When: weekdays, 02:00
    catchup=False,                                  # don't auto-run missed past intervals
    max_active_runs=1,                              # = exclusive control resource
    default_args=default_args,
    tags=["dwh", "orders"],
) as dag:

    wait_orders_file = FileSensor(                  # = File Watcher job
        task_id="wait_orders_file",
        filepath="/data/in/orders_{{ ds_nodash }}.csv",   # {{ ds_nodash }} ~ %%ODATE
        poke_interval=60,
        timeout=60 * 60 * 3,
        mode="reschedule",                          # free the worker slot between pokes
    )

    load_orders = BashOperator(
        task_id="load_orders",
        bash_command="python /opt/etl/load_orders.py --date {{ ds }}",
        pool="dwh_db",                              # = quantitative resource (semaphore)
        execution_timeout=timedelta(hours=1),
    )

    build_mart = BashOperator(
        task_id="build_mart",
        bash_command="dbt build --select marts.sales --vars '{run_date: {{ ds }}}'",
    )

    wait_orders_file >> load_orders >> build_mart   # = Flow / in-out conditions
""", "the same flow as an Airflow DAG"),
    co("note", ["<b>Airflow 3</b> (released 2025) is now common. Key changes: DAG authoring "
                "imports move to <font face='Mono'>airflow.sdk</font>; core operators such as "
                "BashOperator and FileSensor live in the <font face='Mono'>"
                "apache-airflow-providers-standard</font> package; <font face='Mono'>"
                "execution_date</font> is gone (use logical_date / data interval); SubDAGs and "
                "the old SLA feature were removed; there is DAG versioning and a new React UI. "
                "The concepts in this chapter are the same in both versions.",
                "Check which version the job description mentions and read the matching docs."]),
    h2("TaskFlow API (modern Pythonic style)"),
    code("python", r"""
import pendulum
from airflow.decorators import dag, task     # Airflow 3: from airflow.sdk import dag, task


@dag(schedule="@daily", start_date=pendulum.datetime(2024, 1, 1, tz="UTC"), catchup=False)
def orders_api_pipeline():

    @task(retries=3)
    def extract(ds=None) -> str:
        rows = fetch_orders(updated_on=ds)            # your API client from Chapter 5
        path = f"s3://lake/bronze/orders/dt={ds}/orders.jsonl"
        write_jsonl(path, rows)
        return path                                    # passed via XCom (small values only!)

    @task
    def validate(path: str) -> str:
        n = count_rows(path)
        if n == 0:
            raise ValueError(f"no rows in {path}")     # fail loudly, don't load empty data
        return path

    @task
    def load(path: str) -> None:
        copy_into_warehouse(path, table="raw.orders")

    load(validate(extract()))                           # dependencies inferred from data flow


orders_api_pipeline()
""", "TaskFlow DAG"),
    h2("Key concepts checklist"),
    tbl([
        ["Concept", "Meaning", "Watch out for"],
        ["DAG run & logical date", "One execution for one data interval",
         "A daily run for 10 March starts after the interval ends, i.e. on 11 March"],
        ["catchup", "Auto-create runs for missed intervals since start_date",
         "Defaults to False in Airflow 3 (True in 2.x); set it explicitly"],
        ["Backfill", "Explicitly run historical intervals (CLI/UI)", "Tasks must be idempotent"],
        ["Operators", "Templates for a unit of work (Bash, Python, SQL, KubernetesPod)",
         "Prefer provider operators over shell scripts for cloud services"],
        ["Hooks / Connections", "Reusable clients + stored credentials",
         "Never hard-code credentials; use a secrets backend"],
        ["Sensors", "Wait for a condition (file, partition, external task)",
         "Use reschedule mode or deferrable sensors"],
        ["XCom", "Pass small metadata between tasks", "Not for datasets; pass paths, not data"],
        ["Pools", "Limit concurrent tasks hitting a resource", "= Control-M quantitative "
                                                               "resource"],
        ["Trigger rules", "all_success (default), all_done, one_failed, none_failed...",
         "Use all_done for cleanup / notification tasks"],
        ["Datasets / Assets", "Data-aware scheduling: run when upstream data updates",
         "= Control-M cross-folder conditions"],
        ["Dynamic task mapping", "task.expand(x=list) creates N parallel tasks at runtime",
         "Great for 'one task per file/table'"],
    ], [1.3, 2.3, 2.4]),
    h3("Data-aware scheduling across DAGs"),
    code("python", r"""
from airflow.datasets import Dataset      # Airflow 3: from airflow.sdk import Asset

orders_ready = Dataset("s3://lake/silver/orders")

# Producer DAG: a task declares that it updates the dataset
load = BashOperator(task_id="load", bash_command="...", outlets=[orders_ready])

# Consumer DAG: runs whenever the dataset is updated (like a cross-folder condition)
with DAG("sales_mart", schedule=[orders_ready], start_date=datetime(2024, 1, 1)) as dag:
    ...
""", "Datasets (Assets in Airflow 3)"),
    h2("Best practices interviewers look for"),
    ul("<b>Keep DAG files light</b>: no heavy work or DB calls at the top level. The scheduler "
       "re-parses files constantly.",
       "<b>Airflow orchestrates; it doesn't process</b>. Push heavy compute to the warehouse, "
       "Spark or Kubernetes pods, not the Airflow worker.",
       "<b>Atomic, idempotent tasks</b> parameterised by the logical date.",
       "<b>Templated SQL files</b> and config-driven DAG generation for many similar pipelines.",
       "<b>Alerting</b> via on_failure_callback to Slack/PagerDuty, plus run-duration and "
       "freshness monitoring.",
       "<b>Test DAGs in CI</b>: an import test that fails on DAG parse errors or cycles."),
    code("python", r"""
# tests/test_dag_integrity.py: runs in CI on every pull request
from airflow.models import DagBag


def test_no_import_errors():
    bag = DagBag(dag_folder="dags/", include_examples=False)
    assert bag.import_errors == {}, f"DAG import failures: {bag.import_errors}"


def test_every_dag_has_owner_and_retries():
    bag = DagBag(dag_folder="dags/", include_examples=False)
    for dag_id, dag in bag.dags.items():
        assert dag.default_args.get("owner"), f"{dag_id} has no owner"
        assert dag.default_args.get("retries", 0) >= 1, f"{dag_id} has no retries"
""", "DAG integrity tests"),
    co("tip", ["Expect: <i>\"How would you migrate jobs from Control-M to Airflow?\"</i> A "
               "strong answer:",
               "- <b>Inventory</b>: export folders via the Automation API (JSON); classify jobs "
               "by type (command, file watcher, DB, SAP...).",
               "- <b>Map</b> concepts (the table in Chapter 1); identify gaps such as calendars, "
               "cross-folder conditions and quantitative resources.",
               "- <b>Automate</b> conversion with a generator script (Project 2 in Chapter 17), "
               "then hand-tune.",
               "- <b>Run in parallel</b> (shadow mode) and compare outputs and timings, then cut "
               "over in waves by application, with rollback plans.",
               "- <b>Operate</b>: monitoring, alerting, runbooks, SLAs and training for the "
               "support team."]),
    co("bridge", "Many enterprises keep Control-M as the enterprise scheduler and integrate it "
                 "with Airflow, cloud data services and Kubernetes, and BMC offers integrations "
                 "for exactly this. 'I can run both worlds' is a valuable pitch to banks, "
                 "insurers and telcos."),
    h3("Other orchestrators to know by name"),
    ul("<b>Dagster</b>: asset-centric (you define data assets, not just tasks); strong typing "
       "and testing.",
       "<b>Prefect</b>: Pythonic flows, dynamic workflows, hybrid execution.",
       "<b>Cloud-native</b>: AWS Step Functions and MWAA (managed Airflow), GCP Cloud Composer "
       "(managed Airflow) and Workflows, Azure Data Factory / Fabric pipelines.",
       "<b>Enterprise WLA</b>: Control-M, Autosys, Tivoli Workload Scheduler, Stonebranch, "
       "Redwood."),
    cards("Airflow", [
        ("What is a DAG in Airflow?",
         "A Directed Acyclic Graph: a Python-defined workflow of tasks with dependencies and no "
         "cycles, plus a schedule."),
        ("Main Airflow components?",
         "Scheduler, executor, workers, metadata database, webserver/API server, DAG files, "
         "triggerer (for deferrable tasks)."),
        ("What is the logical date (formerly execution_date)?",
         "The start of the data interval a DAG run covers. A daily run for 10 March actually "
         "starts after that interval ends (on 11 March)."),
        ("What does catchup do?",
         "When True, the scheduler creates runs for every missed interval between start_date "
         "and now. It's often set to False to avoid surprise mass runs."),
        ("What is XCom and its limitation?",
         "Cross-communication: small values passed between tasks via the metadata DB. Pass "
         "references (paths, IDs), never large datasets."),
        ("Sensor 'poke' vs 'reschedule' mode?",
         "Poke holds a worker slot while sleeping between checks. Reschedule releases the slot "
         "between checks. Deferrable sensors go further and use the async triggerer."),
        ("What is an Airflow pool?",
         "A named limit on concurrent task slots, used to protect shared resources (like "
         "Control-M quantitative resources)."),
        ("Name three executors.",
         "LocalExecutor (single machine, parallel), CeleryExecutor (distributed workers via a "
         "queue), KubernetesExecutor (one pod per task)."),
        ("What are trigger rules?",
         "Conditions for a task to run based on upstream states: all_success (default), "
         "all_failed, all_done, one_success, one_failed, none_failed, and others."),
        ("Why shouldn't heavy processing run on Airflow workers?",
         "Airflow is an orchestrator. Heavy compute belongs in the warehouse, Spark, or isolated "
         "containers (KubernetesPodOperator) for scalability and isolation."),
        ("What are Datasets / Assets?",
         "Data-aware scheduling: a DAG can be triggered when a task in another DAG updates a "
         "named dataset/asset, instead of on a time schedule."),
        ("What is dynamic task mapping?",
         "Creating a variable number of task instances at runtime with .expand(), e.g. one task "
         "per file discovered."),
        ("Control-M Force OK equivalent in Airflow?",
         "'Mark success' on a task instance in the UI/CLI. 'Clear' is the rerun equivalent."),
        ("How do you test Airflow DAGs?",
         "DagBag import tests in CI (no import errors, no cycles), unit tests for the Python "
         "callables, and 'airflow dags test' for a local end-to-end run."),
    ]),

    # ------------------------------------------------------------------ dbt
    ch("Transformations with dbt",
       "dbt (data build tool) lets you write transformations as SELECT statements, and it "
       "handles dependencies, materialisation, testing and documentation. It's the T in ELT "
       "at most modern companies."),
    h2("How dbt works"),
    ul("A <b>model</b> is a .sql file containing one SELECT. dbt wraps it in CREATE TABLE/VIEW.",
       "<font face='Mono'>{{ ref('model') }}</font> references another model; dbt builds the "
       "dependency DAG from these refs automatically.",
       "<font face='Mono'>{{ source('raw', 'orders') }}</font> references raw tables declared in "
       "YAML, which enables freshness checks and lineage.",
       "<b>Materialisations</b>: view, table, incremental, ephemeral (inlined CTE), plus "
       "materialized_view in some adapters.",
       "<b>Tests</b>: generic (unique, not_null, accepted_values, relationships), singular "
       "(custom SQL that returns failing rows), and unit tests (dbt 1.8+).",
       "<font face='Mono'>dbt build</font> runs models, tests, seeds and snapshots in DAG order."),
    code("text", r"""
my_dbt_project/
  dbt_project.yml
  models/
    staging/            # 1:1 with sources: rename, cast, light cleaning  (views)
      _sources.yml
      stg_orders.sql
      stg_customers.sql
    intermediate/       # joins / business logic building blocks
      int_orders_enriched.sql
    marts/              # facts and dimensions for consumers               (tables)
      fct_orders.sql
      dim_customers.sql
      _marts.yml        # tests + docs
  snapshots/
    customers_snapshot.sql
  tests/                # singular tests
  macros/
""", "standard project layout"),
    code("yaml", r"""
version: 2

sources:
  - name: raw
    schema: raw
    loaded_at_field: _loaded_at
    freshness:                              # dbt source freshness -> alert if stale
      warn_after:  {count: 6,  period: hour}
      error_after: {count: 24, period: hour}
    tables:
      - name: orders
      - name: customers

models:
  - name: fct_orders
    description: "One row per order. Grain: order_id."
    columns:
      - name: order_id
        data_tests: [unique, not_null]
      - name: status
        data_tests:
          - accepted_values:
              values: ['placed', 'shipped', 'cancelled']
      - name: customer_id
        data_tests:
          - relationships:
              to: ref('dim_customers')
              field: customer_id
""", "sources, docs and tests (YAML)"),
    code("sql", r"""
-- models/staging/stg_orders.sql
with source as (
    select * from {{ source('raw', 'orders') }}
),
renamed as (
    select
        cast(id as integer)              as order_id,
        cast(customer as integer)        as customer_id,
        cast(created_at as timestamp)    as order_ts,
        lower(trim(status))              as status,
        cast(amount_cents as numeric) / 100 as amount,
        _loaded_at
    from source
)
select * from renamed
""", "staging model"),
    code("sql", r"""
-- models/marts/fct_orders.sql
{{ config(
    materialized = 'incremental',
    unique_key   = 'order_id',
    incremental_strategy = 'merge',
    on_schema_change = 'append_new_columns'
) }}

select
    o.order_id,
    o.customer_id,
    o.order_ts,
    o.status,
    o.amount,
    o._loaded_at
from {{ ref('stg_orders') }} o

{% if is_incremental() %}
  -- only new/changed rows since the last run, with a 3-day lookback for late data
  where o._loaded_at > (select dateadd('day', -3, max(_loaded_at)) from {{ this }})
{% endif %}
""", "incremental mart model (Snowflake syntax for dateadd)"),
    code("sql", r"""
-- snapshots/customers_snapshot.sql  -> builds an SCD Type 2 table automatically
{% snapshot customers_snapshot %}
{{ config(
    target_schema = 'snapshots',
    unique_key    = 'customer_id',
    strategy      = 'check',
    check_cols    = ['city', 'segment']
) }}
select * from {{ source('raw', 'customers') }}
{% endsnapshot %}
-- adds dbt_valid_from, dbt_valid_to, dbt_scd_id, dbt_updated_at
""", "snapshot = SCD2 for free"),
    code("bash", r"""
dbt deps                                  # install packages (e.g. dbt_utils)
dbt debug                                 # check connection
dbt build --select staging+               # staging models and everything downstream
dbt build --select state:modified+ --defer --state prod-artifacts/   # slim CI
dbt source freshness
dbt docs generate && dbt docs serve       # lineage graph + documentation site
""", "everyday commands"),
    co("bridge", "dbt's <font face='Mono'>--select model+</font> graph selection is like "
                 "ordering a Control-M job together with its downstream successors. 'Rerun from "
                 "failure' is <font face='Mono'>dbt retry</font>."),
    cards("dbt", [
        ("What does ref() do in dbt?",
         "Resolves to the correct schema/table for the target environment AND registers a "
         "dependency, so dbt builds models in the right order."),
        ("source() vs ref()?",
         "source() points at raw tables loaded by something else (declared in YAML, supports "
         "freshness). ref() points at other dbt models."),
        ("Four dbt materialisations?",
         "view, table, incremental, ephemeral (plus materialized_view on some adapters)."),
        ("What does is_incremental() do?",
         "Returns true when the model already exists, isn't run with --full-refresh, and is "
         "materialised incrementally, so you can filter to only new rows."),
        ("Four built-in generic tests?",
         "unique, not_null, accepted_values, relationships."),
        ("What is a dbt snapshot?",
         "A mechanism to capture SCD Type 2 history of a mutable source, using the 'timestamp' "
         "or 'check' strategy."),
        ("What does 'dbt build' do?",
         "Runs seeds, models, snapshots and tests together in dependency order. A failing test "
         "skips downstream nodes."),
        ("Typical dbt layer structure?",
         "staging (1:1 with sources, light cleaning), intermediate (reusable logic), marts "
         "(facts/dimensions for consumers)."),
        ("What is slim CI in dbt?",
         "In CI, build only modified models and their children (state:modified+), deferring "
         "unchanged upstream refs to production artifacts."),
        ("What is an ephemeral model?",
         "A model that isn't built in the database; it's inlined as a CTE into the models that "
         "reference it."),
    ]),
]
