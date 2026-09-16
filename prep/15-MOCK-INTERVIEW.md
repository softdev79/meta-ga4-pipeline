# Full mock interview — 60 minutes, with the interviewer's notes

Run this against a clock. Answer **out loud**. Do not read ahead to the notes before you
answer — the value is entirely in the gap between what you said and what's written here.

---

## Phase 1 — Warm-up (5 min)

**Q1. "Walk me through your background."**
> *Interviewer is scoring:* structure, stack keyword match, whether there's a theme or
> just a job list. 90 seconds. Should end on why this role.
> *Red flag:* chronological CV recital over 4 minutes.
> Your script: `00-BATTLE-PLAN.md` §6.

**Q2. "Tell me about your most recent project."**
> *Scoring:* can they explain a system to someone who doesn't know it? Do they lead with
> the business problem or with the tech list?
> *Your answer:* the 3-minute pitch in `12-PROJECT-STORY.md` §1.
> *Red flag:* "We used BigQuery, Airflow, Python and Dataflow" with no problem statement.

---

## Phase 2 — Project interrogation (15 min) — **the round that decides it**

**Q3. "Why BigQuery and not Snowflake or a Postgres warehouse?"**
> *Model answer:* serverless with no cluster to size or pause; storage/compute separation
> so a heavy ad-hoc query doesn't affect the load; GA4 export lands in BigQuery natively so
> choosing anything else means paying to move it out; native nested/repeated types fit the
> event data. Then the trade-off: *"Snowflake's multi-cluster warehouses give you cleaner
> workload isolation and its cost model is easier for finance to predict than per-TB
> scanned. If the client were multi-cloud I wouldn't argue hard for BigQuery."*
> *Scoring:* did they name the **rejected** option's genuine strength? A candidate who
> can't say anything good about the alternative hasn't really compared them.

**Q4. "You said you MERGE. Why not just append and deduplicate in the view?"**
> *Model answer:* append-and-dedup-at-read works and is cheaper to write, but you pay the
> dedup on every read forever, storage grows with every restatement, and the "correct"
> row depends on a window function every consumer has to get right. MERGE pays the cost
> once at write time and gives consumers a table they can trust naively.
> *"Where I'd flip: very high write volume where MERGE's join cost dominates, or where I
> need the full audit trail of every version — then append plus a current-state view, or
> `insert_overwrite` on the partition, is the better trade."*
> *Scoring:* is there a real trade-off, or just "MERGE is best practice"?

**Q5. "Your DAG re-reads 28 days every run. Isn't that wasteful?"**
> *Model answer:* Yes, and deliberately. The alternative is missing restated conversions
> and under-reporting, which is a correctness problem, and correctness beats efficiency
> here because the volume is small — 28 days of ad×day rows is thousands, not millions.
> The MERGE targets 28 partitions, not the whole table, so the cost is bounded and known.
> *"If the source were high-volume I'd narrow the window and add a weekly full-refresh
> reconciliation instead — pay the cost weekly rather than daily."*
> *Scoring:* do they know the cost of their own decision, or did they copy a pattern?

**Q6. "The YAML-driven DAG factory — what breaks?"**
> Your answer: `04-COMPOSER-AIRFLOW.md` §4. Parse time, testability, debuggability.
> *Scoring:* a candidate who says "nothing breaks" has never run it at scale.

**Q7. "Where does Dataflow fit in this, and if it doesn't, why is it on your CV?"**
> *This is a trap question and it's fair.* Answer: `12-PROJECT-STORY.md` §4.
> Name the decision rule — event-time windowing, per-key state, PII before landing — then
> give a Dataflow example from other work.
> *Red flag:* retrofitting Dataflow into a project that didn't need it, to look good.
> *Green flag:* "I deliberately didn't use it, here's when I would."

---

## Phase 3 — Technical depth, rapid (15 min)

**Q8.** "Partitioning vs clustering — when do you use which?" → `01-BIGQUERY.md` §2.
**Q9.** "The query plan shows one stage taking 90% of the time. What's happening?" → skew;
prove it, then AQE-equivalent options, broadcast, salt, and check whether the key is junk
(NULL/`-1`/empty string causes half of real 'skew').
**Q10.** "Explain watermarks and late data." → `02-DATAFLOW-BEAM.md` §4. Must include
allowed lateness **and** the dead-letter path.
**Q11.** "Pub/Sub is at-least-once. How do you get exactly-once into BigQuery?" →
`02-DATAFLOW-BEAM.md` §10. The point: **it's a property of the sink, not the runner.**
**Q12.** "A DAG ran green but the data's wrong. Debug it." → `04-COMPOSER-AIRFLOW.md` §7.
Hypothesis → diagnostic → recovery → **systemic fix**.
**Q13.** "Write me SQL for the second-highest salary per department."
> ```sql
> SELECT department, salary FROM emp
> QUALIFY DENSE_RANK() OVER (PARTITION BY department ORDER BY salary DESC) = 2;
> ```
> *Say first:* "I'll assume second-highest **distinct** salary — if you mean the second row
> including ties, that's ROW_NUMBER instead." **The clarification scores more than the SQL.**
**Q14.** "Write a Python function that deduplicates records keeping the latest."
> `05-PYTHON.md` §2a — **and bridge to the SQL version.**
**Q15.** "How do you make a pipeline idempotent?" → `04-COMPOSER-AIRFLOW.md` §3. Five points.

---

## Phase 4 — Design / scenario (15 min)

**Q16. "Client has 30 source systems, wants a GCP warehouse in 6 months. Design it."**
> `11-SYSTEM-DESIGN.md` Scenario 1 and 5. Ask three clarifying questions first.
> *Scoring:* metadata-driven approach, layered architecture, DQ gates, and — critically —
> the **thin vertical slice first** sequencing answer. Candidates who design the whole
> platform before delivering anything get marked down at this level.

**Q17. "Now they want real-time. What changes?"**
> Scenario 2. Score depends on whether they push back: *"what decision changes if this is
> 5 minutes old instead of 6 hours?"* before designing.

**Q18. "Their BigQuery bill doubled last month. First three things you check?"**
> Scenario 6. `INFORMATION_SCHEMA.JOBS_BY_PROJECT` must be the first sentence.

---

## Phase 5 — Behavioural & close (10 min)

**Q19.** "Tell me about a production incident you owned." → `13-BEHAVIORAL.md` §3.
**Q20.** "Tell me about bringing a junior engineer up to speed." → `13-BEHAVIORAL.md` §3.
**Q21.** "A stakeholder insists on a metric you think is wrong. What do you do?" → §3.
**Q22.** "Rate yourself on GCP out of 10." → **8, with a calibrated qualifier.** Never 10.
**Q23.** "Questions for us?" → `00-BATTLE-PLAN.md` §8. Ask 2–3.

---

## Self-scoring

After the mock, mark each answer:

| | Criterion |
|---|---|
| ☐ | Did I define the thing in one clean sentence? |
| ☐ | Did I name the alternative I rejected **and something genuinely good about it**? |
| ☐ | Did I attach a concrete example from my own work? |
| ☐ | Did I give a **number**? |
| ☐ | Did I state a trade-off or a "when I wouldn't"? |
| ☐ | Did I stop, or did I keep talking past the answer? |
| ☐ | On scenarios: did I ask a clarifying question before designing? |

**Anything under 4 boxes on a core question → that's what you revise next.**

---

## The five answers that most often decide this round

If you nail only five things today, make them these:

1. **The 3-minute project pitch** — grain, identity, restatement. (`12`)
2. **"Why Dataflow / why not Dataflow"** — the decision rule, not the feature list. (`02` §7)
3. **"The DAG was green but the data was wrong"** — the full four-step answer. (`04` §7)
4. **Partitioning vs clustering + BigQuery cost levers.** (`01` §2–3)
5. **Coaching a junior** — because it's explicitly in the JD and almost nobody prepares it. (`13` §3)
