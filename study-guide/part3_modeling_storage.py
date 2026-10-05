"""Chapters: data modelling; storage, file formats and warehouses."""

from content_helpers import c, ch, h2, h3, p, ul, ol, code, co, tbl, cards, flow

BLOCKS = [
    # ------------------------------------------------------------------ modelling
    ch("Data Modelling",
       "Modelling is what separates a data engineer from someone who moves files around. It "
       "decides whether every downstream query is easy and correct, or painful and wrong."),
    h2("Normalisation (OLTP side)"),
    tbl([
        ["Form", "Rule", "Violation example"],
        ["1NF", "Atomic values; no repeating groups",
         "A 'phones' column holding '555-1, 555-2'"],
        ["2NF", "1NF + every non-key column depends on the whole composite key",
         "order_lines(order_id, product_id, product_name): product_name depends only on "
         "product_id"],
        ["3NF", "2NF + no transitive dependencies (non-key depending on non-key)",
         "customers(id, zip, city): city depends on zip"],
    ], [0.6, 2.4, 2.6]),
    p("Normalisation removes redundancy so <b>writes</b> are safe and consistent. Analytics "
      "does the opposite: it <b>denormalises</b> so <b>reads</b> are simple and fast."),
    h2("Dimensional modelling (Kimball)"),
    p("Kimball's method models a business process as <b>facts</b> (measurements of events) "
      "surrounded by <b>dimensions</b> (the who, what, where and when context). The result is a "
      "<b>star schema</b>."),
    h3("Kimball's four-step design process"),
    ol("<b>Choose the business process</b>: e.g. order fulfilment.",
       "<b>Declare the grain</b>: exactly what one fact row represents, e.g. 'one row per order "
       "line'. This is the most important decision.",
       "<b>Identify the dimensions</b>: date, customer, product, store, promotion.",
       "<b>Identify the facts</b>: quantity, unit price, discount, net amount."),
    code("text", r"""
                        +---------------+
                        |   dim_date    |
                        | date_key (PK) |
                        +-------+-------+
                                |
+---------------+       +-------+---------------+       +-----------------+
| dim_customer  |       |    fct_order_line     |       |   dim_product   |
| customer_key  +-------+ date_key       (FK)   +-------+ product_key (PK)|
| customer_id   |       | customer_key   (FK)   |       | sku, name       |
| name, city    |       | product_key    (FK)   |       | category, brand |
| valid_from/to |       | store_key      (FK)   |       +-----------------+
+---------------+       | order_id  (degenerate)|
                        | quantity, net_amount  |
                        +-------+---------------+
                                |
                        +-------+-------+
                        |   dim_store   |
                        +---------------+
""", "star schema: one fact, many dimensions"),
    h2("Fact table types"),
    tbl([
        ["Type", "Grain", "Example", "Behaviour"],
        ["Transaction", "One row per event", "Order line, payment, click",
         "Insert-only; most common"],
        ["Periodic snapshot", "One row per entity per period", "Daily account balance, "
         "month-end inventory", "Regular, predictable rows; semi-additive measures"],
        ["Accumulating snapshot", "One row per process instance",
         "Order lifecycle: placed, paid, shipped, delivered dates",
         "Row updated as milestones complete"],
        ["Factless", "Event with no measures", "Student attendance, promotion coverage",
         "Count rows to analyse"],
    ], [1.2, 1.3, 1.8, 1.7]),
    h3("Additivity of measures"),
    ul("<b>Additive</b>: can be summed across every dimension (sales amount, quantity).",
       "<b>Semi-additive</b>: can be summed across some dimensions but not time (account "
       "balance, inventory level: you average them or take the last value over time).",
       "<b>Non-additive</b>: ratios and percentages. Store the numerator and denominator and "
       "compute the ratio at query time."),
    h2("Dimensions"),
    ul("<b>Surrogate key</b>: a warehouse-generated key (integer or hash) independent of the "
       "source system's <b>natural/business key</b>. It's needed for SCD Type 2 history and "
       "for combining multiple sources.",
       "<b>Conformed dimension</b>: shared by many fact tables with the same meaning (one "
       "dim_customer used by sales, returns and support facts), which enables drill-across.",
       "<b>Degenerate dimension</b>: a dimension key with no table of its own, stored on the "
       "fact (order_id, invoice number).",
       "<b>Junk dimension</b>: groups low-cardinality flags (is_gift, payment_type) into one "
       "small dimension.",
       "<b>Role-playing dimension</b>: one dimension used several ways (dim_date as order_date, "
       "ship_date, delivery_date).",
       "<b>Date dimension</b>: pre-built calendar with day_of_week, is_holiday, fiscal_quarter "
       "and so on. Every warehouse has one."),
    co("bridge", "Control-M calendars (working days, holidays, fiscal periods) are essentially a "
                 "<b>date dimension</b>. Your experience building rule-based calendars "
                 "translates directly into building and explaining a dim_date table."),
    h2("Slowly Changing Dimensions (SCD)"),
    p("Dimension attributes change: a customer moves city. How do you keep history?"),
    tbl([
        ["Type", "Strategy", "History?", "Example"],
        ["0", "Retain original; never update", "No", "Original signup channel"],
        ["1", "Overwrite in place", "No (current only)", "Fixing a typo in a name"],
        ["2", "Add a new row; close the old one with valid_from / valid_to / is_current",
         "Full", "Customer city for sales-by-region over time"],
        ["3", "Add a 'previous_value' column", "Limited (one prior)", "Previous sales territory"],
        ["4", "Separate history (mini-dimension) table", "Full, separate", "Rapidly changing "
                                                                          "attributes"],
        ["6", "1 + 2 + 3 hybrid: SCD2 rows plus a current-value column on every row", "Full",
         "Report by historical or current region"],
    ], [0.5, 2.6, 1.1, 1.8]),
    code("sql", r"""
-- SCD Type 2 in two steps (works in most warehouses).
-- Step 1: close the current row for customers whose tracked attributes changed
UPDATE dim_customer d
SET    valid_to = CURRENT_TIMESTAMP, is_current = FALSE
FROM   stg_customer s
WHERE  d.customer_id = s.customer_id
  AND  d.is_current
  AND  (d.city <> s.city OR d.segment <> s.segment);

-- Step 2: insert a new current row for changed AND brand-new customers
INSERT INTO dim_customer
       (customer_key, customer_id, name, city, segment, valid_from, valid_to, is_current)
SELECT md5(s.customer_id || '|' || CAST(CURRENT_TIMESTAMP AS VARCHAR)),
       s.customer_id, s.name, s.city, s.segment,
       CURRENT_TIMESTAMP, TIMESTAMP '9999-12-31', TRUE
FROM   stg_customer s
LEFT JOIN dim_customer d
       ON d.customer_id = s.customer_id AND d.is_current
WHERE  d.customer_id IS NULL;   -- no current row: new customer, or row just closed above
""", "SCD Type 2"),
    co("note", "In practice you rarely hand-write SCD2: <b>dbt snapshots</b> (Chapter 10) "
               "generate exactly this logic. But interviewers often ask you to explain or "
               "write it, so know the two steps."),
    code("sql", r"""
-- Point-in-time join: attach the customer's city AS IT WAS when the order happened
SELECT f.order_id, f.order_ts, d.city
FROM fct_orders f
JOIN dim_customer d
  ON d.customer_id = f.customer_id
 AND f.order_ts >= d.valid_from
 AND f.order_ts <  d.valid_to;
""", "querying SCD2 history"),
    h2("Star vs snowflake vs One Big Table vs Data Vault"),
    tbl([
        ["Approach", "Shape", "Pros", "Cons"],
        ["Star schema", "Fact + denormalised dimensions", "Simple, fast joins, BI-friendly",
         "Some redundancy in dimensions"],
        ["Snowflake schema", "Dimensions normalised into sub-dimensions",
         "Less redundancy", "More joins, harder for analysts"],
        ["One Big Table (OBT)", "Everything pre-joined into one wide table",
         "Fastest and simplest to query in columnar DBs", "Duplication; harder to maintain "
                                                          "history"],
        ["Data Vault 2.0", "Hubs (keys), Links (relationships), Satellites (attributes + "
                           "history)", "Auditable, parallel loading, absorbs source change",
         "Complex; still needs marts on top"],
        ["Inmon (3NF EDW)", "Normalised enterprise warehouse feeding data marts",
         "Single integrated source of truth", "Slow to build"],
    ], [1.2, 1.9, 1.6, 1.5]),
    co("tip", "Asked to 'design a data model for X'? Start with: <b>business process, then "
              "grain, then dimensions, then facts</b>. State the grain out loud in one sentence. "
              "Then mention how you'd handle history (SCD2) and late-arriving data. That "
              "structure alone puts you ahead of most candidates."),
    cards("Data modelling", [
        ("What is the grain of a fact table?",
         "Exactly what one row represents, e.g. 'one row per order line per day'. Declare it "
         "before choosing dimensions and facts."),
        ("Fact vs dimension?",
         "Facts are numeric measurements of business events (amount, quantity). Dimensions hold "
         "descriptive context used to filter and group (customer, product, date)."),
        ("Star vs snowflake schema?",
         "Star: denormalised dimensions joined directly to the fact. Snowflake: dimensions "
         "normalised into sub-tables, which means more joins."),
        ("What is a surrogate key and why use one?",
         "A warehouse-generated key independent of source IDs. It enables SCD2 (many rows per "
         "natural key), merges multiple sources and insulates you from source key changes."),
        ("SCD Type 1 vs Type 2?",
         "Type 1 overwrites (no history). Type 2 inserts a new row and closes the old one with "
         "valid_from / valid_to / is_current (full history)."),
        ("What is a conformed dimension?",
         "A dimension with identical meaning and keys shared across multiple fact tables, which "
         "enables consistent cross-process analysis."),
        ("Three types of fact tables?",
         "Transaction (one row per event), periodic snapshot (one row per entity per period), "
         "accumulating snapshot (one row per process instance, updated at milestones)."),
        ("What is a semi-additive measure?",
         "One that can be summed across some dimensions but not time, e.g. account balance or "
         "inventory level."),
        ("What is a degenerate dimension?",
         "A dimension attribute stored directly on the fact with no dimension table, e.g. "
         "order_number."),
        ("What does 3NF guarantee?",
         "No repeating groups (1NF), no partial dependency on a composite key (2NF), no "
         "transitive dependency between non-key columns (3NF)."),
        ("How do you join facts to an SCD2 dimension?",
         "On the natural key AND event_time >= valid_from AND event_time < valid_to (a "
         "point-in-time join), or store the surrogate key on the fact at load time."),
        ("Data Vault's three core table types?",
         "Hubs (unique business keys), Links (relationships between hubs), Satellites "
         "(descriptive attributes with history)."),
    ]),

    # ------------------------------------------------------------------ storage
    ch("Storage, File Formats and Warehouses",
       "Where data lives, and how its physical layout decides cost and speed."),
    h2("Row vs columnar storage"),
    code("text", r"""
Table:  id | name  | city   | amount
         1 | Asha  | Pune   | 120
         2 | Ben   | Leeds  |  50

Row storage (CSV, Postgres):   [1,Asha,Pune,120] [2,Ben,Leeds,50]
Columnar (Parquet, BigQuery):  [1,2] [Asha,Ben] [Pune,Leeds] [120,50]

SELECT SUM(amount) -> columnar reads ONE column block; row storage reads every byte.
""", "why analytics loves columns"),
    h2("File formats"),
    tbl([
        ["Format", "Layout", "Schema", "Splittable / compressible", "Best for"],
        ["CSV", "Row, text", "None (all strings)", "Poor types; gzip isn't splittable",
         "Exchange with humans and legacy systems"],
        ["JSON / JSONL", "Row, text", "Self-describing, nested", "Verbose; JSONL is splittable",
         "APIs, semi-structured events"],
        ["Avro", "Row, binary", "Embedded schema with evolution rules", "Yes / yes",
         "Kafka messages, write-heavy ingestion"],
        ["Parquet", "Columnar, binary", "Embedded, typed, nested", "Yes / excellent",
         "Analytics, data lakes (the default)"],
        ["ORC", "Columnar, binary", "Embedded, typed", "Yes / excellent", "Hive ecosystem"],
    ], [0.8, 1, 1.4, 1.6, 1.7]),
    p("Parquet stores data in <b>row groups</b>, each holding one <b>column chunk</b> per "
      "column with min/max statistics. Engines use those statistics to skip row groups "
      "(<b>predicate pushdown</b>) and read only the requested columns (<b>projection "
      "pushdown</b>). Snappy compression is the usual default; ZSTD gives better ratios."),
    code("python", r"""
import pyarrow as pa
import pyarrow.dataset as ds
import pyarrow.parquet as pq

table = pa.Table.from_pylist([
    {"order_id": 101, "dt": "2024-03-01", "country": "IN", "amount": 120.0},
    {"order_id": 102, "dt": "2024-03-01", "country": "UK", "amount": 80.0},
    {"order_id": 103, "dt": "2024-03-02", "country": "IN", "amount": 50.0},
])

# Hive-style partitioning: lake/orders/dt=2024-03-01/country=IN/part-0.parquet
pq.write_to_dataset(table, root_path="lake/orders",
                    partition_cols=["dt", "country"], compression="zstd")

# Reading back with a filter: only the dt=2024-03-01 folders are opened
dataset = ds.dataset("lake/orders", format="parquet", partitioning="hive")
print(dataset.to_table(filter=ds.field("dt") == "2024-03-01").to_pandas())
""", "partitioned Parquet with PyArrow"),
    h2("Partitioning, clustering and the small-files problem"),
    ul("<b>Partitioning</b> splits a table physically by a column, usually a date. Queries "
       "filtering on it skip whole partitions. Choose a <b>low-to-medium cardinality</b> column "
       "you filter on constantly. Never partition by user_id.",
       "<b>Clustering / sort keys / Z-ordering</b> sort data <i>within</i> partitions by "
       "frequently filtered or joined columns, so min/max statistics prune more blocks.",
       "<b>Small-files problem</b>: thousands of tiny files (common with streaming or "
       "over-partitioning) kill performance because every file has open and metadata overhead. "
       "Fix it with <b>compaction</b> (OPTIMIZE in Delta, rewrite_data_files in Iceberg), "
       "coalescing before writing, and aiming for roughly 128 MB to 1 GB files."),
    code("sql", r"""
-- BigQuery: partition by day, cluster by common filters, force partition filters
CREATE TABLE analytics.orders
(
  order_id     INT64,
  customer_id  INT64,
  country      STRING,
  status       STRING,
  amount       NUMERIC,
  order_ts     TIMESTAMP
)
PARTITION BY DATE(order_ts)
CLUSTER BY country, customer_id
OPTIONS (require_partition_filter = TRUE, partition_expiration_days = 1095);

-- Snowflake equivalent idea: micro-partitions are automatic; add a clustering key
-- ALTER TABLE orders CLUSTER BY (TO_DATE(order_ts), country);
""", "partitioned + clustered table"),
    h2("Cloud data warehouses compared"),
    tbl([
        ["", "BigQuery (GCP)", "Snowflake (multi-cloud)", "Redshift (AWS)",
         "Databricks SQL"],
        ["Architecture", "Serverless; storage and compute separated",
         "Virtual warehouses (compute) over shared storage",
         "Clusters or Serverless; RA3 separates storage", "Lakehouse on Delta Lake"],
        ["Scaling", "Automatic (slots)", "Resize / multi-cluster warehouses",
         "Resize, concurrency scaling", "SQL warehouses, autoscaling"],
        ["Pricing", "On-demand per TB scanned or slot capacity",
         "Credits per second of warehouse runtime", "Per node-hour or RPU",
         "DBUs + cloud compute"],
        ["Layout tuning", "Partition + cluster", "Micro-partitions + clustering keys",
         "Dist key + sort key", "Partitioning, Z-order / liquid clustering"],
        ["Standout features", "BQML, streaming inserts, huge scale",
         "Time Travel, zero-copy cloning, data sharing", "Deep AWS integration, Spectrum",
         "Unified with Spark, ML, Unity Catalog"],
    ], [1, 1.35, 1.45, 1.35, 1.3]),
    h2("Open table formats (lakehouse)"),
    p("Plain Parquet files can't do ACID updates: two writers can corrupt a table, and a "
      "failed job leaves half-written files. Table formats add a <b>transaction log / metadata "
      "layer</b> on top of Parquet:"),
    ul("<b>Delta Lake</b> (Databricks): _delta_log JSON commits; MERGE, time travel, OPTIMIZE, "
       "Z-ORDER.",
       "<b>Apache Iceberg</b> (Netflix origin): metadata tree of snapshots and manifests; hidden "
       "partitioning and partition evolution. Broad engine support (Spark, Trino, Snowflake, "
       "BigQuery, Athena).",
       "<b>Apache Hudi</b> (Uber origin): optimised for upserts and incremental pulls "
       "(copy-on-write vs merge-on-read)."),
    code("python", r"""
# Delta Lake with PySpark: ACID upsert + time travel
from delta.tables import DeltaTable

updates = spark.read.parquet("s3://lake/bronze/orders/dt=2024-03-10/")
target = DeltaTable.forPath(spark, "s3://lake/silver/orders")

(target.alias("t")
   .merge(updates.alias("s"), "t.order_id = s.order_id")
   .whenMatchedUpdateAll(condition="s.updated_at > t.updated_at")
   .whenNotMatchedInsertAll()
   .execute())

yesterday = (spark.read.format("delta")
                  .option("timestampAsOf", "2024-03-09")
                  .load("s3://lake/silver/orders"))     # time travel for audits / rollback
""", "Delta MERGE and time travel"),
    cards("Storage and warehouses", [
        ("Why is Parquet the default for analytics?",
         "Columnar, compressed, typed, with embedded schema and per-row-group min/max statistics "
         "that enable column pruning and predicate pushdown. It's splittable for parallel reads."),
        ("Avro vs Parquet?",
         "Avro: row-based, good for write-heavy streaming and schema evolution (Kafka). Parquet: "
         "columnar, good for read-heavy analytics."),
        ("Partitioning vs clustering?",
         "Partitioning physically separates data (e.g. by date) so whole partitions are skipped. "
         "Clustering sorts data within partitions by columns so blocks can be pruned more "
         "finely."),
        ("What makes a good partition column?",
         "Low-to-medium cardinality, frequently used in filters, evenly distributed. Usually a "
         "date. Avoid high-cardinality columns like user_id."),
        ("What is the small-files problem and its fix?",
         "Too many tiny files add per-file open and metadata overhead and slow queries. Fix: "
         "compaction (OPTIMIZE), fewer partitions, coalesce before write, target 128 MB-1 GB "
         "files."),
        ("What is predicate pushdown?",
         "Applying filters at the storage/scan layer (using file and row-group statistics or "
         "partitions) so irrelevant data is never read."),
        ("Name three open table formats and what they add.",
         "Delta Lake, Apache Iceberg, Apache Hudi. They add ACID transactions, schema "
         "enforcement/evolution, time travel and efficient upserts on top of data-lake files."),
        ("How is BigQuery on-demand pricing calculated?",
         "By bytes scanned per query (or reserved slot capacity). Partition filters and "
         "selecting fewer columns directly reduce cost."),
        ("Snowflake zero-copy cloning?",
         "Creates an instant copy of a table, schema or database that shares the underlying "
         "micro-partitions. Storage is only consumed when data diverges. Great for dev/test."),
        ("Separation of storage and compute: why does it matter?",
         "Each scales and is billed independently. Many compute clusters can read the same data, "
         "and you pay for compute only while queries run."),
        ("Redshift distribution style and sort key?",
         "The DISTKEY decides which node holds each row (co-locate join keys to avoid "
         "redistribution). The SORTKEY orders data on disk so zone maps can skip blocks."),
    ]),
]
