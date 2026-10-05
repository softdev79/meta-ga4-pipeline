"""Chapters: portfolio projects; resume & interviews; glossary; final review deck."""

from content_helpers import c, ch, h2, h3, p, ul, ol, code, co, tbl, cards, flow

BLOCKS = [
    # ------------------------------------------------------------------ projects
    ch("Portfolio Projects",
       "Three projects that prove the skills, and one of them is something almost no other "
       "candidate can build. Put each on GitHub with a strong README."),
    h2("Project 1: Batch ELT pipeline, end to end"),
    flow([
        ("Public API", "e.g. Open-Meteo weather, NYC taxi, GitHub events"),
        ("Python extract", "pagination, retries, JSONL to bucket"),
        ("Bronze", "GCS / S3, dt= partitions"),
        ("Warehouse", "BigQuery sandbox / DuckDB"),
        ("dbt", "staging, marts, tests, snapshot"),
        ("Dashboard", "Looker Studio / Metabase"),
    ], "Airflow (Docker) orchestrates daily  ·  idempotent by logical date  ·  "
       "GitHub Actions CI"),
    ul("<b>Show</b>: idempotent reruns (run the same date twice and show identical counts), a "
       "backfill of 30 days, dbt tests catching an injected bad record, and a lineage graph "
       "screenshot from dbt docs.",
       "<b>README sections</b>: problem, architecture diagram, data model (grain!), how to run "
       "locally (docker compose up), design decisions and trade-offs, what you'd do at 100x "
       "scale."),
    h2("Project 2: Control-M to Airflow migration tool (your signature project)"),
    p("Build a converter that reads a Control-M Automation API folder definition (JSON) and "
      "generates an Airflow DAG. It shows orchestration depth, Python and migration thinking, "
      "and it's a story nobody else in the interview pool has. Start small with Command and "
      "FileWatcher jobs plus Flow sequences, then extend it."),
    code("python", r'''
"""ctm2airflow.py - convert Control-M Automation API folders (JSON) into Airflow DAG files.

usage: python ctm2airflow.py folders.json dags/
"""
import json
import sys
from pathlib import Path

HEADER = """from datetime import datetime

from airflow import DAG
from airflow.operators.bash import BashOperator
from airflow.operators.empty import EmptyOperator
from airflow.sensors.filesystem import FileSensor

with DAG(dag_id="{dag_id}", schedule="{cron}", start_date=datetime(2024, 1, 1),
         catchup=False, max_active_runs=1, tags=["migrated-from-control-m"]) as dag:"""

DOW = {"SUN": 0, "MON": 1, "TUE": 2, "WED": 3, "THU": 4, "FRI": 5, "SAT": 6}
VARS = {"%%ODATE": "{{ ds_nodash }}", "%%$ODATE": "{{ ds_nodash }}"}


def to_cron(when: dict) -> str:
    hhmm = when.get("FromTime", "0000")
    days = ",".join(str(DOW[d]) for d in when.get("WeekDays", [])) or "*"
    return f"{int(hhmm[2:])} {int(hhmm[:2])} * * {days}"


def translate(text: str) -> str:
    for ctm, jinja in VARS.items():
        text = text.replace(ctm, jinja)
    return text


def task_line(name: str, job: dict) -> str:
    tid, kind = name.lower(), job["Type"]
    if kind == "Job:Command":
        return f"    {tid} = BashOperator(task_id={tid!r}, " \
               f"bash_command={translate(job['Command'])!r})"
    if kind.startswith("Job:FileWatcher"):
        return f"    {tid} = FileSensor(task_id={tid!r}, " \
               f"filepath={translate(job['Path'])!r}, mode='reschedule', poke_interval=60)"
    return f"    {tid} = EmptyOperator(task_id={tid!r})  # TODO: unsupported type {kind}"


def convert(folder_name: str, folder: dict) -> str:
    jobs = {k: v for k, v in folder.items()
            if isinstance(v, dict) and v.get("Type", "").startswith("Job")}
    edges = []
    for item in folder.values():
        if isinstance(item, dict) and item.get("Type") == "Flow":
            seq = [s.lower() for s in item["Sequence"]]
            edges += zip(seq, seq[1:])
    lines = [HEADER.format(dag_id=folder_name.lower(), cron=to_cron(folder.get("When", {})))]
    lines += [task_line(n, j) for n, j in jobs.items()]
    lines += [f"    {a} >> {b}" for a, b in edges]
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    src, out = Path(sys.argv[1]), Path(sys.argv[2])
    out.mkdir(parents=True, exist_ok=True)
    for name, folder in json.loads(src.read_text()).items():
        target = out / f"{name.lower()}.py"
        target.write_text(convert(name, folder))
        print(f"wrote {target}")
''', "ctm2airflow.py (starter version)"),
    co("practice", [
        "Extensions that turn this into a standout project:",
        "- Map <b>Resource:Semaphore</b> to Airflow <b>pools</b> and <b>Resource:Mutex</b> to "
        "max_active_runs / pools of size 1.",
        "- Translate <b>in/out conditions across folders</b> to Datasets/Assets or "
        "ExternalTaskSensor.",
        "- Convert <b>calendars</b> to cron expressions or custom Timetables, and flag the ones "
        "that can't be expressed.",
        "- Produce a <b>migration report</b> (CSV/HTML): job counts by type, auto-converted vs "
        "needs-manual-work.",
        "- Add <b>pytest</b> tests and validate the generated DAGs with a DagBag import test in "
        "CI.",
        "- Write a LinkedIn / Medium article: <i>\"What 5 years of Control-M taught me about "
        "Airflow\"</i>.",
    ], "make it yours"),
    h2("Project 3: Streaming pipeline"),
    flow([
        ("Event generator", "Python fake orders / clicks"),
        ("Kafka", "docker compose, 3 partitions"),
        ("Spark Structured Streaming", "parse, watermark, 5-min windows"),
        ("Lake / Delta", "checkpointed, exactly-once file sink"),
        ("Query", "DuckDB / Superset live chart"),
    ]),
    ul("<b>Show</b>: kill the streaming job mid-run, restart it, and prove there are no "
       "duplicates or gaps (checkpoints). Send deliberately late events and show the watermark "
       "behaviour."),
    h2("Read a real repository"),
    p("The repository this guide is stored in (<b>meta-ga4-pipeline</b>) is a compact, "
      "realistic marketing-data pipeline. After Chapters 8-10, read it as a case study:"),
    ul("<font face='Mono'>marketing_ingestion_dag.py</font>: <b>config-driven DAG generation</b> "
       "from <font face='Mono'>sources.yaml</font> (one DAG per ad account), and a trailing "
       "<b>28-day restatement window</b> because the source revises historical numbers.",
       "<font face='Mono'>bigquery.py</font> / <font face='Mono'>meta_ads.py</font>: "
       "<b>MERGE-based idempotent loads</b>, API client and rate limiting.",
       "<font face='Mono'>stg_ga4_sessions.sql</font> and "
       "<font face='Mono'>fct_paid_performance_daily.sql</font>: staging-to-fact modelling, with "
       "an explicit <b>grain</b> decision (roll tracking up to ad x day before joining spend, to "
       "avoid fan-out).",
       "<font face='Mono'>test_meta_ads.py</font>: how ingestion code is unit-tested.",
       "<font face='Mono'>README.md</font>: notice how it explains <i>why</i> (grain, identity, "
       "restatement, attribution). Write your project READMEs the same way."),
    cards("Projects", [
        ("Three things every portfolio README should contain?",
         "An architecture diagram, the data model with explicit grain, and design decisions / "
         "trade-offs (plus how to run it and what you'd change at scale)."),
        ("How do you demonstrate idempotency in a demo?",
         "Run the same logical date twice and show identical row counts and checksums; run a "
         "backfill and show no duplicates."),
        ("Why is the Control-M to Airflow converter a strong project for you?",
         "It combines your unique domain expertise with Python and modern orchestration, and it "
         "maps directly to real enterprise migration work."),
    ]),

    # ------------------------------------------------------------------ interviews
    ch("Resume, Interviews and Landing the Role",
       "Translate your experience into data engineering language, then prove it in each "
       "interview round."),
    h2("Reframing your resume"),
    p("Lead with <b>outcomes, scale and data</b>. Replace the bracketed values with your real "
      "numbers. Never invent metrics: interviewers will ask you about them."),
    tbl([
        ["Before (admin language)", "After (data engineering language)"],
        ["Administered Control-M for the organisation.",
         "Operated enterprise workload orchestration (Control-M) for [2,000+] daily batch jobs "
         "feeding the [Oracle/Teradata] data warehouse and finance reporting, with a [99.x%] "
         "on-time SLA."],
        ["Monitored jobs and handled failures.",
         "Led incident response for production data pipelines; cut mean time to recovery by "
         "[30%] through runbooks, automated reruns and dependency-aware alerting."],
        ["Created and modified job definitions.",
         "Designed batch dependency flows and resource controls (quantitative/control "
         "resources) to shorten the nightly batch window from [6h to 4.5h]."],
        ["Did Control-M upgrades.",
         "Planned and executed Control-M [v9 to v21] upgrade and agent migration across [N] "
         "hosts with zero data-delivery misses."],
        ["Wrote scripts.",
         "Built Python/Bash automation for file ingestion, validation and reconciliation, "
         "removing [N] hours/week of manual checks."],
        ["Worked on development tasks.",
         "Developed [Java/Python] services and SQL for [system]; wrote unit tests and "
         "participated in code review and CI/CD."],
    ], [1.6, 3.4]),
    ul("<b>Headline</b>: 'Data Engineer | Orchestration and Pipeline Reliability | Airflow, SQL, "
       "Python, dbt, Spark | 5 yrs production workload automation'.",
       "<b>Projects section</b> above older experience while you're switching, with GitHub links.",
       "<b>Keywords</b> from the job post (ATS filters): Airflow, ETL/ELT, SQL, Python, Spark, "
       "dbt, Kafka, BigQuery/Snowflake/Redshift, data modelling, CI/CD."),
    h2("Typical interview loop"),
    tbl([
        ["Round", "What they test", "How to prepare"],
        ["Recruiter screen", "Motivation, basics, salary, notice period",
         "60-second 'why data engineering' pitch (below)"],
        ["SQL (live)", "Joins, aggregation, window functions, edge cases",
         "Chapter 4 + 50-100 practice problems"],
        ["Python / coding", "Data manipulation, parsing, simple algorithms",
         "Dicts, sorting, file/JSON parsing, LeetCode easy-medium"],
        ["Data modelling", "Design a schema for a business process",
         "Process, grain, dimensions, facts, SCD"],
        ["System / pipeline design", "End-to-end architecture, trade-offs",
         "The framework below"],
        ["Behavioural", "Ownership, incidents, collaboration",
         "6 STAR stories from your Control-M years"],
    ], [1.3, 2, 2]),
    h2("Your 'why data engineering' pitch"),
    co("tip", "<i>\"For five years I've run the orchestration layer that moves our company's "
              "data, with Control-M scheduling thousands of jobs that feed the warehouse and "
              "reporting. I became the person who understood why jobs failed, not just that "
              "they failed, and that pulled me into the SQL, the data and the pipeline code. "
              "Over the past months I've built [projects] with Airflow, dbt and Spark. I want "
              "to own pipelines end to end, not just schedule them, and I bring production "
              "reliability habits most new data engineers take years to learn.\"</i>",
        "60-second pitch template"),
    h2("STAR stories to prepare"),
    p("<b>S</b>ituation, <b>T</b>ask, <b>A</b>ction (most of the time, and say 'I', not 'we'), "
      "<b>R</b>esult (with numbers). Prepare one story for each prompt:"),
    tbl([
        ["Prompt", "Mine your Control-M experience for..."],
        ["A production incident you resolved", "A failed critical batch, a missed SLA, root "
                                               "cause, prevention"],
        ["Something you automated", "Scripts, Automation API, self-healing reruns, reports"],
        ["A large change / migration", "Version upgrade, agent migration, data centre / cloud "
                                       "move"],
        ["Disagreement with a stakeholder", "Pushing back on an unsafe change or an "
                                            "unrealistic schedule"],
        ["A mistake you made", "What broke, how you owned it, what process you changed"],
        ["Learning something fast", "Your data engineering transition itself!"],
    ], [1.8, 3.2]),
    co("note", [
        "<b>Example (fill in your real details):</b>",
        "<b>S:</b> The finance month-end batch was regularly finishing after the 7 a.m. SLA, "
        "delaying reports to [N] executives.",
        "<b>T:</b> I was asked to bring it back inside the SLA without new hardware.",
        "<b>A:</b> I exported three months of run history, found that [4] long jobs ran "
        "serially without needing to, re-modelled the dependencies to run them in parallel, "
        "added a quantitative resource to protect the database, and moved a heavy "
        "reconciliation step earlier.",
        "<b>R:</b> Completion moved from about 7:40 to about 5:50 a.m.; zero SLA misses for "
        "[6] months. I documented the analysis as a reusable runbook.",
    ], "STAR"),
    h2("Pipeline system design framework"),
    ol("<b>Clarify requirements</b>: consumers, latency (batch or real-time), volume and "
       "growth, freshness SLA, accuracy needs, history and retention, compliance (PII).",
       "<b>Sources and ingestion</b>: databases (CDC or batch extract), APIs, files, events. "
       "Push or pull? Full or incremental?",
       "<b>Storage</b>: lake layers (bronze/silver/gold), formats (Parquet/Delta/Iceberg), "
       "partitioning.",
       "<b>Processing</b>: SQL/dbt in the warehouse vs Spark vs streaming engine. Justify the "
       "choice by volume and latency.",
       "<b>Modelling and serving</b>: star schema / marts, BI, APIs, ML features, reverse ETL.",
       "<b>Orchestration</b>: DAG design, dependencies, retries, backfills, idempotency.",
       "<b>Quality and observability</b>: tests, freshness/volume monitors, alerting, lineage, "
       "runbooks.",
       "<b>Security and cost</b>: IAM, encryption, PII masking; partition pruning, "
       "auto-suspend, lifecycle rules.",
       "<b>Scale and failure modes</b>: what breaks at 10x? Late data, duplicates, schema drift, "
       "source outages."),
    co("practice", [
        "<b>Worked prompt:</b> <i>\"500 retail stores upload daily sales CSVs to SFTP by 1 a.m. "
        "Executives need a dashboard by 7 a.m. Design it.\"</i>",
        "- <b>Ingest:</b> a sensor waits for files (with a cut-off and an alert for missing "
        "stores); copy them to the bronze bucket partitioned by business date; validate row "
        "counts against trailer records.",
        "- <b>Process:</b> load to staging; dedupe; quarantine bad rows to a DLQ table; dbt "
        "builds silver (typed, conformed) and gold (fct_sales at grain store x product x day, "
        "dim_store, dim_product SCD2, dim_date).",
        "- <b>Orchestrate:</b> one Airflow DAG per day; per-store dynamic tasks; idempotent "
        "partition overwrite; late stores reprocessed by a 3-day lookback.",
        "- <b>Quality:</b> blocking tests (unique keys, non-negative amounts, store coverage "
        "&gt;= 98%) before the dashboard refresh; freshness SLA alert at 6:30 a.m.",
        "- <b>Scale:</b> 500 stores of daily CSVs is small; a warehouse plus dbt is enough. "
        "Spark only if volume grows by orders of magnitude. Mention cost and simplicity.",
    ], "system design"),
    h2("Questions to ask the interviewer"),
    ul("What does the current data stack look like, and what's the biggest pain point?",
       "How are pipelines monitored, and who is on call?",
       "How do you test data and deploy changes (CI/CD)?",
       "What would success look like for this role in the first 90 days?",
       "Is there an ongoing migration (e.g. from a legacy scheduler or on-prem to cloud)? "
       "<i>(a perfect opening for your background)</i>"),
    cards("Interview prep", [
        ("STAR stands for?",
         "Situation, Task, Action, Result. Spend most of the time on Action ('I') and quantify "
         "the Result."),
        ("First step in any system design answer?",
         "Clarify requirements: consumers, latency, volume, freshness SLA, history, compliance. "
         "Then propose an architecture and discuss trade-offs."),
        ("How do you answer 'You've never had a data engineer title'?",
         "Reframe: you've operated production data pipelines (orchestration, SLAs, incidents) "
         "for 5 years, and you've built [projects] covering SQL, dbt, Airflow and Spark. Give "
         "concrete examples."),
        ("Why should you mention idempotency and backfills in design answers?",
         "They show you've thought about reruns and failure recovery, the operational reality "
         "most junior candidates miss."),
    ]),

    # ------------------------------------------------------------------ glossary
    ch("Glossary",
       "Quick definitions to skim before interviews."),
    tbl([
        ["Term", "Definition"],
        ["ACID", "Atomicity, Consistency, Isolation, Durability: transaction guarantees"],
        ["Backfill", "Running a pipeline for historical intervals"],
        ["CDC", "Change Data Capture: streaming row-level changes from a database log"],
        ["Columnar storage", "Storing each column contiguously; fast analytic scans"],
        ["Data contract", "Agreed, enforced schema/semantics/SLA between producer and consumer"],
        ["Data mart", "Subject-specific subset of the warehouse (e.g. sales mart)"],
        ["DAG", "Directed acyclic graph: tasks with dependencies and no cycles"],
        ["Data lake", "Object storage holding raw files of any format"],
        ["Lakehouse", "Lake + open table format giving warehouse-like ACID behaviour"],
        ["DLQ", "Dead-letter queue: where failed records are quarantined"],
        ["ELT / ETL", "Load-then-transform in the warehouse / transform-then-load"],
        ["Fan-out", "Row multiplication from joining across grains"],
        ["Grain", "What one row of a table represents"],
        ["Idempotent", "Same result no matter how many times it runs"],
        ["Lineage", "Map of data's origins and downstream dependencies"],
        ["Logical date", "The data interval a scheduled run is responsible for (ODATE)"],
        ["Medallion", "Bronze/silver/gold layering of data quality"],
        ["Micro-batch", "Processing a stream as frequent small batches"],
        ["OLAP / OLTP", "Analytical / transactional workloads"],
        ["Parquet", "Open columnar file format with embedded schema and statistics"],
        ["Partition pruning", "Skipping partitions that can't match a filter"],
        ["Reverse ETL", "Syncing warehouse data back into operational tools (CRM, ads)"],
        ["SCD", "Slowly changing dimension: strategies for attribute history"],
        ["Schema evolution", "Handling added/changed columns over time safely"],
        ["Shuffle", "Redistributing data across the network by key (Spark)"],
        ["Skew", "Uneven data distribution causing straggler tasks"],
        ["Star schema", "Fact table surrounded by denormalised dimension tables"],
        ["Surrogate key", "Warehouse-generated key independent of source IDs"],
        ["Watermark (batch)", "Last processed value used for incremental loads"],
        ["Watermark (streaming)", "Lateness threshold for event-time windows"],
    ], [1.3, 4]),

    # ------------------------------------------------------------------ final deck
    ch("Appendix: Rapid-Fire Review Deck",
       "Mixed questions across every chapter. Use this deck in the final two weeks and on "
       "the morning of each interview."),
    cards("Mixed review", [
        ("A daily job inserted duplicates after a rerun. Root cause and fix?",
         "The load isn't idempotent (plain INSERT). Fix: partition overwrite (delete+insert for "
         "the run date in one transaction) or MERGE on a business key, plus a uniqueness test."),
        ("A dashboard shows revenue doubled after a new join. What happened?",
         "Fan-out: the join was to a table at a finer grain (many rows per key). Aggregate to "
         "the same grain before joining, or fix the join key."),
        ("A Spark stage has 199 fast tasks and 1 that runs for an hour. Why?",
         "Data skew on the partition key. Fix with AQE skew join, salting, broadcasting the "
         "other side, or handling the hot key separately."),
        ("BigQuery costs spiked. First three things to check?",
         "SELECT * queries, missing partition filters (enable require_partition_filter), and "
         "repeated scheduled queries / dashboards scanning large tables."),
        ("The source added a column and the pipeline broke. How do you prevent it next time?",
         "Schema-drift handling: allow additive changes (on_schema_change / mergeSchema), "
         "alert on breaking ones, and agree a data contract with the producer."),
        ("A Kafka consumer is far behind (lag growing). Options?",
         "Add consumers up to the partition count; increase partitions; speed up processing "
         "(batching, async I/O); check for a slow sink or rebalancing loops."),
        ("Explain the difference between a data warehouse and a data lake in one breath.",
         "A warehouse stores structured, modelled data optimised for SQL analytics; a lake "
         "stores raw files of any format cheaply. A lakehouse adds table formats to bridge "
         "the two."),
        ("What happens if an Airflow task's start_date is dynamic, like datetime.now()?",
         "Scheduling becomes unpredictable and runs may never trigger. Always use a fixed, "
         "static start_date."),
        ("When would you pick Airflow over Control-M (and vice versa)?",
         "Airflow: code-first data pipelines, open source, rich data integrations, Git/CI "
         "workflows. Control-M: enterprise-wide workload automation across mainframe/ERP/"
         "file transfer, mature governance and support. Many firms use both."),
        ("What does 'exactly-once' really require end to end?",
         "Replayable source with tracked offsets, deterministic processing, and an idempotent "
         "or transactional sink committed together with the offsets/checkpoint."),
        ("How do you choose between dbt in the warehouse and Spark?",
         "Data already in the warehouse and SQL-expressible: dbt. Very large volumes, "
         "unstructured data, complex non-SQL logic or ML: Spark."),
        ("Define SLA, SLO and SLI for a data product.",
         "SLI: the measured metric (e.g. table freshness). SLO: the internal target (fresh by "
         "06:30 on 99% of days). SLA: the external commitment with consequences."),
        ("What is the difference between a view and a materialised view?",
         "A view stores only the query and recomputes on every read. A materialised view "
         "stores results and refreshes them (incrementally in some engines)."),
        ("What is a surrogate key collision risk when using hashes?",
         "Different inputs producing the same hash. With md5/sha over well-delimited natural "
         "keys it's negligible, but always include a delimiter and handle NULLs consistently."),
        ("Why should raw (bronze) data be immutable?",
         "It allows replaying and rebuilding downstream layers after bugs, provides an audit "
         "trail, and decouples ingestion from transformation logic."),
        ("Name the four Kimball design steps.",
         "Select the business process, declare the grain, identify dimensions, identify facts."),
    ]),
    h2("Final checklist before applying"),
    tbl([
        ["Done", "Item"],
        ["[  ]", "100+ SQL problems solved, including 30+ with window functions"],
        ["[  ]", "Project 1 (batch ELT) on GitHub with README, diagram and CI badge"],
        ["[  ]", "Project 2 (Control-M to Airflow converter) with tests and a write-up"],
        ["[  ]", "Project 3 (streaming) or a Spark tuning write-up"],
        ["[  ]", "Resume rewritten in data engineering language with real metrics"],
        ["[  ]", "LinkedIn headline + 'Open to work' (recruiters only) + 2 posts about your "
                 "projects"],
        ["[  ]", "6 STAR stories written and rehearsed aloud"],
        ["[  ]", "System design framework practised on 3 prompts"],
        ["[  ]", "Every flashcard in Box 3 or higher"],
        ["[  ]", "One cloud certification booked or passed (optional)"],
    ], [0.6, 5]),
    co("note", "You're not starting from zero. You're starting from production. Every concept "
               "in this guide builds on things you have already done at scale. Keep going."),
]
