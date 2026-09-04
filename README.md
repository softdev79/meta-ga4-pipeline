# Meta Ads + GA4 Marketing Data Pipeline

Ingestion and attribution pipeline joining Meta Marketing API spend data to
GA4 site-side tracking in BigQuery, orchestrated with Airflow.

Built to answer one question honestly: **what did we spend, and what did we
actually get for it?**

---

## Why this is harder than it looks

Joining ad spend to web tracking sounds like a join. It isn't. It's a grain
problem and an identity problem wearing a join's clothing, and most
implementations get one of the following wrong.

**Grain.** Spend is aggregate — one row per ad per day, already attributed by
the platform's own model. Tracking is user-level and event-level. If you join
spend onto sessions, the spend fans out across every session and your cost
per acquisition silently divides by the session count. The number looks
great. It's fiction. This pipeline rolls tracking **up** to `ad × day` and
joins there, never the reverse.

**Identity.** `utm_campaign=summer_sale` is not a join key. Marketers rename
campaigns mid-flight and your history breaks. The fix is at campaign setup,
not in SQL: Meta's URL parameter macros (`{{campaign.id}}`, `{{adset.id}}`,
`{{ad.id}}`) push the real platform IDs into the landing page query string,
where `stg_ga4_sessions` recovers them as a stable key.

**Restatement.** Meta revises attributed conversions for up to **28 days**
after the fact. Yesterday's numbers are not final. Append-only ingestion
produces duplicate rows per ad per day and every downstream `SUM` is quietly
inflated. Ingestion here is a `MERGE` on `(ad_id, date_start)`, and the DAG
deliberately re-reads a trailing 28-day window every run.

**Attribution.** Meta reports 7d-click and 1d-view. GA4 reports
last-non-direct-click. The CRM reports what actually closed. These will never
reconcile and shouldn't be forced to. Each is kept as a separate labelled
column and the mart **exposes the variance** rather than hiding it. Blending
them into one unfalsifiable number is how attribution reporting loses the
marketing team's trust.

---

## Architecture

```
Meta Marketing API                    GA4 BigQuery export
   (async insights jobs)                 (events_* / events_intraday_*)
          |                                        |
          v                                        v
   MetaAdsInsightsConnector                 stg_ga4_sessions
   - async job submit + poll                - sessionise on
   - cursor pagination                        user_pseudo_id + ga_session_id
   - rate-limit backoff                     - recover platform IDs from URL
   - attribution window split               - capture fbclid
          |                                        |
          v                                        |
   BigQueryLoader                                  |
   - staging table -> MERGE                        |
   - partitioned + clustered                       |
          |                                        |
          v                                        v
   stg_meta_ad_insights_daily  ------>  fct_paid_performance_daily
                                        (ad x day: spend + delivery
                                         + tracking + plural attribution)
                                                   |
                                                   v
                                            dim_campaign
                                        (naming-convention parsing)
```

---

## Design decisions worth defending

### Async insights jobs, not the synchronous endpoint

For anything beyond a few days at ad level, the synchronous endpoint times out
or silently truncates. The connector submits a report job, polls
`async_status`, then pages the materialised result.

One subtlety: `async_percent_completion` reaches 100 **before** `async_status`
flips to `Job Completed`. Treating 100% as done is a classic source of empty
result sets. The connector gates on the status field only —
`test_polls_until_complete_then_pages_results` covers exactly this case.

### Proactive throttling instead of reactive backoff

Meta doesn't send `Retry-After`. It sends utilisation percentages in
`X-Business-Use-Case-Usage` and expects you to slow down *before* hitting the
wall. Once throttled, `estimated_time_to_regain_access` is measured in
**minutes**.

So the client parses those headers on every response and ramps a pause
quadratically between 75% and 95% utilisation. A few seconds of self-imposed
delay costs nothing; tripping the limit costs minutes.

### Meta throttles arrive as HTTP 400

Error code 17 (`User request limit reached`) comes back as a 400, not a 429.
Classifying on status code alone means treating a throttle as a permanent
failure. The client classifies on `error.code` from the response body:

| Codes | Treatment |
|---|---|
| 1, 2, 4, 17, 32, 341, 613, 80000, 80004 | Retryable — backoff and retry |
| 100, 190, 200 | Terminal — fail fast, don't burn quota |

### Backoff uses full jitter

When several ad accounts ingest in parallel, un-jittered backoff makes them
all retry in lockstep — reproducing the thundering herd that caused the
throttle in the first place.

### Metadata-driven DAG generation

`config/sources.yaml` drives DAG creation at parse time. Onboarding an ad
account is a YAML entry, not a new DAG file. Retry semantics, restatement
handling and freshness checks are defined once and inherited by every account.

This is a small-scale version of a pattern I've run in production at
considerably larger scale (~600 generated DAGs).

### The freshness check fails loudly

A pipeline that succeeds while loading zero rows is worse than one that fails.
Dashboards keep rendering, they just quietly stop moving, and nobody notices
until someone asks why spend fell off a cliff. `check_freshness` raises when
yesterday produced no rows.

### The reconciliation signal

`fct_paid_performance_daily` exposes `session_to_click_ratio` — platform link
clicks against site-observed sessions. Sharp divergence usually means a broken
tag or a redirect stripping query parameters. You want that within hours, not
at month end.

---

## What this enables

Because spend joins to CRM outcomes rather than to raw form fills, the mart
produces **cost per qualified lead** and **revenue-based ROAS** rather than
platform ROAS. That distinction changes budget decisions: a campaign can have
the best CPL in the account and the worst revenue per lead.

The natural next step is closing the loop — pushing offline conversions and
lead-quality scores back to Meta via the Conversions API so bidding optimises
toward *qualified* leads rather than raw submissions. That turns the data
platform from a reporting layer into something that moves CAC directly.

---

## Running it

```bash
git clone <this-repo> && cd meta-ga4-pipeline
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"

pytest                      # 15 tests, no credentials needed
```

For a live run:

```bash
cp .env.example .env        # add META_ACCESS_TOKEN and GCP_PROJECT
```

Get a token from a [Meta developer app](https://developers.facebook.com/) with
a sandbox ad account — free, no ad spend required. Use a **system user token**;
short-lived user tokens expire mid-backfill and surface as error code 190.

### GA4 data

The config points at `bigquery-public-data.ga4_obfuscated_sample_ecommerce`, a
genuine GA4 export Google publishes (~Nov 2020–Jan 2021 of real ecommerce
traffic). It exercises the sessionisation and event-flattening logic against
real GA4 structure.

**Being straight about the limitation:** that sample contains no Meta traffic,
so the `ad_id` join in `fct_paid_performance_daily` returns no matches against
it. The join logic, grain handling and attribution modelling are real and
correct; the *linked* dataset is not. Point `ga4_project` / `ga4_dataset` at a
property carrying tagged Meta traffic and the full model resolves.

---

## Layout

```
config/sources.yaml                  # source registry -> drives DAG generation
dags/marketing_ingestion_dag.py      # DAG factory, one per ad account
src/marketing_pipeline/
  http/rate_limit.py                 # BUC header parsing, proactive throttle
  http/client.py                     # retry, backoff, error classification
  connectors/base.py                 # the ingestion contract
  connectors/meta_ads.py             # async job lifecycle, action flattening
  warehouse/bigquery.py              # staging -> MERGE upsert
sql/staging/stg_ga4_sessions.sql     # sessionisation, ID recovery
sql/marts/fct_paid_performance_daily.sql   # the spend x tracking join
sql/marts/dim_campaign.sql           # naming-convention parsing
tests/test_meta_ads.py               # 15 tests
```

## Extending to another platform

Implement `Connector` — `extract()`, `schema()`, `merge_keys` — and add a YAML
entry. The loader, orchestration and freshness checks are source-agnostic, and
`fct_paid_performance_daily` uses platform-neutral column names specifically so
Google Ads or Bing can `UNION` in without a schema change.
