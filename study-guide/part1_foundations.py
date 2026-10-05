"""Chapters: how to use, Control-M bridge, roadmap, DE foundations."""

from content_helpers import c, ch, h2, h3, p, ul, ol, code, co, tbl, cards, flow, space

BLOCKS = [
    # ------------------------------------------------------------------ 0
    ch("How to Use This Guide",
       "You already run production. You already know what a 2 a.m. failed job feels like. "
       "This guide turns five years of Control-M administration and software development "
       "into a data engineering profile, one concept at a time."),
    p("This guide is written for a professional with about <b>five years of Control-M "
      "administration plus some software development</b>, and no formal data engineering "
      "title yet. It doesn't assume any big-data background, but it does assume you know "
      "scheduling, job dependencies, Linux and production support, because you do."),
    h2("What is inside"),
    tbl([
        ["Element", "What it looks like", "How to use it"],
        ["Concept sections", "Plain-language explanations",
         "Read once slowly, then skim before interviews."],
        ["Code blocks", "Syntax-highlighted SQL, Python, PySpark, YAML, Bash",
         "Type them out. Do not copy-paste; the typing is the learning."],
        ["Control-M Bridge", "Amber boxes",
         "Link each new idea to something you already did in Control-M. "
         "These become interview stories."],
        ["Flashcards", "Blue (front) / white (back) cards",
         "Cover the right column with a sheet of paper, answer aloud, reveal. "
         "Mark the ones you miss."],
        ["Interview Tip / Pitfall", "Green / red boxes",
         "What interviewers actually probe, and the traps that lose offers."],
        ["Practice", "Purple boxes", "Small exercises. Do them, and push the answers to GitHub."],
    ], [1.1, 1.6, 2.6]),
    h2("Spaced repetition with the flashcards"),
    p("Use the Leitner system. It's the cheapest memory technique that actually works:"),
    ol("Every card starts in <b>Box 1</b>. Review Box 1 every day.",
       "Answer right: the card moves up a box. Box 2 gets reviewed every 3 days, Box 3 weekly, "
       "and Box 4 every two weeks.",
       "Answer wrong: the card goes back to Box 1, however high it had reached.",
       "Write the card number (e.g. <b>#045</b>) in a notebook or spreadsheet with its current "
       "box. Twenty minutes a day is enough."),
    co("note", "Studying for a career switch is a marathon. Aim for <b>about 10 hours a week for "
               "16 weeks</b>: about 1 hour on weekdays and about 2.5 hours on each weekend day. "
               "Consistency beats intensity."),
    h2("Recommended local setup"),
    code("bash", r"""
# 1. Python 3.11+ with an isolated environment
python3 -m venv ~/de-env && source ~/de-env/bin/activate
pip install pandas pyarrow duckdb requests pytest pyspark==3.5.* dbt-duckdb

# 2. Docker Desktop (for Postgres, Kafka and Airflow in containers)
docker run -d --name pg -e POSTGRES_PASSWORD=pg -p 5432:5432 postgres:16

# 3. Free practice databases / clouds
#   - DuckDB: a warehouse in a file, perfect for SQL practice (no server needed)
#   - BigQuery sandbox: free, no credit card, 10 GB storage / 1 TB queries per month
#   - Snowflake / Databricks: 30-day / community trials
""", "one-time setup"),

    # ------------------------------------------------------------------ 1
    ch("Your Unfair Advantage: Control-M to Data Engineering",
       "Most career switchers into data engineering start from analytics and have never run "
       "production. You start from production and need to learn the data side. That is "
       "the easier direction."),
    p("A data engineer builds and runs the systems that move data from where it is produced "
      "to where it is used, reliably, on time and correct. Roughly half of that is "
      "<b>workload automation and operations</b>, which you have done for five years. The other "
      "half is <b>data</b>: SQL, modelling, distributed processing and cloud warehouses. This "
      "guide concentrates on that half."),
    h2("Concept mapping: what you already know"),
    tbl([
        ["Control-M concept", "Data engineering equivalent", "Where to learn it"],
        ["Job", "Task (Airflow), op/asset (Dagster), node (dbt)", "Ch. 9"],
        ["Folder / SMART Folder / Sub-folder", "DAG (directed acyclic graph) / TaskGroup", "Ch. 9"],
        ["In / Out conditions", "Task dependencies (>>), Datasets / data-aware scheduling",
         "Ch. 9"],
        ["File Watcher job", "Sensor (FileSensor, S3KeySensor, GCSObjectExistenceSensor)", "Ch. 9"],
        ["Calendars, rule-based calendars", "Cron schedules, Timetables", "Ch. 9"],
        ["Order date (ODATE), %%ODATE", "Logical date / data interval, {{ ds }}", "Ch. 9"],
        ["Rerun / Force OK / Hold / Free", "Clear task / Mark success / Pause DAG", "Ch. 9"],
        ["Quantitative resources", "Pools, max_active_tasks, concurrency slots", "Ch. 9"],
        ["Control resources (exclusive)", "max_active_runs=1, mutex patterns", "Ch. 9"],
        ["Agents / agentless hosts", "Executors and workers (Celery, Kubernetes)", "Ch. 9"],
        ["SLA Management, BIM", "SLAs, freshness checks, data observability", "Ch. 14"],
        ["Automation API (jobs-as-code JSON)", "DAGs as Python in Git, CI/CD", "Ch. 9, 15"],
        ["Cyclic jobs", "Frequent schedules, micro-batches, streaming", "Ch. 12"],
        ["Variables %%VAR, auto-edit", "Jinja templating, Airflow Variables, params", "Ch. 9"],
        ["Control-M for Databases / Hadoop / ETL plug-ins",
         "Operators and provider packages", "Ch. 9"],
        ["Archived job output / sysout", "Task logs, centralised logging, lineage", "Ch. 14"],
    ], [1.6, 2.2, 0.7]),
    co("bridge", [
        "Every row in this table is a sentence for your interviews: <i>\"In Control-M I "
        "managed X; the Airflow equivalent is Y and here is how they differ.\"</i> Hiring managers "
        "are looking for people who understand <b>why</b> orchestration exists. You can explain "
        "failure handling, reruns, dependencies and SLAs from first-hand experience, which "
        "most junior candidates can't.",
    ], "Turn the table into talking points"),
    h2("The real gaps to close"),
    tbl([
        ["Skill", "Why it matters", "Priority"],
        ["SQL (advanced)", "About 60% of day-to-day DE work. Every interview has a SQL round.",
         "Critical"],
        ["Python for data", "Ingestion, APIs, transformations, testing, glue code.", "Critical"],
        ["Data modelling", "Star schemas, SCDs, grain. Separates engineers from scripters.",
         "High"],
        ["Cloud warehouse", "BigQuery / Snowflake / Redshift / Databricks: where data lives.",
         "High"],
        ["Orchestration (Airflow)", "You already have about 70% of this. Learn the Python API.",
         "Medium (head start)"],
        ["dbt", "The industry-standard SQL transformation tool.", "High"],
        ["Spark", "Distributed processing for big volumes. Asked in most mid-size+ roles.",
         "High"],
        ["Streaming (Kafka)", "Real-time pipelines. Often a plus, sometimes required.", "Medium"],
        ["Data quality / governance", "Tests, contracts, lineage, PII.", "Medium"],
        ["Docker, Git, CI/CD, Terraform", "You probably know parts. Polish them.", "Medium"],
    ], [1.3, 3, 0.9]),
    h2("Self-assessment (fill in now, then again at week 16)"),
    tbl([
        ["Area", "Week 0 (1-5)", "Week 8 (1-5)", "Week 16 (1-5)"],
        ["SQL: joins, aggregation", "", "", ""],
        ["SQL: window functions, CTEs", "", "", ""],
        ["Python: files, APIs, pandas", "", "", ""],
        ["Dimensional modelling", "", "", ""],
        ["Airflow DAG authoring", "", "", ""],
        ["dbt", "", "", ""],
        ["Spark / PySpark", "", "", ""],
        ["Kafka / streaming", "", "", ""],
        ["One cloud platform", "", "", ""],
        ["Git, Docker, CI/CD", "", "", ""],
    ], [2.2, 1, 1, 1]),
    cards("Career framing", [
        ("What does a data engineer do, in one sentence?",
         "Builds and operates reliable, scalable systems that collect, store, transform and serve "
         "data so analysts, data scientists and applications can trust and use it."),
        ("What is the Airflow equivalent of a Control-M Folder?",
         "A <b>DAG</b>. Jobs map to <b>tasks</b>; in/out conditions map to task dependencies "
         "(<font face='Mono'>a &gt;&gt; b</font>)."),
        ("What is the Airflow equivalent of a Control-M File Watcher?",
         "A <b>Sensor</b>, e.g. FileSensor, S3KeySensor or GCSObjectExistenceSensor. Use "
         "<font face='Mono'>mode='reschedule'</font> or deferrable sensors so they don't hold a "
         "worker slot."),
        ("What is the Airflow equivalent of Control-M's ODATE?",
         "The <b>logical date</b> / data interval: the period a run is responsible for. In "
         "templates it's {{ ds }} or {{ data_interval_start }}."),
        ("Which Control-M feature maps to Airflow pools?",
         "<b>Quantitative resources</b>. Both cap how many jobs can use a shared resource "
         "(e.g. DB connections) at once."),
        ("Your biggest transferable strength?",
         "Production operations: dependency management, failure handling, reruns, SLAs, "
         "monitoring, change management, incident response, and talking to stakeholders "
         "when things break."),
    ]),

    # ------------------------------------------------------------------ 2
    ch("The 16-Week Roadmap",
       "A realistic plan at about 10 hours a week. Every phase ends with something you can show."),
    tbl([
        ["Week", "Focus", "Deliverable (push to GitHub)"],
        ["1-2", "SQL fundamentals: SELECT, joins, GROUP BY, NULLs, CTEs",
         "50 solved problems (LeetCode SQL 50 / DataLemur / StrataScratch)"],
        ["3", "Advanced SQL: window functions, dedupe, MERGE, gaps-and-islands",
         "README of 20 'pattern' queries with explanations"],
        ["4", "Python for data: files, generators, requests, pandas, logging, pytest",
         "API-to-CSV ingestion script with tests"],
        ["5", "Data modelling: Kimball, star schema, grain, SCD types",
         "Star schema diagram + DDL for a retail dataset"],
        ["6", "Storage and warehouses: Parquet, partitioning, BigQuery/Snowflake",
         "Load public data to BigQuery sandbox; partitioned + clustered table"],
        ["7", "Pipeline patterns: incremental loads, idempotency, CDC, backfills",
         "Incremental loader with watermark table"],
        ["8", "Airflow (your head start): DAGs, sensors, XCom, pools, backfills",
         "Dockerised Airflow running Project 1 end-to-end"],
        ["9", "dbt: models, tests, snapshots, incremental, docs",
         "dbt project with staging/marts layers + tests + docs site"],
        ["10-11", "Spark / PySpark: DataFrames, joins, partitions, skew, Spark SQL",
         "PySpark job on 10M+ rows; write-up of tuning choices"],
        ["12", "Streaming: Kafka concepts, producers/consumers, Structured Streaming",
         "Kafka to Spark streaming demo in docker-compose"],
        ["13", "Cloud deep dive (pick ONE: AWS, GCP or Azure) + IAM + cost",
         "Project 1 deployed on cloud; Terraform for buckets/datasets"],
        ["14", "Data quality, observability, CI/CD, Docker",
         "GitHub Actions running pytest + dbt build on every PR"],
        ["15", "Portfolio polish: Control-M to Airflow converter (Project 2)",
         "Blog post / LinkedIn article about your migration tool"],
        ["16", "Interview prep: SQL drills, system design, STAR stories, resume",
         "Resume v2, 6 STAR stories, 3 mock interviews"],
    ], [0.6, 2.4, 2.4]),
    co("tip", "Apply from <b>week 10</b>, not week 16. Interviews are a skill in themselves, and "
              "the first few are practice. Internal transfer is often the fastest route: if your "
              "current company has a data team, tell them now that you're learning and offer to "
              "take on their scheduling and orchestration work."),
    h3("Certification options (optional but useful for career switchers)"),
    ul("<b>Google Cloud Professional Data Engineer</b>: well respected, covers BigQuery, "
       "Dataflow, Pub/Sub and Composer.",
       "<b>AWS Certified Data Engineer - Associate (DEA-C01)</b>: covers Glue, Redshift, Kinesis, "
       "EMR and Athena.",
       "<b>Microsoft Certified: Fabric Data Engineer Associate (DP-700)</b>: the successor to "
       "the retired DP-203.",
       "<b>Databricks Certified Data Engineer Associate</b>: Spark, Delta Lake, lakehouse.",
       "<b>SnowPro Core</b> (Snowflake) and the <b>dbt Analytics Engineering</b> certification."),
    co("note", "Pick <b>one</b> cloud certification that matches the job postings in your city. "
               "A certification gets you past the resume filter; projects get you through the "
               "interview."),

    # ------------------------------------------------------------------ 3
    ch("Data Engineering Foundations",
       "The vocabulary and mental model everything else hangs on."),
    h2("The data lifecycle"),
    flow([
        ("Sources", "OLTP DBs, APIs, files, SaaS, events, logs"),
        ("Ingest", "batch extract, CDC, streaming"),
        ("Store (Lake)", "S3 / GCS / ADLS raw files: Parquet, JSON"),
        ("Transform", "clean, join, model: SQL, dbt, Spark"),
        ("Warehouse", "BigQuery, Snowflake, Redshift, Databricks"),
        ("Serve", "BI dashboards, ML features, reverse ETL, APIs"),
    ], "ORCHESTRATION (Airflow / Control-M)  ·  DATA QUALITY  ·  SECURITY  ·  "
       "OBSERVABILITY  ·  GOVERNANCE run across every stage"),
    h2("Batch vs streaming"),
    tbl([
        ["", "Batch", "Streaming"],
        ["Latency", "Minutes to hours (e.g. nightly)", "Milliseconds to seconds"],
        ["Unit of work", "A bounded dataset (yesterday's orders)",
         "An unbounded stream of events"],
        ["Tools", "Airflow + SQL/dbt/Spark, Control-M", "Kafka, Flink, Spark Structured "
                                                       "Streaming, Kinesis, Pub/Sub"],
        ["Complexity", "Lower: easy to rerun and backfill",
         "Higher: state, late data, exactly-once"],
        ["Use when", "Reporting, finance, most analytics",
         "Fraud detection, real-time personalisation, monitoring"],
    ], [1, 2, 2]),
    co("bridge", "Every Control-M batch window you've managed (the nightly cycle, "
                 "upstream-before-downstream ordering, the 6 a.m. reporting SLA) is classic "
                 "<b>batch data engineering</b>. Cyclic jobs every 5 minutes are "
                 "<b>micro-batch</b>, a step toward streaming."),
    h2("ETL vs ELT"),
    p("<b>ETL</b> (Extract, Transform, Load) transforms data <i>before</i> loading it into the "
      "warehouse, traditionally with tools like Informatica, DataStage or SSIS, because "
      "warehouse compute used to be expensive. <b>ELT</b> loads raw data first and transforms "
      "<i>inside</i> the warehouse with SQL (usually dbt), because cloud warehouses separate "
      "cheap storage from elastic compute. Most modern stacks are ELT: Fivetran/Airbyte to "
      "load, dbt to transform, Airflow to orchestrate."),
    h2("OLTP vs OLAP"),
    tbl([
        ["", "OLTP (transactional)", "OLAP (analytical)"],
        ["Purpose", "Run the business: place an order", "Analyse the business: revenue by month"],
        ["Examples", "PostgreSQL, MySQL, Oracle, SQL Server",
         "BigQuery, Snowflake, Redshift, ClickHouse"],
        ["Queries", "Many small reads/writes by key", "Few large scans and aggregations"],
        ["Storage", "Row-oriented", "Column-oriented"],
        ["Schema", "Normalised (3NF)", "Denormalised (star schema)"],
    ], [1, 2, 2]),
    h2("Lake, warehouse, lakehouse and the medallion architecture"),
    ul("<b>Data lake</b>: cheap object storage (S3/GCS/ADLS) holding files in any format. "
       "Flexible, but it turns into a swamp without governance.",
       "<b>Data warehouse</b>: structured, SQL-first, strongly governed, fast for analytics.",
       "<b>Lakehouse</b>: open table formats (Delta Lake, Apache Iceberg, Apache Hudi) add ACID "
       "transactions, schema enforcement and time travel to files in the lake, so you get "
       "warehouse behaviour on lake storage."),
    tbl([
        ["Layer", "Also called", "Contents", "Rule"],
        ["Bronze", "raw / landing", "Data exactly as received, plus load metadata",
         "Append-only, never edited; lets you replay"],
        ["Silver", "staging / cleaned", "Typed, deduplicated, conformed columns",
         "One row per real-world entity/event"],
        ["Gold", "marts / presentation", "Business-level facts, dimensions and aggregates",
         "Shaped for consumers and BI"],
    ], [0.7, 1.1, 2.2, 2]),
    h2("Roles around the data engineer"),
    tbl([
        ["Role", "Main focus", "Main tools"],
        ["Data engineer", "Pipelines, platforms, reliability, scale",
         "Python, SQL, Spark, Airflow, cloud"],
        ["Analytics engineer", "Clean, modelled, tested data for analysis", "SQL, dbt, warehouse"],
        ["Data analyst", "Answer business questions, dashboards", "SQL, BI (Looker, Power BI)"],
        ["Data scientist / ML engineer", "Models, experiments, ML in production",
         "Python, notebooks, MLflow"],
        ["Platform / DataOps engineer", "Infrastructure, CI/CD, orchestration platform",
         "Kubernetes, Terraform, Control-M/Airflow admin"],
    ], [1.4, 2, 1.8]),
    co("tip", "<b>DataOps / Data Platform Engineer</b> roles are a natural bridge for you. They "
              "value orchestration administration directly. Look for titles like \"Data Platform "
              "Engineer\", \"DataOps Engineer\" and \"Workload Automation Engineer, Data\"."),
    cards("Foundations", [
        ("ETL vs ELT?",
         "ETL transforms before loading (in an external engine). ELT loads raw data first and "
         "transforms inside the warehouse with SQL. ELT is the modern default because cloud "
         "warehouse compute is elastic and raw data is kept for replay."),
        ("OLTP vs OLAP?",
         "OLTP: transactional, many small row-level reads/writes, row storage, normalised. "
         "OLAP: analytical, large scans/aggregations, columnar storage, denormalised."),
        ("Why are analytical databases columnar?",
         "Queries touch few columns over many rows. Columnar storage reads only the needed "
         "columns and compresses well (similar values sit together), so there is far less I/O."),
        ("What is a lakehouse?",
         "Lake storage (cheap files in object storage) plus an open table format (Delta, "
         "Iceberg, Hudi) that adds ACID transactions, schema enforcement and time travel."),
        ("Medallion architecture?",
         "Bronze (raw, as received) to Silver (cleaned, typed, deduplicated) to Gold "
         "(business-level marts). Each layer increases quality and structure."),
        ("Batch vs streaming: when do you choose streaming?",
         "When the business value depends on low latency (seconds), e.g. fraud, alerting, "
         "real-time personalisation. Otherwise batch is simpler, cheaper and easier to rerun."),
        ("What are the 'V's of big data?",
         "Volume (size), Velocity (speed of arrival), Variety (formats), plus Veracity "
         "(trustworthiness) and Value."),
        ("Name the stages of the data lifecycle.",
         "Generation/source, ingestion, storage, transformation, serving. Orchestration, "
         "security, quality and governance cut across all of them."),
    ]),
]
