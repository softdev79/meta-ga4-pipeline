"""Chapters: SQL, Python for data engineering."""

from content_helpers import c, ch, h2, h3, p, ul, ol, code, co, tbl, cards

BLOCKS = [
    # ------------------------------------------------------------------ SQL
    ch("SQL for Data Engineers",
       "SQL is the most-used and most-tested data engineering skill. Every interview loop has a "
       "SQL round. Get fluent enough that window functions feel as natural as a Control-M "
       "dependency."),
    h2("The practice schema"),
    p("Every example in this chapter uses this small retail schema. Create it in DuckDB "
      "(<font face='Mono'>pip install duckdb</font>, then run <font face='Mono'>duckdb shop.db"
      "</font>) or in PostgreSQL."),
    code("sql", r"""
CREATE TABLE customers (
    customer_id   INTEGER PRIMARY KEY,
    name          VARCHAR,
    city          VARCHAR,
    signup_date   DATE
);

CREATE TABLE orders (
    order_id      INTEGER PRIMARY KEY,
    customer_id   INTEGER REFERENCES customers(customer_id),
    order_ts      TIMESTAMP,
    status        VARCHAR,           -- 'placed' | 'shipped' | 'cancelled'
    amount        DECIMAL(10,2)
);

INSERT INTO customers VALUES
  (1,'Asha','Pune','2024-01-05'), (2,'Ben','Leeds','2024-02-11'),
  (3,'Chen','Austin','2024-02-20'), (4,'Divya','Pune','2024-03-02');

INSERT INTO orders VALUES
  (101,1,'2024-03-01 10:00','shipped',120.00),
  (102,1,'2024-03-05 12:30','shipped', 80.00),
  (103,2,'2024-03-05 09:10','cancelled',50.00),
  (104,3,'2024-03-06 18:45','placed', 200.00),
  (105,1,'2024-03-09 08:00','shipped', 40.00),
  (106,3,'2024-03-10 14:00','shipped', 200.00);
""", "practice schema"),
    h2("Logical order of execution"),
    p("SQL is written in one order and evaluated in another. Knowing the evaluation order "
      "explains most 'why doesn't this work?' errors, such as why you can't use a SELECT alias "
      "in WHERE."),
    tbl([
        ["Step", "Clause", "What happens"],
        ["1", "FROM / JOIN", "Build the working set of rows"],
        ["2", "WHERE", "Filter individual rows (no aggregates allowed)"],
        ["3", "GROUP BY", "Collapse rows into groups"],
        ["4", "HAVING", "Filter groups (aggregates allowed)"],
        ["5", "Window functions", "Computed over the remaining rows"],
        ["6", "SELECT", "Pick and compute output columns, assign aliases"],
        ["7", "DISTINCT", "Remove duplicate output rows"],
        ["8", "ORDER BY", "Sort (aliases ARE allowed here)"],
        ["9", "LIMIT / OFFSET", "Trim the result"],
    ], [0.5, 1.4, 3.5]),
    co("note", "Some engines (BigQuery, Snowflake, DuckDB) also support <b>QUALIFY</b>, which "
               "filters on window-function results the way HAVING filters on aggregates. It is "
               "evaluated after window functions."),
    h2("Joins"),
    tbl([
        ["Join", "Returns", "Typical use"],
        ["INNER", "Only rows that match on both sides", "Orders with their customer"],
        ["LEFT", "All left rows; NULLs where the right side has no match",
         "All customers, with orders if any"],
        ["RIGHT", "Mirror of LEFT (rarely used; rewrite it as a LEFT join)", "-"],
        ["FULL OUTER", "All rows from both sides", "Reconciling two systems"],
        ["CROSS", "Every combination (Cartesian product)", "Date spine x products"],
        ["SEMI (EXISTS / IN)", "Left rows that have a match, without duplicating them",
         "Customers who ordered"],
        ["ANTI (NOT EXISTS)", "Left rows with no match", "Customers who never ordered"],
    ], [1.1, 2.4, 2]),
    code("sql", r"""
-- Customers who have never ordered (anti-join). Prefer NOT EXISTS over NOT IN:
-- NOT IN returns no rows at all if the subquery contains a single NULL.
SELECT c.*
FROM customers c
WHERE NOT EXISTS (SELECT 1 FROM orders o WHERE o.customer_id = c.customer_id);

-- LEFT JOIN trap: a filter on the right table in WHERE silently turns it into an INNER JOIN
SELECT c.name, o.order_id
FROM customers c
LEFT JOIN orders o
       ON o.customer_id = c.customer_id
      AND o.status = 'shipped'        -- keep right-table filters in the ON clause
ORDER BY c.name;
""", "anti-join and the LEFT JOIN trap"),
    co("warn", ["<b>Join fan-out</b>: joining a one-row-per-customer table to a "
                "many-rows-per-customer table multiplies rows. Summing a customer-level column "
                "afterwards double counts. Always know the <b>grain</b> (what one row means) of "
                "both sides before joining.",
                "<b>NULLs never equal anything</b>, not even another NULL. Use "
                "<font face='Mono'>IS NULL</font>, <font face='Mono'>COALESCE</font> or "
                "<font face='Mono'>IS NOT DISTINCT FROM</font>."]),
    h2("Aggregation, GROUP BY, HAVING"),
    code("sql", r"""
-- Revenue per city, only for cities with more than one shipped order
SELECT c.city,
       COUNT(*)                                        AS shipped_orders,
       SUM(o.amount)                                   AS revenue,
       COUNT(DISTINCT o.customer_id)                   AS buyers,
       SUM(CASE WHEN o.amount >= 100 THEN 1 ELSE 0 END) AS big_orders  -- conditional agg
FROM orders o
JOIN customers c USING (customer_id)
WHERE o.status = 'shipped'          -- row filter: before grouping
GROUP BY c.city
HAVING COUNT(*) > 1                 -- group filter: after grouping
ORDER BY revenue DESC;
""", "conditional aggregation"),
    p("Note that <font face='Mono'>COUNT(*)</font> counts rows, <font face='Mono'>COUNT(col)"
      "</font> counts non-NULL values and <font face='Mono'>COUNT(DISTINCT col)</font> counts "
      "unique non-NULL values. Interviewers love asking about the difference."),
    h2("CTEs and subqueries"),
    p("A <b>Common Table Expression</b> (<font face='Mono'>WITH name AS (...)</font>) names an "
      "intermediate result. CTEs make SQL readable top to bottom, a bit like a chain of jobs. "
      "Recursive CTEs walk hierarchies such as org charts, bills of materials, or a job "
      "dependency graph."),
    code("sql", r"""
-- Recursive CTE: walk a job-dependency tree (yes, like a Control-M flow!)
WITH RECURSIVE downstream AS (
    SELECT job_name, depends_on, 1 AS depth
    FROM job_deps
    WHERE depends_on = 'LOAD_ORDERS'          -- start node
    UNION ALL
    SELECT d.job_name, d.depends_on, ds.depth + 1
    FROM job_deps d
    JOIN downstream ds ON d.depends_on = ds.job_name
)
SELECT * FROM downstream ORDER BY depth;
""", "recursive CTE: impact analysis"),
    co("bridge", "\"Which jobs are impacted if LOAD_ORDERS fails?\" is a question you've "
                 "answered in Control-M's flow diagrams. In SQL it's a recursive CTE, and in "
                 "data engineering it's called <b>lineage / impact analysis</b>."),
    h2("Window functions: the most important topic"),
    p("A window function computes a value across a set of rows related to the current row "
      "<i>without collapsing them</i> (unlike GROUP BY). Syntax: "
      "<font face='Mono'>FUNC() OVER (PARTITION BY ... ORDER BY ... ROWS BETWEEN ...)</font>."),
    tbl([
        ["Family", "Functions", "Example use"],
        ["Ranking", "ROW_NUMBER, RANK, DENSE_RANK, NTILE",
         "Latest record per key; top N per group"],
        ["Offset", "LAG, LEAD, FIRST_VALUE, LAST_VALUE, NTH_VALUE",
         "Change vs previous day; next event"],
        ["Aggregate", "SUM, AVG, COUNT, MIN, MAX ... OVER", "Running totals; moving averages"],
        ["Distribution", "PERCENT_RANK, CUME_DIST, PERCENTILE_CONT", "Percentiles"],
    ], [1, 2.4, 2.2]),
    code("sql", r"""
SELECT order_id, customer_id, order_ts, amount,
       ROW_NUMBER() OVER (PARTITION BY customer_id ORDER BY order_ts)      AS order_seq,
       LAG(amount)  OVER (PARTITION BY customer_id ORDER BY order_ts)      AS prev_amount,
       SUM(amount)  OVER (PARTITION BY customer_id ORDER BY order_ts
                          ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) AS running_total,
       AVG(amount)  OVER (ORDER BY order_ts
                          ROWS BETWEEN 2 PRECEDING AND CURRENT ROW)         AS moving_avg_3
FROM orders
WHERE status <> 'cancelled';
""", "the four window patterns you must know"),
    tbl([
        ["amount", "ROW_NUMBER()", "RANK()", "DENSE_RANK()"],
        ["200", "1", "1", "1"],
        ["200", "2", "1", "1"],
        ["120", "3", "3", "2"],
        ["80", "4", "4", "3"],
    ], [1, 1, 1, 1]),
    h3("Pattern: deduplicate, keeping the latest row per key"),
    p("This is the single most common query in data engineering. Raw data often contains "
      "duplicates (retries, CDC updates, re-sent files)."),
    code("sql", r"""
-- Portable version
WITH ranked AS (
    SELECT *,
           ROW_NUMBER() OVER (PARTITION BY order_id
                              ORDER BY updated_at DESC, _loaded_at DESC) AS rn
    FROM raw_orders
)
SELECT * FROM ranked WHERE rn = 1;

-- BigQuery / Snowflake / DuckDB shorthand
SELECT *
FROM raw_orders
QUALIFY ROW_NUMBER() OVER (PARTITION BY order_id ORDER BY updated_at DESC) = 1;
""", "dedupe latest record"),
    co("warn", "ROW_NUMBER with a non-unique ORDER BY is <b>non-deterministic</b>: two runs can "
               "keep different rows. Always add a tie-breaker column (e.g. load timestamp or "
               "file name)."),
    h3("Pattern: top N per group"),
    code("sql", r"""
-- Top 2 orders by amount for each customer (ties included)
SELECT *
FROM (
  SELECT o.*, DENSE_RANK() OVER (PARTITION BY customer_id ORDER BY amount DESC) AS rnk
  FROM orders o
) t
WHERE rnk <= 2;
""", "top-N per group"),
    h3("Pattern: gaps and islands (consecutive streaks)"),
    p("To find consecutive days a user was active, subtract a row number from the date. "
      "Consecutive dates produce the same difference, which forms an 'island'."),
    code("sql", r"""
WITH d AS (
  SELECT DISTINCT user_id, CAST(event_ts AS DATE) AS day
  FROM events
),
g AS (
  SELECT user_id, day,
         day - CAST(ROW_NUMBER() OVER (PARTITION BY user_id ORDER BY day) AS INTEGER) AS grp
  FROM d
)
SELECT user_id, MIN(day) AS streak_start, MAX(day) AS streak_end, COUNT(*) AS days
FROM g
GROUP BY user_id, grp
ORDER BY days DESC;
""", "gaps and islands"),
    co("bridge", "Same pattern, ops flavour: \"find each continuous period a job was failing\" "
                 "from a job-run history table. Try it on exported Control-M run data as a "
                 "practice exercise; it makes a great portfolio talking point."),
    h3("Pattern: month-over-month growth"),
    code("sql", r"""
WITH monthly AS (
  SELECT DATE_TRUNC('month', order_ts) AS month, SUM(amount) AS revenue
  FROM orders WHERE status = 'shipped'
  GROUP BY 1
)
SELECT month, revenue,
       LAG(revenue) OVER (ORDER BY month) AS prev_revenue,
       ROUND(100.0 * (revenue - LAG(revenue) OVER (ORDER BY month))
             / NULLIF(LAG(revenue) OVER (ORDER BY month), 0), 1) AS pct_growth
FROM monthly
ORDER BY month;
""", "MoM growth with NULLIF to avoid divide-by-zero"),
    h2("Writing data: INSERT, UPDATE, MERGE (upsert)"),
    p("Pipelines constantly need to 'insert new rows, update changed rows'. "
      "<font face='Mono'>MERGE</font> does it atomically, and it's the backbone of "
      "<b>idempotent</b> loads: you can re-run it and get the same result."),
    code("sql", r"""
MERGE INTO dw.orders AS t
USING staging.orders_batch AS s
   ON t.order_id = s.order_id
WHEN MATCHED AND s.updated_at > t.updated_at THEN
  UPDATE SET status = s.status, amount = s.amount, updated_at = s.updated_at
WHEN NOT MATCHED THEN
  INSERT (order_id, customer_id, order_ts, status, amount, updated_at)
  VALUES (s.order_id, s.customer_id, s.order_ts, s.status, s.amount, s.updated_at);

-- PostgreSQL alternative (also valid; MERGE exists in PG 15+)
INSERT INTO dw.orders AS t (order_id, status, amount, updated_at)
SELECT order_id, status, amount, updated_at FROM staging.orders_batch
ON CONFLICT (order_id) DO UPDATE
  SET status = EXCLUDED.status, amount = EXCLUDED.amount, updated_at = EXCLUDED.updated_at
  WHERE EXCLUDED.updated_at > t.updated_at;
""", "upsert"),
    co("warn", "MERGE fails (or behaves unpredictably) if the source has <b>duplicate keys</b>. "
               "Deduplicate the staging batch first with the ROW_NUMBER pattern."),
    h2("DDL vs DML, and DELETE vs TRUNCATE vs DROP"),
    tbl([
        ["Command", "Type", "Removes", "Rollback / notes"],
        ["DELETE", "DML", "Rows matching WHERE", "Logged row by row, can roll back, fires triggers"],
        ["TRUNCATE", "DDL", "All rows; keeps structure",
         "Fast, minimal logging, resets identity in many DBs"],
        ["DROP", "DDL", "The table itself (data + structure)", "Gone; dependent objects break"],
    ], [1, 0.7, 1.8, 2.5]),
    h2("Performance and query tuning"),
    ul("<b>Read the plan</b>: <font face='Mono'>EXPLAIN</font> / <font face='Mono'>EXPLAIN "
       "ANALYZE</font> (Postgres), the Query Profile (Snowflake), Execution details (BigQuery).",
       "<b>Never SELECT * on columnar warehouses</b>. You pay per column scanned in BigQuery.",
       "<b>Filter on partition columns</b> so the engine can skip files (partition pruning). "
       "Avoid wrapping partition columns in functions: write <font face='Mono'>WHERE dt >= "
       "'2024-03-01'</font>, not <font face='Mono'>WHERE YEAR(dt) = 2024</font>.",
       "<b>Indexes</b> (OLTP) speed up selective lookups but slow down writes. Columnar warehouses "
       "use partitioning, clustering and sort keys instead.",
       "<b>Filter early, aggregate before joining</b> to shrink data before expensive joins.",
       "Prefer <font face='Mono'>UNION ALL</font> over <font face='Mono'>UNION</font> unless you "
       "need deduplication; UNION adds a sort/distinct step.",
       "<b>Watch out for exploding joins</b>: check row counts before and after each join."),
    code("sql", r"""
EXPLAIN ANALYZE
SELECT c.city, SUM(o.amount)
FROM orders o JOIN customers c USING (customer_id)
WHERE o.order_ts >= DATE '2024-03-01'
GROUP BY c.city;
-- Look for: Seq Scan on a huge table (missing index / partition filter),
-- row estimates far from actual rows (stale stats -> ANALYZE),
-- Nested Loop over big inputs (consider hash join / index).
""", "reading a plan"),
    h2("SQL interview practice"),
    co("practice", [
        "Try each one before looking at the solution. Use the practice schema.",
        "- <b>Q1.</b> Second-highest order amount overall (handle ties and the case with no "
        "second value).",
        "- <b>Q2.</b> For each customer, the number of days between their first and second order.",
        "- <b>Q3.</b> Customers whose shipped revenue is above the average customer revenue.",
        "- <b>Q4.</b> Each customer's share (%) of total shipped revenue.",
        "- <b>Q5.</b> Find duplicate rows in a table that has no primary key.",
    ], "five classic questions"),
    code("sql", r"""
-- Q1: second-highest distinct amount (NULL if none)
SELECT MAX(amount) AS second_highest
FROM orders
WHERE amount < (SELECT MAX(amount) FROM orders);
-- or: SELECT amount FROM (SELECT DISTINCT amount, DENSE_RANK() OVER (ORDER BY amount DESC) r
--     FROM orders) WHERE r = 2;

-- Q2: days between first and second order
SELECT customer_id,
       DATE_DIFF('day', MIN(order_ts), MAX(order_ts)) AS days_to_second  -- DuckDB syntax
FROM (SELECT customer_id, order_ts,
             ROW_NUMBER() OVER (PARTITION BY customer_id ORDER BY order_ts) AS rn
      FROM orders) t
WHERE rn <= 2
GROUP BY customer_id
HAVING COUNT(*) = 2;

-- Q3: above-average customers
WITH rev AS (
  SELECT customer_id, SUM(amount) AS revenue
  FROM orders WHERE status = 'shipped' GROUP BY customer_id
)
SELECT * FROM rev WHERE revenue > (SELECT AVG(revenue) FROM rev);

-- Q4: share of total (window over the whole result set)
SELECT customer_id, SUM(amount) AS revenue,
       ROUND(100.0 * SUM(amount) / SUM(SUM(amount)) OVER (), 2) AS pct_of_total
FROM orders WHERE status = 'shipped'
GROUP BY customer_id;

-- Q5: duplicates
SELECT customer_id, order_ts, amount, COUNT(*) AS copies
FROM orders
GROUP BY customer_id, order_ts, amount
HAVING COUNT(*) > 1;
""", "solutions"),
    co("tip", ["In live SQL rounds, <b>talk while you type</b>: state the grain of each table, "
               "say which join you are choosing and why, and mention edge cases (NULLs, ties, "
               "empty groups, duplicates) before the interviewer asks.",
               "Good free practice sites: DataLemur, StrataScratch, LeetCode (SQL 50), "
               "SQLBolt and Mode's SQL tutorial."]),
    cards("SQL", [
        ("Logical order of SQL execution?",
         "FROM/JOIN, WHERE, GROUP BY, HAVING, window functions, SELECT, DISTINCT, ORDER BY, LIMIT."),
        ("WHERE vs HAVING?",
         "WHERE filters rows before grouping (no aggregates). HAVING filters groups after "
         "aggregation (aggregates allowed)."),
        ("ROW_NUMBER vs RANK vs DENSE_RANK on 200, 200, 120?",
         "ROW_NUMBER: 1,2,3. RANK: 1,1,3 (gaps after ties). DENSE_RANK: 1,1,2 (no gaps)."),
        ("How do you keep only the latest record per key?",
         "ROW_NUMBER() OVER (PARTITION BY key ORDER BY updated_at DESC, tiebreaker DESC), "
         "then keep rn = 1 (or use QUALIFY)."),
        ("Why prefer NOT EXISTS over NOT IN?",
         "If the NOT IN subquery returns any NULL, the predicate is never true and you get "
         "zero rows. NOT EXISTS handles NULLs correctly."),
        ("COUNT(*) vs COUNT(col) vs COUNT(DISTINCT col)?",
         "All rows; non-NULL values of col; unique non-NULL values of col."),
        ("What does a LEFT JOIN with a right-table filter in WHERE do?",
         "It removes the NULL-extended rows, effectively becoming an INNER JOIN. Put "
         "right-table filters in the ON clause instead."),
        ("What is a window function?",
         "A function computed over a set of related rows (the window) defined by OVER(PARTITION "
         "BY ... ORDER BY ... frame). Unlike GROUP BY, it doesn't collapse rows."),
        ("ROWS vs RANGE frame?",
         "ROWS counts physical rows (e.g. 2 PRECEDING = 2 rows back). RANGE uses value ranges, "
         "so rows with equal ORDER BY values (peers) are included together."),
        ("What is MERGE used for?",
         "Atomic upsert: update matched rows, insert unmatched (optionally delete) in one "
         "statement. It's the basis of idempotent incremental loads."),
        ("What is a CTE and why use one?",
         "A named temporary result (WITH x AS ...). Readability, reuse within a query, and "
         "recursion for hierarchies."),
        ("Gaps-and-islands trick?",
         "date minus ROW_NUMBER() over (PARTITION BY entity ORDER BY date) is constant for "
         "consecutive dates; group by it to get each streak."),
        ("DELETE vs TRUNCATE vs DROP?",
         "DELETE: DML, removes filtered rows, logged, can roll back. TRUNCATE: DDL, removes all "
         "rows fast, keeps structure. DROP: removes the table entirely."),
        ("UNION vs UNION ALL?",
         "UNION removes duplicates (extra sort/hash step). UNION ALL keeps every row and is faster."),
        ("How do you avoid divide-by-zero in SQL?",
         "Wrap the denominator in NULLIF(x, 0), so the result is NULL instead of an error. "
         "Some engines also have SAFE_DIVIDE."),
        ("What is partition pruning?",
         "The engine skips partitions/files whose partition values can't match the filter. It "
         "requires filtering directly on the partition column (no functions wrapped around it)."),
        ("What is 'grain' and why check it before a join?",
         "Grain is what one row represents (e.g. one order line per row). Joining tables of "
         "different grain causes fan-out and double counting."),
        ("Correlated vs non-correlated subquery?",
         "Correlated subqueries reference the outer row and conceptually run per row (often "
         "rewritten as joins). Non-correlated ones run once, independently."),
    ]),

    # ------------------------------------------------------------------ Python
    ch("Python for Data Engineering",
       "You've written software, so this chapter focuses on the Python idioms that come up in "
       "data work: streaming large files, calling APIs safely, pandas, configuration, logging "
       "and tests."),
    h2("Core language features you must be fluent in"),
    tbl([
        ["Feature", "Why DEs care"],
        ["dict / list / set comprehensions", "Concise record transformations"],
        ["Generators (yield)", "Process files bigger than memory, one record at a time"],
        ["Context managers (with)", "Files, DB connections and locks always get closed"],
        ["Decorators", "Retries, timing, Airflow @task / @dag"],
        ["Type hints + dataclasses", "Readable, self-documenting records and configs"],
        ["Exceptions (try/except/finally)", "Fail loudly, retry the right errors, clean up"],
        ["pathlib, datetime / zoneinfo", "Paths and timezone-correct timestamps"],
        ["logging (not print)", "Levels, timestamps, shipping logs to central tools"],
    ], [2, 3.4]),
    h2("Streaming a large file with generators"),
    code("python", r"""
import csv
import gzip
from collections.abc import Iterator
from pathlib import Path


def read_rows(path: Path) -> Iterator[dict]:
    # Yield one dict per CSV row; works for .csv and .csv.gz without loading it all.
    opener = gzip.open if path.suffix == ".gz" else open
    with opener(path, "rt", newline="", encoding="utf-8") as f:
        yield from csv.DictReader(f)


def batched(rows: Iterator[dict], size: int = 10_000) -> Iterator[list[dict]]:
    batch = []
    for row in rows:
        batch.append(row)
        if len(batch) == size:
            yield batch
            batch = []
    if batch:
        yield batch


for chunk in batched(read_rows(Path("orders_2024.csv.gz"))):
    load_to_db(chunk)          # memory stays flat even for a 50 GB file
""", "constant-memory file processing"),
    co("note", "Python 3.12+ has <font face='Mono'>itertools.batched()</font> built in. Knowing how "
               "to write it yourself is still a common interview question."),
    h2("Calling REST APIs: pagination, retries, rate limits"),
    p("Most ingestion work is 'pull JSON from an API and land it somewhere'. Robust ingestion "
      "handles <b>pagination</b>, <b>transient failures</b> (HTTP 429/5xx) with exponential "
      "backoff, <b>timeouts</b>, and <b>secrets</b> that never appear in code."),
    code("python", r"""
import logging
import os
import random
import time

import requests

log = logging.getLogger(__name__)
API = "https://api.example.com/v1/orders"
TOKEN = os.environ["ORDERS_API_TOKEN"]          # secret from env / secret manager
RETRYABLE = {429, 500, 502, 503, 504}


def get_with_retry(session, url, params, max_attempts=5):
    for attempt in range(1, max_attempts + 1):
        retry_after = None
        try:
            resp = session.get(url, params=params, timeout=30)
        except (requests.ConnectionError, requests.Timeout) as exc:
            err = repr(exc)
        else:
            if resp.status_code not in RETRYABLE:
                resp.raise_for_status()           # 4xx (not 429) -> fail fast
                return resp.json()
            err = f"HTTP {resp.status_code}"
            retry_after = resp.headers.get("Retry-After")    # server-requested wait
        if attempt == max_attempts:
            break
        wait = int(retry_after) if retry_after else 2 ** attempt + random.random()
        log.warning("attempt %s failed (%s); sleeping %.1fs", attempt, err, wait)
        time.sleep(wait)
    raise RuntimeError(f"gave up after {max_attempts} attempts: {url} ({err})")


def fetch_all(since: str):
    with requests.Session() as s:
        s.headers["Authorization"] = f"Bearer {TOKEN}"
        params = {"updated_since": since, "limit": 500}
        while True:
            page = get_with_retry(s, API, params)
            yield from page["data"]
            cursor = page.get("next_cursor")
            if not cursor:
                break
            params["cursor"] = cursor
""", "paginated, retrying API client"),
    co("tip", "In interviews, say the words <b>idempotent</b>, <b>exponential backoff with "
              "jitter</b>, <b>cursor-based pagination</b> and <b>secrets manager</b>. They show "
              "production thinking, which you already have from Control-M on-call."),
    h2("pandas essentials (and when not to use it)"),
    code("python", r"""
import pandas as pd

orders = pd.read_csv("orders.csv", parse_dates=["order_ts"],
                     dtype={"customer_id": "int64", "status": "category"})

clean = (
    orders
    .drop_duplicates(subset="order_id", keep="last")
    .query("status != 'cancelled'")
    .assign(order_date=lambda d: d["order_ts"].dt.date,
            amount=lambda d: d["amount"].fillna(0).round(2))
)

daily = (clean.groupby(["order_date", "customer_id"], as_index=False)
              .agg(orders=("order_id", "count"), revenue=("amount", "sum")))

customers = pd.read_parquet("customers.parquet")
report = daily.merge(customers, on="customer_id", how="left", validate="many_to_one")

report.to_parquet("daily_revenue.parquet", index=False)   # columnar, typed, compressed
""", "typical pandas transform"),
    co("warn", ["pandas is <b>single-machine and in-memory</b>. Rule of thumb: fine up to a few "
                "GB. Beyond that, use <b>DuckDB</b> or <b>Polars</b> on one machine, or "
                "<b>Spark</b> / the warehouse for distributed scale.",
                "<font face='Mono'>validate='many_to_one'</font> in merge raises an error on "
                "unexpected fan-out, a cheap safety net."]),
    h3("DuckDB: SQL on files, no server"),
    code("python", r"""
import duckdb

con = duckdb.connect()   # in-memory; S3 paths need: INSTALL httpfs; LOAD httpfs;
top = con.sql('''
    SELECT customer_id, SUM(amount) AS revenue
    FROM read_parquet('s3://my-bucket/orders/dt=2024-03-*/*.parquet')
    GROUP BY 1 ORDER BY 2 DESC LIMIT 10
''').df()                # returns a pandas DataFrame
""", "DuckDB querying Parquet directly"),
    h2("Configuration, logging and structure"),
    code("python", r"""
import logging
import os
from dataclasses import dataclass

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)


@dataclass(frozen=True)
class Settings:
    db_url: str = os.environ.get("DB_URL", "postgresql://localhost/dev")
    batch_size: int = int(os.environ.get("BATCH_SIZE", "10000"))
    env: str = os.environ.get("ENV", "dev")


def main(run_date: str) -> int:
    settings = Settings()
    log = logging.getLogger("orders")
    log.info("run_date=%s starting load env=%s batch=%s",
             run_date, settings.env, settings.batch_size)
    ...
    return 0          # exit code 0 = success: the scheduler sees this


if __name__ == "__main__":
    import sys
    sys.exit(main(sys.argv[1]))
""", "a pipeline script the scheduler can run"),
    co("bridge", "Exit codes, stdout/stderr and log files are how Control-M decides a job "
                 "ended OK or NOTOK. The same holds when Airflow runs your script through a "
                 "BashOperator or KubernetesPodOperator: <b>non-zero exit = failed task</b>. "
                 "Structured logs with a run id make the 'sysout' searchable."),
    h2("Testing with pytest"),
    code("python", r"""
# transform.py
def normalise_status(raw: str | None) -> str:
    mapping = {"ship": "shipped", "shipped": "shipped", "cxl": "cancelled",
               "cancelled": "cancelled", "placed": "placed"}
    if raw is None:
        return "unknown"
    return mapping.get(raw.strip().lower(), "unknown")


# test_transform.py
import pytest
from transform import normalise_status


@pytest.mark.parametrize("raw, expected", [
    ("SHIP", "shipped"), (" cxl ", "cancelled"), (None, "unknown"), ("weird", "unknown"),
])
def test_normalise_status(raw, expected):
    assert normalise_status(raw) == expected
""", "unit test for a transformation"),
    h2("Python interview questions"),
    tbl([
        ["Question", "Short answer"],
        ["List vs tuple vs set vs dict?",
         "Mutable ordered / immutable ordered / unique unordered / key-value with O(1) lookup."],
        ["What is a generator?",
         "A function using yield that produces values lazily, keeping memory constant."],
        ["Shallow vs deep copy?",
         "A shallow copy copies the container but shares nested objects; a deep copy copies "
         "everything recursively."],
        ["What does the GIL mean for data work?",
         "Only one thread runs Python bytecode at a time. Use threads for I/O-bound work (APIs), "
         "multiprocessing or native libraries for CPU-bound work."],
        ["*args / **kwargs?", "Variable positional / keyword arguments."],
        ["How do you handle secrets?",
         "Environment variables or a secrets manager (Vault, AWS Secrets Manager, GCP Secret "
         "Manager), never in Git."],
        ["Mutable default argument bug?",
         "def f(x=[]) shares one list across calls. Use None and create the list inside."],
    ], [1.8, 3.6]),
    cards("Python", [
        ("Why use generators in data pipelines?",
         "They process one item at a time (lazy evaluation), so memory stays constant regardless "
         "of input size: ideal for big files and API pagination."),
        ("Which HTTP status codes should be retried?",
         "429 (rate limited) and 5xx (500, 502, 503, 504), plus connection errors and timeouts. "
         "Other 4xx are client errors: fail fast."),
        ("What is exponential backoff with jitter?",
         "Wait 1s, 2s, 4s, 8s... between retries, plus a random offset, so many clients don't "
         "retry in lockstep and overwhelm the server."),
        ("When is pandas the wrong tool?",
         "When the data doesn't fit comfortably in one machine's memory or needs distributed "
         "processing. Use DuckDB/Polars (single node) or Spark/the warehouse."),
        ("Threads vs processes in Python?",
         "Threads suit I/O-bound work (network, disk) because the GIL is released while waiting. "
         "Processes suit CPU-bound work and give true parallelism."),
        ("Why log instead of print?",
         "Levels, timestamps, logger names, configurable handlers and structured context, all "
         "of which central log tools can search and alert on."),
        ("What does a scheduler use to judge script success?",
         "The process exit code: 0 = success, non-zero = failure (Control-M NOTOK, Airflow "
         "task failed)."),
        ("What is a context manager?",
         "An object used with 'with' that guarantees setup and teardown (__enter__ / __exit__), "
         "e.g. closing files or DB connections even on error."),
        ("Cursor vs offset pagination?",
         "Offset (page=3) can skip or duplicate rows when data changes between calls. A cursor "
         "(an opaque next token / last seen id) is stable and efficient."),
        ("pytest parametrize?",
         "@pytest.mark.parametrize runs one test function over many (input, expected) cases."),
    ]),
]
