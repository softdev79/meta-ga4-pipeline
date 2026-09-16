# Data quality & governance

The JD calls this out explicitly: *"Develop and implement data quality and governance
procedures to ensure the accuracy and reliability of data."* Most candidates answer this
vaguely. A structured answer here is a large differentiator.

---

## 1. The six dimensions — the framework to anchor on

| Dimension | Question it answers | Test |
|---|---|---|
| **Completeness** | is anything missing? | row counts vs source, null rate on required fields, missing date partitions |
| **Uniqueness** | are there duplicates at the grain? | `COUNT(*) = COUNT(DISTINCT key)` |
| **Validity** | does it conform to the rules? | type, range, regex, accepted values, FK exists |
| **Accuracy** | does it match reality? | reconcile against the source system or a trusted control total |
| **Consistency** | does it agree with itself/other systems? | cross-system totals, referential integrity |
| **Timeliness** | is it fresh enough? | max(event_ts) vs now, partition arrival SLA |

**Say the framework, then immediately ground it:**
> "Accuracy is the one you can't test in isolation — it needs a reconciliation against
> something outside the pipeline. In my pipeline that's `session_to_click_ratio`: platform
> link clicks against site-observed sessions. If those diverge sharply it almost always
> means a broken tag or a redirect stripping query parameters. You want that signal within
> hours, not at month end when finance asks why the numbers moved."

---

## 2. Where the checks live (four gates)

1. **At the edge — contract validation.** Pub/Sub schemas (Avro/Proto), or JSON Schema on
   the connector. Reject or dead-letter at ingest; never let malformed data into raw silently.
2. **Post-load, pre-transform — the gate.** `BigQueryCheckOperator` /
   `BigQueryValueCheckOperator` / `BigQueryIntervalCheckOperator` between load and marts.
   **This is the single highest-value control**, because it stops bad data from propagating
   into everything downstream.
3. **In-transform — dbt tests.** `unique`, `not_null`, `accepted_values`, `relationships`,
   `dbt_utils.expression_is_true`, `dbt_expectations` for distribution checks, plus
   `dbt source freshness`. `--warn-error` in CI; `severity: warn` vs `error` per test.
4. **Continuous monitoring — observability.** Dataplex auto data quality scans, or a
   metrics table plus Cloud Monitoring alerts; anomaly detection on row counts and
   distributions rather than only hard thresholds.

**Circuit breaker vs monitor — name the distinction:**
> "There are two kinds of check and conflating them is a design error. A **blocking gate**
> stops the pipeline — I use it for things that make downstream output *wrong*: duplicate
> keys at the grain, null on a join key, zero rows loaded. A **non-blocking monitor**
> raises an alert but lets the run proceed — I use it for things that are *suspicious*:
> a 30% row-count swing, a distribution shift. If you make everything blocking, people
> start disabling checks at 3 a.m., and then you have no checks at all."

That last sentence is earned-experience phrasing and interviewers respond to it.

---

## 3. The checks I'd implement on day one (be concrete)

```sql
-- 1. Freshness: yesterday produced rows at all
SELECT COUNT(*) FROM `mart.fct_paid_performance_daily`
WHERE date = DATE_SUB(CURRENT_DATE(), INTERVAL 1 DAY);     -- assert > 0

-- 2. Uniqueness at the declared grain
SELECT COUNT(*) - COUNT(DISTINCT FARM_FINGERPRINT(CONCAT(ad_id, CAST(date AS STRING))))
FROM `mart.fct_paid_performance_daily`;                     -- assert = 0

-- 3. Volume anomaly: today vs trailing 7-day median
WITH daily AS (SELECT date, COUNT(*) n FROM t GROUP BY 1)
SELECT n, APPROX_QUANTILES(n, 2)[OFFSET(1)] OVER (ORDER BY date ROWS BETWEEN 7 PRECEDING AND 1 PRECEDING)
FROM daily;                                                 -- alert if outside ±30%

-- 4. Referential integrity (orphan facts)
SELECT COUNT(*) FROM fct f LEFT JOIN dim d USING (ad_id) WHERE d.ad_id IS NULL;

-- 5. Business rule / reconciliation
SELECT ABS(SUM(spend) - (SELECT SUM(spend) FROM source_control_total)) < 0.01;
```

Write the results to a **`dq_results` table** with run_id, check_name, status, observed
value, threshold. *"Storing results means I can trend quality over time and show a client
that the pipeline's reliability is improving, rather than just asserting it."*

---

## 4. Governance on GCP — the tool map

- **Dataplex** — the unified governance plane: data lakes/zones/assets over GCS and
  BigQuery, **auto data quality scans** (null, range, regex, uniqueness, custom SQL, at
  row and aggregate level), **data profiling**, **catalog** (metadata, search, tags,
  business glossary — Data Catalog is now part of Dataplex), **lineage**, and
  **policy tags** for column-level security.
- **Data Catalog / Dataplex Catalog** — discovery, tag templates (owner, PII class,
  retention, SLA), business glossary.
- **Data lineage API** — automatic column-level lineage for BigQuery and Dataflow jobs.
  *"Lineage is what turns 'this number is wrong' from a two-day investigation into a
  two-minute one."*
- **DLP / Sensitive Data Protection** — discover and classify PII, then de-identify:
  masking, bucketing, **format-preserving tokenisation** (so a tokenised ID still joins).
- **Cloud Audit Logs** — admin activity (always on) and **data access logs (must be
  enabled, and they cost)**; export to BigQuery for access reporting.
- **Analytics Hub** — publish/subscribe datasets across org boundaries without copying.
- **Access control layers** — see `01-BIGQUERY.md` §9.

---

## 5. Data contracts — the modern answer, worth volunteering

> "The root cause of most data quality incidents isn't the pipeline, it's an upstream team
> changing a field without knowing anyone depended on it. A **data contract** makes the
> schema, semantics, SLA and ownership an explicit agreement enforced in the producer's
> CI — a breaking change fails their build rather than my 3 a.m. pager. Technically it's
> a schema registry plus tests; organisationally it's the harder and more important half.
> Where I can't get a producer to adopt one, the fallback is a permissive landing zone —
> raw payload plus ingest timestamp — so a schema change **degrades** my pipeline instead
> of halting it, plus an alert on schema drift."

---

## 6. Governance the organisational side (Platform Engineer III territory)

- **Ownership**: every dataset has a named owner and a steward; ownership in the catalog,
  not in someone's head.
- **Classification**: public / internal / confidential / restricted, driving access and retention.
- **Retention & deletion**: partition expiry, GCS lifecycle rules, and a documented
  **right-to-erasure** path for GDPR/DPDP — which is genuinely hard in an immutable raw
  layer, so say how: keep PII in a separate, keyed vault table that can be purged, and
  reference it by token everywhere else.
- **Change management**: schema changes go through PR; additive changes are backward
  compatible, breaking changes get a version and a deprecation window.
- **Access request process**: a request, an approver, a time bound, an audit trail.
  Standing broad access is the finding every auditor writes up.

---

## 7. If asked "how would you improve data quality at our client?"

Answer as a consultant, in three moves:

1. **Measure before fixing.** *"I'd start by instrumenting: freshness, volume and
   uniqueness on the top 20 consumed tables, and a dq_results table. You cannot get
   funding to fix quality without a number showing it's bad."*
2. **Stop the bleeding at the highest-leverage point.** *"Then a blocking gate between
   load and marts on the tables the business actually reports from — that's usually five
   tables, not five hundred."*
3. **Push left.** *"Then move checks upstream toward the producers, with contracts, so the
   failure happens where it can be fixed rather than where it's detected."*

Then the honest caveat that makes it credible: *"And I'd be explicit with stakeholders
that quality will appear to get worse first, because we start detecting problems that were
already there. If you don't set that expectation up front, the first month of alerts looks
like the new pipeline broke something."*
