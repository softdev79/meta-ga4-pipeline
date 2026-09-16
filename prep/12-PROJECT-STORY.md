# Your project story — rehearse this out loud

Candidate reports for HCLTech consistently say the technical round is **"discussion on
projects and services used"** and *"services used in big data projects in detail, including
scenarios explaining why particular services were chosen over alternatives."*

So: **the project narrative is the interview.** Everything else is follow-up.

---

## 1. The 3-minute pitch (memorise the beats, not the words)

> **The problem.** "Marketing wanted to know what they spent and what they actually got
> for it. That sounds like a join between ad spend and site tracking. It isn't — it's a
> grain problem and an identity problem wearing a join's clothing, and most implementations
> get one of them wrong.
>
> **The architecture.** Meta's Marketing API on one side, the GA4 BigQuery export on the
> other. A Python connector pulls insights via Meta's **async report jobs** — submit, poll,
> then page the materialised result — lands them into a staging table, and **MERGEs** into
> a partitioned, clustered fact. On the GA4 side, a staging model sessionises the raw event
> export and recovers platform IDs. Both meet at `fct_paid_performance_daily`, at **ad ×
> day**. Airflow orchestrates it, and the DAGs are **generated from a YAML source registry**
> rather than written by hand.
>
> **The three hard problems.**
> *Grain* — spend is already aggregated per ad per day, tracking is user-level. If you join
> spend onto sessions, the spend fans out across every session and your cost per
> acquisition silently divides by the session count. The number looks fantastic and it's
> fiction. So I roll tracking **up** to ad × day and join there, never the reverse.
> *Identity* — `utm_campaign=summer_sale` is not a join key; marketers rename campaigns
> mid-flight and history breaks. The fix isn't in SQL, it's at campaign setup: Meta's URL
> macros push the real platform IDs into the landing page query string, and the staging
> model recovers them as a stable key.
> *Restatement* — Meta revises attributed conversions for up to **28 days**. Yesterday's
> numbers aren't final. An append-only load duplicates rows per ad per day and every
> downstream SUM inflates. So the load is a MERGE on `(ad_id, date_start)` and the DAG
> deliberately re-reads a trailing 28-day window every run.
>
> **The opinionated bit.** Meta reports 7-day-click and 1-day-view, GA4 reports
> last-non-direct-click, the CRM reports what actually closed. Those three will never
> reconcile and shouldn't be forced to. I keep them as separate labelled columns and the
> mart **exposes the variance** instead of hiding it. Blending them into one unfalsifiable
> number is how attribution reporting loses the marketing team's trust.
>
> **The outcome.** Because spend joins to CRM outcomes rather than raw form fills, the mart
> produces cost per *qualified* lead and revenue-based ROAS rather than platform ROAS —
> which changes budget decisions, because a campaign can have the best CPL in the account
> and the worst revenue per lead."

**Timing:** ~3 minutes at a normal pace. **Practise it out loud twice today.** Reading it
silently does not build the muscle memory; you will stumble on "fan-out" and "restatement"
the first two times you say them aloud.

---

## 2. The hooks you've planted, and the follow-ups they invite

| Hook you say | Follow-up you'll get | Your answer lives in |
|---|---|---|
| "MERGE on a business key" | "Why not DELETE+INSERT? What's the cost?" | `01-BIGQUERY.md` §5 |
| "28-day restatement window" | "How do you know 28 is right? What if it changes?" | below |
| "DAGs generated from YAML" | "What breaks at scale? How do you test it?" | `04-COMPOSER-AIRFLOW.md` §4 |
| "Partitioned and clustered" | "On what, and why that order?" | `01-BIGQUERY.md` §2 |
| "Async report jobs" | "Why not the synchronous endpoint?" | below |
| "Fails loudly" | "Show me the check. What's the threshold?" | `08-DQ-GOVERNANCE.md` |
| "Rate limiting" | "How do you handle throttling?" | below |
| "15 tests, no credentials" | "What do you actually test?" | `05-PYTHON.md` §4 |

---

## 3. The six deep-dive answers (have these ready verbatim-ish)

**a) "Why async report jobs instead of the synchronous endpoint?"**
> "For anything beyond a few days at ad level, the synchronous endpoint times out or
> silently truncates — and silent truncation is the worse of the two. So the connector
> submits a report job, polls `async_status`, then pages the materialised result. There's a
> subtlety worth knowing: `async_percent_completion` reaches **100 before** `async_status`
> flips to `Job Completed`. Treating 100% as done is a classic source of empty result sets,
> and it's invisible in testing because it only shows up under real data volumes. I have a
> test named `test_polls_until_complete_then_pages_results` that covers exactly that."

**b) "How do you handle rate limiting?"**
> "Meta doesn't send `Retry-After`. It sends utilisation percentages in the
> `X-Business-Use-Case-Usage` header and expects you to slow down **before** you hit the
> wall — because once you're throttled, `estimated_time_to_regain_access` is measured in
> *minutes*. So the client parses those headers on every response and ramps a pause
> **quadratically between 75% and 95% utilisation**. A few seconds of self-imposed delay
> costs nothing; tripping the limit costs minutes of the batch window.
>
> The second half is error classification. **Meta returns throttles as HTTP 400, not 429** —
> error code 17, `User request limit reached`. If you classify on status code alone you
> treat a temporary throttle as a permanent failure. So the client classifies on
> `error.code` from the response body: codes 1, 2, 4, 17, 32, 341, 613 and the 80000-series
> are retryable; 100, 190 and 200 are terminal, and I fail fast on those rather than burning
> quota retrying an expired token.
>
> And the backoff uses **full jitter** — when several ad accounts ingest in parallel,
> un-jittered exponential backoff makes them all retry in lockstep and reproduces the
> thundering herd that caused the throttle in the first place."

*This answer alone is worth the interview. It is specific, it is operational, and almost no
candidate at this level can produce anything like it.*

**c) "How do you know your data is right?"**
> "Two mechanisms. A **freshness check** that raises when yesterday produced no rows —
> because a pipeline that succeeds while loading zero rows is worse than one that fails;
> dashboards keep rendering, they just quietly stop moving, and nobody notices until
> someone asks why spend fell off a cliff.
>
> And a **reconciliation signal**: the mart exposes `session_to_click_ratio` — platform
> link clicks against site-observed sessions. Sharp divergence almost always means a broken
> tag or a redirect stripping query parameters. You want that within hours, not at month
> end. That's the check that catches the failures the pipeline can't see, because the
> pipeline is working perfectly — the *instrumentation upstream* broke."

**d) "How would you add Google Ads?"**
> "Implement the `Connector` contract — `extract()`, `schema()`, `merge_keys` — and add a
> YAML entry. The loader, orchestration and freshness checks are source-agnostic by design,
> and `fct_paid_performance_daily` deliberately uses **platform-neutral column names** —
> `ad_group_id`, not `adset_id`; no `meta_` prefixes — specifically so Google Ads or Bing
> can `UNION` in without a schema change. That column-naming decision cost nothing at the
> time and is the difference between a day of work and a re-model."

**e) "What are the limitations / what would you do differently?"**
*Do not skip this. Volunteering limitations is the strongest credibility move available.*
> "Three honest ones.
> First, the GA4 dataset I demo against is Google's public sample, which contains no Meta
> traffic — so the `ad_id` join returns no matches against it. The join logic, grain
> handling and attribution modelling are real and correct; the *linked* dataset isn't.
> Point it at a property carrying tagged Meta traffic and the model resolves.
> Second, the 28-day restatement window is a constant, and it should be per-source config —
> different platforms and different conversion events settle at different speeds. That's a
> YAML field I haven't added.
> Third, at real scale I'd move the extract off the Airflow worker. Running the API pull
> inside the task is fine at two accounts; at two hundred it makes the worker the
> bottleneck and a retry re-pulls everything. I'd push it to a Cloud Run job or Dataflow
> and have Airflow orchestrate rather than execute."

**f) "What's the next step for it?"**
> "Closing the loop — pushing offline conversions and lead-quality scores back to Meta via
> the Conversions API, so the platform's bidding optimises toward *qualified* leads rather
> than raw form submissions. That turns the data platform from a reporting layer into
> something that moves CAC directly, which is a much easier conversation to have with a
> CFO than 'we improved dashboard freshness'."

---

## 4. Mapping the project onto every JD line

When they ask about a JD skill you haven't used heavily, **bridge** — don't apologise.

| JD requirement | Your bridge |
|---|---|
| BigQuery | partitioned+clustered fact, MERGE upsert, sessionisation SQL, nested GA4 export |
| GCS | raw landing / archive tier; "immutable raw is my replay tape" |
| **Dataflow** | "In this project transformation is ELT in BigQuery because the transform is expressible in SQL and the volume doesn't justify a second compute engine. I reach for Dataflow when I need **event-time windowing, per-key state, or PII masked before landing** — none of which apply here. [Then give a Dataflow example from prior work / `02-DATAFLOW-BEAM.md`.]" |
| **Pub/Sub** | "This pipeline is batch because ad spend settles daily — there is no such thing as real-time spend data, so streaming would be complexity with no payoff. Where I have used Pub/Sub is [prior work] …" |
| Composer/Airflow | the DAG factory, idempotency, freshness gate, task dependencies |
| Python | connector, rate limiter, retry with full jitter, ABC contract, 15 tests |
| Data warehousing | layered architecture, grain, star schema, platform-neutral columns |
| Data quality & governance | freshness check, reconciliation ratio, plural attribution |
| dbt/Talend | "The SQL models are already dbt-shaped — staging and marts, source-declared, testable. Porting them to dbt is mostly moving `ref()` in." |
| Coaching juniors | "The README exists so a new engineer understands *why*, not just *what*. Most handovers fail on the why." |
| CI/CD, Terraform | tests run with no credentials, config out of code, `.env.example` pattern |

**The rejection answer is as important as the selection answer.** "I didn't use Dataflow
here, and here's the rule I'd use to decide when I would" scores higher than pretending you
did. Interviewers are specifically listening for candidates who over-engineer.

---

## 5. If they ask about scale (and they will)

Be honest and reframe:
> "This particular repo is a reference implementation at small scale — two ad accounts. The
> patterns in it are the ones I've run in production at considerably larger scale: the
> metadata-driven DAG factory at around **600 generated DAGs**, and the staging-plus-MERGE
> restatement pattern on facts in the hundreds of millions of rows. I built this one to be
> readable, so the design decisions are visible rather than buried in a platform."

Then immediately pivot to the largest real numbers you own — rows/day, TB scanned, DAG
count, source count, SLA, cost saved. **Have those five numbers memorised before the call.**
Write them here now:

```
Largest volume I've handled:        ______ rows/day  /  ______ GB/day
Number of pipelines/DAGs I owned:   ______
Number of source systems:           ______
Tightest SLA I've met:              ______
A cost or runtime I improved:       from ______ to ______  ( ____% )
Team size / juniors mentored:       ______
```
