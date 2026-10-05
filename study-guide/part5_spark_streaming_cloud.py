"""Chapters: Apache Spark; streaming and Kafka; cloud platforms."""

from content_helpers import c, ch, h2, h3, p, ul, ol, code, co, tbl, cards, flow

BLOCKS = [
    # ------------------------------------------------------------------ spark
    ch("Distributed Processing with Apache Spark",
       "When data outgrows one machine, Spark splits the work across a cluster. It's asked "
       "about in most mid-size and large company interviews."),
    h2("Architecture"),
    flow([
        ("Driver", "SparkSession; builds the plan; DAG + task scheduler"),
        ("Cluster manager", "YARN, Kubernetes, Standalone, Databricks"),
        ("Executors", "JVMs on worker nodes; run tasks; cache data"),
        ("Tasks", "one per partition, run in parallel on cores"),
    ]),
    tbl([
        ["Term", "Definition"],
        ["Application", "Your program: one driver plus its executors"],
        ["Job", "Triggered by each action (count, write, collect)"],
        ["Stage", "A set of tasks with no shuffle between them; a new stage starts at every "
                  "shuffle boundary"],
        ["Task", "The unit of work on one partition, run on one executor core"],
        ["Partition", "A chunk of the data; the unit of parallelism"],
    ], [1, 4]),
    h2("Lazy evaluation: transformations vs actions"),
    p("Transformations (select, filter, join, groupBy) only build a <b>logical plan</b>. "
      "Nothing runs until an <b>action</b> (count, show, collect, write). Spark's <b>Catalyst</b> "
      "optimiser then rewrites the whole plan (pushes filters down, prunes columns, picks join "
      "strategies) and <b>Tungsten</b> generates efficient code."),
    tbl([
        ["Narrow transformations (no shuffle)", "Wide transformations (shuffle)"],
        ["select, filter/where, withColumn, map, union, coalesce",
         "groupBy, join (non-broadcast), distinct, orderBy, repartition, window "
         "partitionBy"],
        ["Each output partition depends on one input partition",
         "Data is redistributed across the network by key: expensive"],
    ], [1, 1]),
    h2("A complete PySpark job"),
    code("python", r"""
from pyspark.sql import SparkSession, Window
from pyspark.sql import functions as F

spark = (SparkSession.builder
         .appName("daily_orders")
         .config("spark.sql.adaptive.enabled", "true")          # AQE (default on in 3.2+)
         .config("spark.sql.shuffle.partitions", "200")
         .getOrCreate())

run_date = "2024-03-10"

orders = (spark.read.parquet("s3://lake/bronze/orders/")
          .where(F.col("dt") == run_date))                       # partition pruning
customers = spark.read.parquet("s3://lake/silver/customers/")

# 1) clean + dedupe: keep latest version of each order
w = Window.partitionBy("order_id").orderBy(F.col("updated_at").desc())
clean = (orders
         .withColumn("status", F.lower(F.trim("status")))
         .withColumn("rn", F.row_number().over(w))
         .where("rn = 1").drop("rn")
         .where(F.col("amount").isNotNull()))

# 2) enrich: customers is small -> broadcast join avoids shuffling the big side
enriched = clean.join(F.broadcast(customers.select("customer_id", "city", "segment")),
                      on="customer_id", how="left")

# 3) aggregate
daily = (enriched
         .groupBy("city", "segment")
         .agg(F.countDistinct("customer_id").alias("buyers"),
              F.sum("amount").alias("revenue"),
              F.avg("amount").alias("avg_order_value"))
         .withColumn("dt", F.lit(run_date)))

# 4) idempotent write: overwrite only this run's partition
spark.conf.set("spark.sql.sources.partitionOverwriteMode", "dynamic")
(daily.repartition(1)                                            # few rows -> one file
      .write.mode("overwrite")
      .partitionBy("dt")
      .parquet("s3://lake/gold/daily_city_revenue/"))
""", "read, dedupe, broadcast join, aggregate, write"),
    h3("The same thing in Spark SQL"),
    code("python", r"""
orders.createOrReplaceTempView("orders")
spark.sql('''
    SELECT city, SUM(amount) AS revenue
    FROM orders o JOIN customers c USING (customer_id)
    WHERE dt = '2024-03-10'
    GROUP BY city
''').show()
""", "Spark SQL"),
    h2("Performance tuning: what interviewers ask"),
    tbl([
        ["Problem", "Symptom", "Fix"],
        ["Shuffle-heavy joins", "Huge 'shuffle write' in the Spark UI; slow stages",
         "Broadcast the small table (default threshold 10 MB; raise "
         "spark.sql.autoBroadcastJoinThreshold carefully); filter and aggregate before the "
         "join"],
        ["Data skew", "One task runs far longer than others in a stage",
         "AQE skew-join handling; salting hot keys; isolate and handle hot keys separately"],
        ["Wrong partition count", "Too few: idle cores, OOM. Too many: scheduling overhead, "
                                  "tiny files",
         "Aim for 100-200 MB per partition; tune spark.sql.shuffle.partitions; let AQE "
         "coalesce"],
        ["Small output files", "Thousands of KB-sized files",
         "coalesce() / repartition() before write; compaction"],
        ["Recomputation", "The same lineage computed repeatedly",
         "cache()/persist() a DataFrame reused by several actions, then unpersist()"],
        ["Python UDFs", "Slow row-by-row serialisation between JVM and Python",
         "Use built-in functions; else pandas_udf (vectorised, Arrow)"],
        ["Driver OOM", "collect() on large data", "Never collect big data; write it out instead"],
    ], [1.2, 1.9, 2.9]),
    code("python", r"""
# Salting a skewed key: spread the hot customer across N sub-keys
N = 16
big = big_df.withColumn("salt", (F.rand() * N).cast("int"))
small = (small_df
         .withColumn("salt", F.explode(F.array([F.lit(i) for i in range(N)]))))
joined = big.join(small, on=["customer_id", "salt"]).drop("salt")

# repartition vs coalesce
df.repartition(64, "customer_id")   # full shuffle; can increase or decrease; balances by key
df.coalesce(8)                      # no full shuffle; only decreases; may be unbalanced
""", "salting and repartition vs coalesce"),
    co("tip", ["Open the <b>Spark UI</b> and know your way around it: Jobs, Stages (look for "
               "task duration skew and shuffle read/write), the SQL tab (physical plan, join "
               "strategy) and Executors (GC time, memory).",
               "Describe a tuning story as: <b>symptom, then evidence in the Spark UI, then the "
               "change, then the measured result</b>."]),
    co("bridge", "Spark's driver/executor model is like a Control-M Server dispatching to "
                 "agents, except that a single job is split into thousands of parallel tasks. "
                 "Long-running stragglers are the Spark version of the one job that always "
                 "holds up the batch window."),
    cards("Spark", [
        ("Spark driver vs executor?",
         "The driver runs your main program, builds the plan and schedules tasks. Executors "
         "are worker JVMs that run tasks on partitions and store cached data."),
        ("Transformation vs action?",
         "Transformations are lazy and build the plan (filter, join). Actions trigger execution "
         "and return or write results (count, collect, write)."),
        ("Narrow vs wide transformation?",
         "Narrow: each output partition comes from one input partition, no shuffle (filter, "
         "select). Wide: requires a shuffle across the network (groupBy, join, distinct)."),
        ("What creates a new stage?",
         "A shuffle boundary (wide transformation)."),
        ("What is a broadcast join and when do you use it?",
         "The small table is copied to every executor so the big table isn't shuffled. Use it "
         "when one side is small (by default 10 MB, configurable)."),
        ("What is data skew and how do you fix it?",
         "A few keys hold most of the data, so a few tasks run very long. Fixes: AQE skew join, "
         "salting, broadcast, handling hot keys separately."),
        ("repartition() vs coalesce()?",
         "repartition does a full shuffle and can increase or decrease partitions (balanced). "
         "coalesce only decreases, avoids a full shuffle, and may be unbalanced."),
        ("cache() vs persist()?",
         "cache() is persist() with the default storage level (MEMORY_AND_DISK for "
         "DataFrames). persist() lets you choose the level. Both are lazy until an action."),
        ("What is AQE?",
         "Adaptive Query Execution: re-optimises at runtime using shuffle statistics, "
         "coalescing partitions, switching join strategies and splitting skewed partitions."),
        ("Why avoid Python UDFs?",
         "Each row is serialised between the JVM and Python, and Catalyst can't optimise inside "
         "them. Prefer built-in functions or vectorised pandas_udf."),
        ("RDD vs DataFrame?",
         "RDD: low-level distributed objects with no schema or optimiser. DataFrame: "
         "schema'd rows optimised by Catalyst and Tungsten. Use DataFrames by default."),
        ("What is the Catalyst optimizer?",
         "Spark SQL's optimiser. It turns the logical plan into an optimised physical plan "
         "(predicate pushdown, column pruning, join selection)."),
        ("How is Spark fault tolerant?",
         "Lineage: lost partitions are recomputed from the recorded chain of transformations. "
         "Checkpointing truncates long lineage."),
        ("Ideal partition size?",
         "Roughly 100-200 MB per partition (files of 128 MB-1 GB on disk). Too small adds "
         "overhead; too big causes spills and OOM."),
    ]),

    # ------------------------------------------------------------------ streaming
    ch("Streaming and Apache Kafka",
       "Moving from 'nightly batch' to 'events as they happen'."),
    h2("Kafka core concepts"),
    tbl([
        ["Concept", "Meaning"],
        ["Broker", "A Kafka server. A cluster has several for scale and fault tolerance."],
        ["Topic", "A named stream of records (like a table of events), e.g. orders.v1"],
        ["Partition", "An ordered, append-only log within a topic; the unit of parallelism. "
                      "Ordering is guaranteed only within a partition."],
        ["Offset", "A record's position in a partition. Consumers track the offsets they've "
                   "processed."],
        ["Producer", "Writes records. The record key decides the partition (same key, same "
                     "partition, preserved order)."],
        ["Consumer group", "Consumers sharing the work. Each partition is read by exactly one "
                           "consumer in the group."],
        ["Replication factor", "Copies of each partition across brokers (typically 3). One "
                               "leader, the rest followers (ISR = in-sync replicas)."],
        ["Retention", "How long records are kept (time or size), or log compaction (keep the "
                      "latest value per key)."],
        ["Schema Registry", "Stores Avro/Protobuf/JSON schemas and enforces compatibility "
                            "rules."],
    ], [1.3, 4]),
    h2("Delivery semantics"),
    tbl([
        ["Semantics", "How", "Risk"],
        ["At-most-once", "Commit offset before processing", "Data loss on crash"],
        ["At-least-once", "Process, then commit offset (the default choice)",
         "Duplicates on retry, so make sinks idempotent"],
        ["Exactly-once", "Idempotent producer + transactions (read-process-write within Kafka), "
                         "or at-least-once + idempotent/transactional sink",
         "More complex; end-to-end needs sink support"],
    ], [1.2, 2.8, 1.8]),
    code("python", r"""
# pip install confluent-kafka
import json

from confluent_kafka import Consumer, Producer

producer = Producer({"bootstrap.servers": "localhost:9092",
                     "enable.idempotence": True, "acks": "all"})

def on_delivery(err, msg):
    if err:
        print(f"delivery failed: {err}")

order = {"order_id": 107, "customer_id": 2, "amount": 75.5, "status": "placed"}
producer.produce("orders.v1", key=str(order["customer_id"]),     # key -> partition
                 value=json.dumps(order), callback=on_delivery)
producer.flush()


consumer = Consumer({"bootstrap.servers": "localhost:9092",
                     "group.id": "orders-loader",
                     "auto.offset.reset": "earliest",
                     "enable.auto.commit": False})                # commit manually
consumer.subscribe(["orders.v1"])
try:
    while True:
        msg = consumer.poll(1.0)
        if msg is None:
            continue
        if msg.error():
            print(msg.error()); continue
        record = json.loads(msg.value())
        upsert_order(record)                    # idempotent sink (MERGE on order_id)
        consumer.commit(message=msg)            # at-least-once: commit AFTER processing
finally:
    consumer.close()
""", "Kafka producer and consumer"),
    h2("Stream processing concepts"),
    ul("<b>Event time vs processing time</b>: when the event happened vs when the system saw "
       "it. Analytics should almost always use event time.",
       "<b>Windows</b>: <b>tumbling</b> (fixed, non-overlapping, e.g. every 5 minutes), "
       "<b>sliding/hopping</b> (overlapping, e.g. 10-minute window every 5 minutes), "
       "<b>session</b> (activity separated by a gap of inactivity).",
       "<b>Watermark</b>: how late data may arrive and still be counted. It lets the engine "
       "finalise windows and drop old state.",
       "<b>State and checkpoints</b>: running aggregates are stored as state and checkpointed, "
       "so a restart resumes exactly where it left off.",
       "<b>Engines</b>: Spark Structured Streaming (micro-batch), Apache Flink (true "
       "event-at-a-time, low latency), Kafka Streams, cloud services (Kinesis, Dataflow/Beam)."),
    code("python", r"""
from pyspark.sql import functions as F
from pyspark.sql.types import (DoubleType, LongType, StringType, StructField,
                               StructType, TimestampType)

schema = StructType([
    StructField("order_id", LongType()), StructField("customer_id", LongType()),
    StructField("amount", DoubleType()), StructField("status", StringType()),
    StructField("event_ts", TimestampType()),
])

events = (spark.readStream.format("kafka")
          .option("kafka.bootstrap.servers", "localhost:9092")
          .option("subscribe", "orders.v1")
          .option("startingOffsets", "latest")
          .load()
          .select(F.from_json(F.col("value").cast("string"), schema).alias("o"))
          .select("o.*"))

revenue_5m = (events
              .withWatermark("event_ts", "10 minutes")             # tolerate 10 min lateness
              .groupBy(F.window("event_ts", "5 minutes"), "status")
              .agg(F.sum("amount").alias("revenue"), F.count("*").alias("orders")))

query = (revenue_5m.writeStream
         .outputMode("append")                                       # emit finalised windows
         .format("parquet")
         .option("path", "s3://lake/gold/revenue_5m/")
         .option("checkpointLocation", "s3://lake/_checkpoints/revenue_5m/")
         .trigger(processingTime="1 minute")
         .start())
""", "Spark Structured Streaming from Kafka"),
    co("bridge", "A Control-M cyclic job that runs every 5 minutes and processes 'new files "
                 "since last run' is conceptually a <b>micro-batch with a checkpoint</b>. "
                 "Structured Streaming automates the bookkeeping (offsets, state, exactly-once "
                 "file sink) that you'd otherwise build by hand."),
    cards("Streaming and Kafka", [
        ("Kafka topic vs partition?",
         "A topic is a named stream. Partitions split it into ordered, append-only logs for "
         "parallelism. Ordering is only guaranteed within a partition."),
        ("How does Kafka decide the partition for a record?",
         "By hashing the record key (same key, same partition, so per-key order is kept). "
         "Without a key, the producer spreads records across partitions."),
        ("What is a consumer group?",
         "A set of consumers sharing a topic's partitions. Each partition goes to exactly one "
         "consumer in the group, so the maximum useful parallelism equals the partition count."),
        ("What is an offset?",
         "The position of a record in a partition. Consumers commit offsets to remember their "
         "progress."),
        ("At-least-once vs exactly-once?",
         "At-least-once: process, then commit, so a crash causes duplicates (make sinks "
         "idempotent). Exactly-once: idempotent producers + transactions, or an idempotent / "
         "transactional sink."),
        ("Event time vs processing time?",
         "Event time is when the event occurred (in the payload). Processing time is when the "
         "system handled it. Use event time for correct analytics with late data."),
        ("Tumbling vs sliding vs session window?",
         "Tumbling: fixed, non-overlapping. Sliding: fixed size, overlapping. Session: dynamic "
         "windows closed by an inactivity gap."),
        ("What is a watermark in stream processing?",
         "A threshold of how late events may arrive. Older events are dropped, and windows "
         "before the watermark are finalised and their state freed."),
        ("Why does Kafka use replication factor 3?",
         "Fault tolerance: with min.insync.replicas=2 and acks=all, a write survives one broker "
         "failure without data loss."),
        ("What is log compaction?",
         "A retention mode that keeps at least the latest record per key, useful for "
         "changelog/state topics (e.g. current customer profile)."),
        ("Why use a Schema Registry?",
         "It centralises message schemas (Avro/Protobuf) and enforces compatibility, so "
         "producers can't break consumers with incompatible changes."),
    ]),

    # ------------------------------------------------------------------ cloud
    ch("Cloud Platforms for Data Engineering",
       "Pick one cloud and go deep. The concepts transfer; only the service names change."),
    h2("Service map"),
    tbl([
        ["Need", "AWS", "GCP", "Azure"],
        ["Object storage (lake)", "S3", "Cloud Storage (GCS)", "ADLS Gen2 / Blob"],
        ["Warehouse", "Redshift", "BigQuery", "Synapse / Fabric Warehouse"],
        ["Serverless SQL on files", "Athena", "BigQuery external tables / BigLake",
         "Synapse serverless / Fabric"],
        ["Managed Spark", "EMR, Glue (Spark jobs)", "Dataproc", "Databricks, Synapse Spark, "
                                                              "Fabric"],
        ["Managed ETL / ingestion", "Glue, DMS, AppFlow", "Dataflow (Beam), Datastream, "
                                                           "Data Fusion", "Data Factory"],
        ["Streaming", "Kinesis, MSK (Kafka)", "Pub/Sub, Managed Kafka", "Event Hubs"],
        ["Managed Airflow", "MWAA", "Cloud Composer", "Data Factory Workflow Orchestration "
                                                       "Manager / Fabric"],
        ["Serverless functions", "Lambda", "Cloud Run functions", "Azure Functions"],
        ["Workflow (non-Airflow)", "Step Functions", "Workflows", "Logic Apps / ADF pipelines"],
        ["Catalog / governance", "Glue Data Catalog, Lake Formation", "Dataplex",
         "Microsoft Purview"],
        ["Secrets", "Secrets Manager", "Secret Manager", "Key Vault"],
        ["Identity", "IAM roles/policies", "IAM + service accounts", "Entra ID + RBAC, managed "
                                                                      "identities"],
    ], [1.3, 1.4, 1.5, 1.5]),
    h2("A reference batch architecture on AWS"),
    flow([
        ("Sources", "RDS, SaaS APIs, files via SFTP"),
        ("Ingest", "DMS (CDC), Lambda / Glue jobs"),
        ("S3 bronze", "raw Parquet / JSON, partitioned by date"),
        ("Glue / EMR Spark", "clean to S3 silver (Iceberg)"),
        ("Redshift / Athena", "gold marts via dbt"),
        ("QuickSight", "dashboards"),
    ], "MWAA (Airflow) orchestrates  ·  Glue Data Catalog  ·  CloudWatch alarms  "
       "·  IAM least privilege  ·  KMS encryption"),
    h2("Working with object storage in Python"),
    code("python", r"""
import boto3

s3 = boto3.client("s3")              # credentials come from the IAM role / env, never code

s3.upload_file("daily_revenue.parquet", "acme-data-lake",
               "gold/daily_revenue/dt=2024-03-10/part-000.parquet")

paginator = s3.get_paginator("list_objects_v2")
for page in paginator.paginate(Bucket="acme-data-lake", Prefix="bronze/orders/dt=2024-03-10/"):
    for obj in page.get("Contents", []):
        print(obj["Key"], obj["Size"])

# GCP equivalent:
# from google.cloud import storage
# storage.Client().bucket("acme-data-lake").blob("gold/x.parquet").upload_from_filename("x")
""", "S3 with boto3"),
    code("sql", r"""
-- BigQuery: load Parquet from GCS, then query
LOAD DATA INTO analytics.orders_raw
FROM FILES (format = 'PARQUET', uris = ['gs://acme-data-lake/bronze/orders/dt=2024-03-10/*']);

-- Athena: query S3 files in place through a Glue catalog table
SELECT status, COUNT(*) FROM lake.orders WHERE dt = '2024-03-10' GROUP BY status;
""", "loading and querying lake data"),
    h2("Security and cost basics"),
    ul("<b>Least privilege IAM</b>: each pipeline gets its own role or service account with "
       "only the buckets and datasets it needs.",
       "<b>Encryption</b> at rest (KMS-managed keys) and in transit (TLS). Private networking "
       "(VPC endpoints / Private Service Connect) for sensitive data.",
       "<b>No long-lived keys</b> in code or CI: use workload identity / OIDC federation.",
       "<b>Cost levers</b>: partition and cluster tables, avoid SELECT *, lifecycle policies "
       "(move old data to cold storage), auto-suspend warehouses, spot/preemptible instances "
       "for Spark, budgets and alerts.",
       "<b>Tag everything</b> (team, pipeline, env) so cost can be attributed."),
    co("bridge", "You already know agents, hosts, service accounts, firewall rules and run-as "
                 "users from Control-M. Cloud IAM is the same 'who can run what, where' "
                 "problem, applied to APIs and data."),
    cards("Cloud", [
        ("AWS / GCP / Azure object storage names?",
         "S3 / Cloud Storage (GCS) / ADLS Gen2 (Blob Storage)."),
        ("AWS / GCP / Azure warehouse names?",
         "Redshift / BigQuery / Synapse or Fabric Warehouse (plus Snowflake and Databricks on "
         "all three)."),
        ("What is Athena?",
         "AWS's serverless SQL engine (Trino-based) for querying files in S3 via the Glue Data "
         "Catalog. You pay per data scanned."),
        ("Managed Airflow services?",
         "AWS MWAA, GCP Cloud Composer, and Azure Data Factory Workflow Orchestration Manager "
         "(Fabric also offers Apache Airflow jobs)."),
        ("What is the principle of least privilege?",
         "Grant each identity only the minimum permissions needed for its task, which limits "
         "the blast radius if it's compromised."),
        ("Name three cloud cost levers for data workloads.",
         "Partitioning/clustering to reduce scans; auto-suspend/auto-scale compute; storage "
         "lifecycle tiers; spot instances; avoiding SELECT *."),
        ("GCP streaming ingestion and processing services?",
         "Pub/Sub (messaging) and Dataflow (Apache Beam, unified batch + stream processing)."),
        ("What is AWS Glue?",
         "A serverless data integration service: the Glue Data Catalog (metastore), crawlers, "
         "and Spark/Python ETL jobs."),
    ]),
]
