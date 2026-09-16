# Cloud Composer / Airflow

You have a real DAG in this repo (`marketing_ingestion_dag.py`) — a **metadata-driven DAG
factory**. That is a genuinely senior pattern and most candidates have never built one.
Lead with it.

---

## 1. Core concepts, stated precisely

- **DAG** — a collection of tasks with dependencies + a schedule. The DAG file is Python
  that **runs on every scheduler parse** (default every 30s). Anything expensive at module
  level — an API call, a BigQuery query, a `pd.read_csv` — runs hundreds of times an hour.
  **This is the #1 Airflow interview trap.** Say it before they ask.
- **Operator / Task / Task Instance** — the template / the instantiated node / a specific
  run of that node for a specific logical date.
- **Executor** — Sequential, Local, **Celery** (workers + Redis/Rabbit broker),
  **Kubernetes** (pod per task). Composer 2/3 runs on GKE with **Celery + KubernetesExecutor**,
  autoscaling workers.
- **Scheduler → Executor → Worker → Metadata DB**. The metadata DB (Cloud SQL in Composer)
  is the system of record; the webserver only reads it.
- **XCom** — small inter-task messages, stored **in the metadata DB**. Not for data. Push
  a GCS URI, not a DataFrame. (Custom XCom backends can offload to GCS.)
- **Hooks / Connections / Variables** — reusable client wrappers / stored credentials /
  key-value config. **Connections and Variables hit the DB on every parse if read at module
  level** — use a Jinja template or read inside the task. Secrets belong in **Secret
  Manager** via the Composer secrets backend.
- **Pools** — concurrency limits for a shared resource ("only 5 concurrent Oracle
  extracts"). **Priority weight** orders within a pool.
- **Sensors** — wait for a condition. Use `mode='reschedule'` (frees the worker slot
  between pokes) not `mode='poke'`, and **always set a `timeout`**. A poke-mode sensor
  with no timeout is how you deadlock a Composer environment.
- **Trigger rules** — `all_success` (default), `all_done`, `one_failed`, `none_failed_min_one_success`.
  `all_done` is how you guarantee cluster teardown runs even when the job failed.
- **Deferrable operators / the Triggerer** — async waiting on an asyncio event loop
  instead of occupying a worker slot. **Modern answer to "how do you scale sensors."**
- **Dynamic task mapping** (`.expand()`, Airflow 2.3+) — fan out tasks at runtime from a
  list produced by an upstream task. The modern replacement for building tasks in a loop
  over a runtime-unknown collection.
- **Datasets / asset-based scheduling** (2.4+ / Airflow 3) — schedule a DAG on *data
  produced by another DAG* instead of a cron. Replaces `ExternalTaskSensor` for most cases.
- **TaskFlow API** — `@dag` / `@task` decorators; XCom passing becomes function arguments.

---

## 2. `schedule_interval`, `logical_date`, and the question everyone gets wrong

**Q: "A DAG is scheduled `@daily`. It runs at 02:00 on the 16th. What's the logical date?"**

> **The 15th.** Airflow runs an interval *after it closes*. `logical_date`
> (formerly `execution_date`) is the **start of the data interval**, so the daily run that
> fires early on the 16th is processing the 15th's data. That's why every SQL template uses
> `{{ ds }}` and not `CURRENT_DATE()` — the task must produce the same output whenever it
> runs, including on a backfill six months later.

Related macros: `{{ ds }}` (YYYY-MM-DD), `{{ ds_nodash }}`, `{{ data_interval_start }}` /
`{{ data_interval_end }}` (the modern, preferred pair), `{{ prev_ds }}`, `{{ run_id }}`.

- **`catchup=True`** backfills every missed interval since `start_date`. Setting a
  `start_date` a year back with `catchup=True` and `max_active_runs` unset launches 365
  concurrent runs and takes down the environment. **`catchup=False` + `max_active_runs=1`
  is the safe default.**
- **`start_date` must be static.** `datetime.now()` as a start date means the DAG never
  becomes eligible to run — a classic "my DAG won't trigger" ticket.

---

## 3. Idempotency — the concept the whole round hangs on

> "A task is idempotent if running it twice for the same logical date leaves the world in
> the same state as running it once. Practically that means: write to the **partition of
> `{{ ds }}`** with `WRITE_TRUNCATE`, or `MERGE` on a business key — never `WRITE_APPEND`
> with `CURRENT_DATE()`. Once every task is idempotent, retries, backfills and manual
> replays stop being scary, and that's what actually lets you sleep during an incident."

Checklist to recite:
1. Deterministic destination: partition decided by `{{ ds }}`, not wall clock.
2. `WRITE_TRUNCATE` on the partition, or `MERGE` on the key.
3. No `INSERT` without a dedup/merge strategy.
4. Externally-visible side effects (emails, API pushes) guarded so a retry doesn't re-send.
5. Extraction uses `data_interval_start`/`end` as bounds, not "since last run".

---

## 4. Your metadata-driven DAG factory — the story to tell

```python
# config/sources.yaml drives DAG creation at parse time
for source in load_sources("config/sources.yaml"):
    dag_id = f"ingest_{source['name']}"
    globals()[dag_id] = build_ingestion_dag(source)   # must land in globals()
```

**Say this:**
> "Onboarding a new ad account is a YAML entry, not a new DAG file. Retry semantics,
> restatement window, freshness checks and alerting are defined once in the factory and
> inherited by every source. I've run this pattern at roughly **600 generated DAGs** —
> at that scale the alternative, copy-pasted DAG files, means a change to retry policy is
> a 600-file pull request and the drift is guaranteed."

**Be ready for the pushback — it's the good interviewer's move:**
- *"What's the cost of that?"* → **Parse time.** Every generated DAG is parsed on every
  loop. Keep the factory cheap — no I/O at module level, YAML read from the DAG folder
  and cached, `dagbag_import_timeout` / `min_file_process_interval` tuned. At 600 DAGs I
  watch the `dag_processing.total_parse_time` metric like a production SLO.
- *"How do you test it?"* → A DAG-integrity test in CI: import the DagBag, assert zero
  import errors, assert every DAG has an owner, retries, an SLA and tags. That single
  test catches most breakage before deploy.
- *"Debuggability?"* → Generated DAGs are harder to read in the UI. Mitigate with a
  consistent `dag_id` convention, tags per source system, and `doc_md` rendered from the
  YAML so the UI shows where the config came from.

---

## 5. Cloud Composer specifics (as opposed to plain Airflow)

- **Composer 2** = GKE Autopilot + Cloud SQL + GCS bucket for DAGs, autoscaling workers.
  **Composer 3** decouples further, faster environment ops, better isolation.
- **DAGs are synced from a GCS bucket** (`gs://<env>-bucket/dags`). Deploy = copy files.
  `/plugins`, `/data` also mounted. Propagation is ~1–2 minutes, not instant.
- **Environment sizing:** scheduler count/CPU, worker min/max, web server. Composer costs
  money **while idle** — a common client complaint. For a handful of scheduled queries,
  **Cloud Scheduler + Cloud Run/Workflows, or BigQuery scheduled queries, is often the
  right, cheaper answer.** Volunteering that shows commercial judgement.
- **Private IP + VPC-SC** for regulated clients; PyPI packages installed via the
  environment config (and a private PyPI mirror if egress is blocked).
- **Upgrades** are the real operational pain: Airflow version upgrades can break provider
  imports. Keep `requirements` pinned and test in a lower environment.
- **Logs** go to Cloud Logging; metrics to Cloud Monitoring.

---

## 6. Operators you should name without hesitating

```
BigQueryInsertJobOperator          # the modern one — run any query/load/extract job
BigQueryCreateEmptyTableOperator / BigQueryGetDataOperator
BigQueryCheckOperator / BigQueryValueCheckOperator / BigQueryIntervalCheckOperator   # DQ gates
GCSToBigQueryOperator / BigQueryToGCSOperator / GCSToGCSOperator
GCSObjectExistenceSensor  (deferrable variant available)
DataflowTemplatedJobStartOperator / DataflowStartFlexTemplateOperator / BeamRunPythonPipelineOperator
DataprocCreateClusterOperator / DataprocSubmitJobOperator / DataprocDeleteClusterOperator
DataprocCreateBatchOperator        # Dataproc Serverless — no cluster at all
CloudRunExecuteJobOperator / KubernetesPodOperator
PubSubPublishMessageOperator / PubSubPullSensor
TriggerDagRunOperator / ExternalTaskSensor
PythonOperator / BranchPythonOperator / ShortCircuitOperator / EmptyOperator
```

**Deprecated, do not say:** `BigQueryOperator`, `BigQueryExecuteQueryOperator` (→ use
`BigQueryInsertJobOperator`), `SubDagOperator` (→ **TaskGroups**).

**The ephemeral Dataproc pattern — a near-certain question:**
```
create_cluster >> submit_job >> delete_cluster
delete_cluster.trigger_rule = 'all_done'     # tear down even if the job failed
```
> "Better still, `DataprocCreateBatchOperator` — Dataproc Serverless removes the cluster
> lifecycle entirely, so there's no orphaned-cluster failure mode to design around."

---

## 7. Debugging scenarios — rehearse these out loud

**"A DAG isn't running at all."**
Checklist, in order: is it **unpaused**? Is `start_date` in the past and static? Is the
schedule what you think (interval closes *after*)? Import errors in the DAG list
(`airflow dags list-import-errors`)? Is the file in the right GCS path and synced?
Is the scheduler healthy — check `dag_processing.total_parse_time` and scheduler
heartbeat? Are all slots consumed (`max_active_runs`, pool exhausted, concurrency)?

**"Tasks are stuck in `queued`/`scheduled`."**
Workers are saturated or not scaling → check worker count, `worker_concurrency`,
`parallelism`, pool slots, and whether a `poke`-mode sensor army is holding every slot.
In Composer, check GKE node pressure and whether pods are Pending on resources.

**"Half of yesterday's data is missing in BigQuery and the DAG shows green."**
This is a real HCL-style scenario and your answer should be:
> "Green with missing data means a task succeeded while doing nothing — my first
> hypothesis is a source that returned an empty or partial result and a load step that
> happily wrote zero rows. I'd check row counts per partition in
> `INFORMATION_SCHEMA.PARTITIONS` against the source, then look at whether the extract
> window was correct — a `CURRENT_DATE()` in the query instead of `{{ ds }}` produces
> exactly this on a delayed run. The recovery is a `clear` of that task instance so it
> re-runs idempotently for that logical date. The **fix** is a data quality gate between
> load and marts: a `BigQueryCheckOperator` asserting the partition has a plausible row
> count, so the pipeline fails loudly instead of succeeding emptily. I built exactly this
> as `check_freshness` in my own pipeline, because a pipeline that succeeds while loading
> zero rows is worse than one that fails — dashboards keep rendering and nobody notices
> for a week."

**That answer is a 5/5.** Hypothesis → diagnostic → recovery → systemic fix → own experience.

**"How do you handle a task that must not run twice concurrently?"**
`max_active_tis_per_dag`, a **pool of size 1**, or `depends_on_past=True` /
`wait_for_downstream`. Note that `depends_on_past` will stall the whole chain forever on a
single unresolved failure — a trade-off worth naming.

---

## 8. Alerting and SLAs

- `on_failure_callback` → Slack/PagerDuty/Cloud Monitoring. `email_on_failure` alone is
  where alerts go to die.
- **SLA misses** (`sla=timedelta(hours=2)`) fire a separate callback — this catches "it
  didn't fail, it's just late," which is the failure mode that actually hurts business users.
- Alert on **data**, not just tasks: freshness, row count deltas, null rates. See `08-DQ-GOVERNANCE.md`.
- Composer → Cloud Monitoring dashboards on task failure rate, scheduler heartbeat,
  DAG parse time, worker pod restarts.

---

## 9. Airflow vs the alternatives (the JD says "Composer/Airflow", but be ready)

- **Cloud Workflows** — serverless YAML/JSON orchestration for API calls; no Python, no
  backfill semantics, near-zero cost. Right for lightweight service chaining.
- **Cloud Scheduler + Cloud Run Jobs** — cron + a container. Right when there are 5 jobs, not 500.
- **Dataform / dbt Cloud** — in-warehouse transformation DAG; complements Airflow rather
  than replacing it (Airflow triggers the dbt run).
- **Dagster / Prefect** — asset-centric and typed; better local dev ergonomics. Know the
  names; don't evangelise a different tool in a Composer interview.
