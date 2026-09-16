# SQL — the round you cannot afford to fumble

"Medium-level SQL" in a services-firm L2 means: window functions, a self-join or
gaps-and-islands, a "find the second highest" variant, and one question designed to catch
you on NULL semantics or join fan-out.

**Rule: narrate before you type.** *"I'll rank within each group and filter to rank 1 —
in BigQuery I can do that with QUALIFY instead of wrapping it in a subquery."* Then write.

---

## 1. Window functions — write these from memory

```sql
-- Dedupe: keep the latest row per key (THE most useful pattern in DE)
SELECT * FROM events
QUALIFY ROW_NUMBER() OVER (PARTITION BY id ORDER BY updated_at DESC, ingest_ts DESC) = 1;

-- Top N per group
SELECT * FROM sales
QUALIFY DENSE_RANK() OVER (PARTITION BY region ORDER BY revenue DESC) <= 3;

-- Running total
SUM(amount) OVER (PARTITION BY customer_id ORDER BY order_date
                  ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW)

-- 7-day moving average
AVG(spend) OVER (PARTITION BY ad_id ORDER BY date
                 ROWS BETWEEN 6 PRECEDING AND CURRENT ROW)

-- Day-over-day delta and % change
spend - LAG(spend) OVER (PARTITION BY ad_id ORDER BY date)                     AS dod_delta
SAFE_DIVIDE(spend, LAG(spend) OVER (PARTITION BY ad_id ORDER BY date)) - 1     AS dod_pct

-- First/last value in a group without a self-join
FIRST_VALUE(channel) OVER (PARTITION BY user_id ORDER BY ts
                           ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING)

-- Percentile / bucketing
NTILE(4)          OVER (ORDER BY revenue DESC)
PERCENT_RANK()    OVER (ORDER BY revenue)
APPROX_QUANTILES(revenue, 100)[OFFSET(95)]      AS p95
```

**`ROW_NUMBER` vs `RANK` vs `DENSE_RANK` on `100, 100, 90`** → `1,2,3` / `1,1,3` / `1,1,2`.
Dedupe / competition ranking / **Nth distinct value**.
`ROW_NUMBER` needs a **tiebreaker** in the ORDER BY to be deterministic — without one,
a re-run can pick a different row and your "idempotent" pipeline isn't.

**The frame trap:** with `ORDER BY` and no frame clause, the default is
`RANGE BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW`. **RANGE ties collapse together** —
duplicate ORDER BY values are all included in the same frame. If you want a true row
window, say `ROWS`. This is a favourite senior-interviewer trap.

---

## 2. The classic puzzles

**Second highest salary** — three ways, and know why:
```sql
-- 1. Window (best; handles ties explicitly, one pass)
SELECT DISTINCT salary FROM emp
QUALIFY DENSE_RANK() OVER (ORDER BY salary DESC) = 2;

-- 2. Correlated subquery (portable, slow)
SELECT MAX(salary) FROM emp WHERE salary < (SELECT MAX(salary) FROM emp);

-- 3. OFFSET (breaks on ties)
SELECT DISTINCT salary FROM emp ORDER BY salary DESC LIMIT 1 OFFSET 1;
```
*"I'd ask whether 'second highest' means second distinct value or the second row — that
changes DENSE_RANK to ROW_NUMBER."* **Asking that question scores higher than the answer.**

**Nth highest per department** — same, with `PARTITION BY department`.

**Find duplicates**
```sql
SELECT id, COUNT(*) FROM t GROUP BY id HAVING COUNT(*) > 1;
```

**Gaps and islands / sessionisation** — this is literally what `stg_ga4_sessions.sql` does:
```sql
WITH flagged AS (
  SELECT *,
    IF(TIMESTAMP_DIFF(ts, LAG(ts) OVER w, MINUTE) > 30 OR LAG(ts) OVER w IS NULL, 1, 0) AS new_session
  FROM events
  WINDOW w AS (PARTITION BY user_pseudo_id ORDER BY ts)
),
numbered AS (
  SELECT *, SUM(new_session) OVER (PARTITION BY user_pseudo_id ORDER BY ts) AS session_no
  FROM flagged
)
SELECT user_pseudo_id, session_no, MIN(ts) AS started_at, MAX(ts) AS ended_at, COUNT(*) AS events
FROM numbered GROUP BY 1, 2;
```
**Pattern: LAG → boolean flag → running SUM of the flag → GROUP BY.** Memorise the shape;
it solves sessionisation, consecutive-login-streaks, and contiguous-date-ranges questions.

**Consecutive days / streaks**
```sql
-- date minus row_number is constant within a streak
SELECT user_id, MIN(d), MAX(d), COUNT(*) AS streak_len
FROM (SELECT *, DATE_SUB(d, INTERVAL ROW_NUMBER() OVER (PARTITION BY user_id ORDER BY d) DAY) AS grp
      FROM logins)
GROUP BY user_id, grp HAVING COUNT(*) >= 3;
```

**Cumulative / retention cohort**
```sql
SELECT cohort_month,
       DATE_DIFF(activity_month, cohort_month, MONTH) AS month_n,
       COUNT(DISTINCT user_id) AS actives
FROM user_activity GROUP BY 1, 2 ORDER BY 1, 2;
```

**Pivot**
```sql
SELECT date,
  SUM(IF(channel='paid',    spend, 0)) AS paid,
  SUM(IF(channel='organic', spend, 0)) AS organic
FROM spend GROUP BY date;
-- or BigQuery's PIVOT operator
SELECT * FROM spend PIVOT(SUM(spend) FOR channel IN ('paid','organic'));
```

**Anti-join (orphans / referential integrity)**
```sql
SELECT a.* FROM fact a LEFT JOIN dim b USING (dim_id) WHERE b.dim_id IS NULL;
```

**Self-join: employee/manager**
```sql
SELECT e.name, m.name AS manager
FROM emp e LEFT JOIN emp m ON e.manager_id = m.id;
```

---

## 3. The traps they set

1. **`LEFT JOIN` silently becomes `INNER JOIN`** when you filter the right table in
   `WHERE` instead of `ON`:
   ```sql
   FROM a LEFT JOIN b ON a.k = b.k WHERE b.status = 'active'   -- ✗ drops unmatched a rows
   FROM a LEFT JOIN b ON a.k = b.k AND b.status = 'active'     -- ✓
   ```
2. **`COUNT(*)` vs `COUNT(col)`** — the second skips NULLs. `COUNT(DISTINCT col)` too.
3. **`NOT IN` with NULLs returns nothing.** If the subquery yields a single NULL, the
   whole predicate is UNKNOWN. Use `NOT EXISTS` or `LEFT JOIN ... IS NULL`.
4. **`NULL = NULL` is NULL, not TRUE.** Use `IS NULL`, `IS DISTINCT FROM`, or
   `COALESCE` before comparing. In BigQuery, `NULL`s *do* group together in `GROUP BY`
   and are equal in `USING`/join keys — a genuine inconsistency worth knowing.
5. **Join fan-out.** Joining a 1-row-per-day fact to a many-row dimension multiplies your
   measures. **This is the exact problem your README describes** — spend joined onto
   sessions divides cost-per-acquisition by the session count and the number looks great
   and is fiction. *Bring this up. It's a genuinely senior observation and you own it.*
   Fix: aggregate to a common grain **first**, then join.
6. **`HAVING` vs `WHERE`** — before vs after aggregation. Filtering in `WHERE` is cheaper
   because fewer rows reach the aggregate.
7. **`UNION` vs `UNION ALL`** — `UNION` deduplicates and therefore **sorts/shuffles**.
   Use `UNION ALL` unless you actually need dedup.
8. **Order of execution** — `FROM → WHERE → GROUP BY → HAVING → SELECT → QUALIFY → ORDER BY → LIMIT`.
   This is why you can't reference a `SELECT` alias in `WHERE` (but can in `GROUP BY`/`ORDER BY` in BigQuery).
9. **Division by zero** — `SAFE_DIVIDE(a, b)` in BigQuery; `NULLIF(b, 0)` elsewhere.
10. **Implicit cross join** from a comma in `FROM` — and `UNNEST` in `FROM` is one.

---

## 4. BigQuery-flavoured SQL you should show off

```sql
QUALIFY                      -- filter on a window function without a subquery
SAFE_DIVIDE / SAFE_CAST / SAFE.PARSE_DATE
ARRAY_AGG(x ORDER BY ts DESC LIMIT 1)[OFFSET(0)]     -- "latest value" without a window
STRUCT / ARRAY / UNNEST / LEFT JOIN UNNEST
EXCEPT / REPLACE:  SELECT * EXCEPT(pii_col), * REPLACE(LOWER(email) AS email)
APPROX_COUNT_DISTINCT / APPROX_QUANTILES / APPROX_TOP_COUNT
GENERATE_DATE_ARRAY('2026-01-01','2026-01-31')       -- date spine for gap filling
FARM_FINGERPRINT(key) / TO_HEX(MD5(TO_JSON_STRING(t)))   -- surrogate keys, hash_diff
PARSE_URL-style: NET.HOST(url), REGEXP_EXTRACT(url, r'[?&]utm_campaign=([^&]+)')
DATE_TRUNC / DATE_DIFF / TIMESTAMP_SUB / FORMAT_DATE
MERGE / CREATE OR REPLACE TABLE ... PARTITION BY ... CLUSTER BY ...
```

**Date spine for gap filling (very common ask):**
```sql
SELECT d, IFNULL(s.spend, 0) AS spend
FROM UNNEST(GENERATE_DATE_ARRAY('2026-01-01', '2026-01-31')) AS d
LEFT JOIN spend s ON s.date = d;
```

---

## 5. Optimisation — how you say it

> "I'd look at it in this order: **reduce rows**, **reduce columns**, **reduce shuffles**.
> Filter early and on the partition column so pruning happens; select only the columns I
> need; then look at the joins — is the grain right, is there an accidental fan-out, is
> one key skewed. After that, structural options: pre-aggregate into a mart or a
> materialised view, or denormalise into nested columns so a join becomes a column read.
> I'd confirm each change against the query plan and the bytes billed, not by feel."

**Index question in a BigQuery context:** there are no traditional indexes — partitioning
and clustering are the equivalents (plus **search indexes** for `SEARCH()` on text and
**vector indexes**). If they mean an OLTP database: B-tree vs hash, covering index,
composite index leftmost-prefix rule, index on a low-cardinality column is usually
useless, and every index slows writes.

---

## 6. Warehouse-agnostic theory they may sanity-check

- **ACID** — atomicity, consistency, isolation, durability. BigQuery is ACID **per job**;
  multi-statement transactions exist (`BEGIN TRANSACTION`).
- **Isolation levels** — read uncommitted/committed/repeatable read/serializable; dirty
  read, non-repeatable read, phantom read.
- **Normalisation 1NF/2NF/3NF** — atomic values / no partial dependency on part of a
  composite key / no transitive dependency. **Then say:** *"3NF is right for OLTP where
  writes dominate. In an analytical warehouse I denormalise deliberately — star schema, or
  nested columns in BigQuery — because scan cost and join shuffles dominate, not update anomalies."*
- **DROP vs DELETE vs TRUNCATE** — DDL/DML/DDL; structure+data / filtered rows / all rows;
  rollback only for `DELETE`; `TRUNCATE` resets identity and fires no triggers.
  In BigQuery: `TRUNCATE` is free, `DELETE` costs bytes scanned, and dropping a day's data
  should be **dropping a partition**, not a `DELETE`.
- **CTE vs subquery vs temp table** — readability / inline / materialised. In BigQuery a
  CTE referenced N times is **executed N times**; materialise into a temp table if it's expensive.
