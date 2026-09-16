# Round 2 cheat sheet — read this in the cab

*(Round 1's Spark/Hadoop/migration sheet is `CHEATSHEET.md` in the repo root. This one is
the GCP-native round.)*

---

## The answer template
**Define** → **Contrast with the alternative** (and say something true and good about it)
→ **Your project, with a number** → **When I wouldn't**. ~60 seconds.

---

## The 10 answers you must not fumble

**1. BigQuery architecture** — **Colossus** (storage) · **Capacitor** (columnar format) ·
**Dremel** (serving tree: root → mixers → leaves) · **Jupiter** (petabit network) ·
**slots** (units of compute) · **in-memory shuffle**. Storage/compute separated.

**2. Partitioning vs clustering** — 1 column, 10k partitions max, **pruning guaranteed and
visible in the dry run** · up to 4 columns, **order matters**, sorts within the partition,
**savings only known after the query runs**. Guardrails: `require_partition_filter=TRUE`
+ `maximum_bytes_billed`. **`LIMIT` does not reduce bytes scanned.**

**3. BigQuery cost levers** — no `SELECT *` · constant partition filter · cluster on
filter/join keys · `--dry_run` · `APPROX_COUNT_DISTINCT` · CTE used N times executes N
times → temp table · **batch load is free**, streaming isn't · materialised views + BI
Engine · partition expiry · editions vs on-demand · **start at
`INFORMATION_SCHEMA.JOBS_BY_PROJECT` ordered by `total_bytes_billed`**.

**4. MERGE / idempotency** — staging table → `MERGE` on the business key, and
**partition-filter the target inside the `ON` clause**. Airflow: write the partition of
**`{{ ds_nodash }}`** with `WRITE_TRUNCATE`, never `CURRENT_DATE()`. `catchup=False` +
`max_active_runs=1`. Sensors `mode='reschedule'` with a timeout. Teardown with
`trigger_rule='all_done'`.

**5. Airflow logical date** — a `@daily` run firing on the 16th is processing **the 15th**.
Airflow runs an interval **after it closes**. This is *why* `{{ ds }}`, not `CURRENT_DATE()`.

**6. Beam in one line** — **batch is streaming over a bounded PCollection.**
Windowing (fixed/sliding/session/global) = *how you slice event time* ·
**watermark** = the runner's belief about event-time progress ·
**trigger** = when a pane emits (early/on-time/late) ·
**allowed lateness** = how long late data is accepted; past that it's **dropped** →
**dead-letter via tagged output, never silently drop.**

**7. Exactly-once into BigQuery** — Pub/Sub is **at-least-once**; Dataflow gives
exactly-once *processing*; end-to-end needs an **idempotent sink**: Storage Write API with
stream offsets, or staging + `MERGE` on a business key. **It's a property of the sink, not
the runner.**

**8. Dataflow vs Dataproc vs BigQuery ELT** — event-time windowing / per-key state / PII
masked before landing → **Dataflow**. Existing Spark estate, lift-and-shift → **Dataproc**.
Expressible in SQL and already landed → **BigQuery ELT, which is my default.**
*"Compute I don't run is compute I don't tune."*

**9. Pub/Sub** — one message → **every subscription**; two consumers = **two
subscriptions**. At-least-once (exactly-once available) · ordering off by default,
opt-in per ordering key · 7-day unacked retention · **seek** for replay · **always
configure a dead-letter topic** · *the* health metric is
**`subscription/oldest_unacked_message_age`** · a **BigQuery subscription** removes
Dataflow entirely when the transform is "just land it."

**10. ROW_NUMBER / RANK / DENSE_RANK** on `100,100,90` → `1,2,3` / `1,1,3` / `1,1,2`.
Dedupe / competition rank / **Nth distinct value**. ROW_NUMBER needs a **tiebreaker** to be
deterministic — without one your "idempotent" pipeline isn't.

---

## SQL patterns — write from memory
```sql
QUALIFY ROW_NUMBER() OVER (PARTITION BY id ORDER BY updated_at DESC) = 1   -- dedupe
DENSE_RANK() OVER (PARTITION BY g ORDER BY x DESC) <= 3                    -- top N per group
SUM(v) OVER (ORDER BY d ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW)  -- running total
LAG(ts) OVER w -> new-session flag -> SUM(flag) OVER w -> GROUP BY          -- gaps & islands
FROM a LEFT JOIN b USING (k) WHERE b.k IS NULL                             -- anti-join
UNNEST(GENERATE_DATE_ARRAY(s,e)) d LEFT JOIN t ON t.date = d               -- date spine
```
**Traps:** a `WHERE` filter on the right table turns a LEFT JOIN into an INNER JOIN — put it
in `ON`. `NOT IN` with a NULL returns nothing. Default frame with ORDER BY is **RANGE**, not
ROWS. Joining different grains **fans out your measures**.

---

## Data quality — the structure
Six dimensions: **completeness, uniqueness, validity, accuracy, consistency, timeliness**.
Four gates: **contract at the edge → blocking check post-load → dbt tests in transform →
continuous monitoring**. Blocking gate for "downstream will be wrong"; alert-only monitor
for "suspicious" — *make everything blocking and people disable checks at 3 a.m.*
Alert on **data**, not just infrastructure: freshness, row-count delta, DQ pass rate.

---

## Your three headline stories
1. **Grain** — spend joined onto sessions fans out and divides CPA by the session count.
   The number looks great and it's fiction. Roll tracking **up** to ad × day.
2. **Restatement** — Meta revises conversions for **28 days**; append-only silently
   inflates every SUM. MERGE on `(ad_id, date_start)`, re-read a trailing 28-day window.
3. **Rate limiting** — Meta sends no `Retry-After`; it sends **utilisation headers** and
   **returns throttles as HTTP 400, error code 17**. Classify on `error.code`, throttle
   **proactively** between 75–95%, back off with **full jitter** so parallel accounts don't
   retry in lockstep.

Plus: **`async_percent_completion` hits 100 before `async_status` says `Job Completed`** —
treating 100% as done gives you empty result sets.
And: **a pipeline that succeeds while loading zero rows is worse than one that fails.**

---

## Bridges for JD items you didn't use here
- **Dataflow:** *"Not here — the transform is SQL and the volume doesn't justify a second
  compute engine. I reach for it when I need event-time windowing, per-key state, or PII
  masked before landing."*
- **Pub/Sub:** *"Ad spend settles daily — there's no such thing as real-time spend, so
  streaming would be complexity with no payoff."*
- **Something you genuinely haven't used:** name what it is, name when you'd reach for it,
  ask how they use it. **Never invent a number.**

---

## Things to say
"The trade-off there was…" · "That bit us when…" · "I'd push back on that if…" ·
"What's the latency requirement, and what decision does it change?" ·
"I'd ask whether you mean the second distinct value or the second row."

## Things not to say
"Basically" (every sentence) · "Best practice" without a reason · a rating of 9 or 10 ·
any number you're not sure of · anything negative about a current employer.

---

## Ask them
Migration engagement or steady-state platform? · Transformation in BigQuery/dbt or
Dataflow/Dataproc? · How is data quality enforced today — contracts or downstream
detection? · **What pages the on-call most often?** · Is there a junior layer I'd be
expected to bring up?

---

## Final 60 seconds before you dial
Breathe out slowly, twice. Water. Repo open in a second window. Pen and paper.
**Slow down 20% — nerves speed everyone up.** First answer is the 90-second intro; you
already know it. Go.
