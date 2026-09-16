# IAM, monitoring, Terraform, CI/CD

"Good to have" in the JD — which in practice means it's where you pick up the points that
separate you from the other shortlisted candidate.

---

## 1. IAM — the mental model

**Principal → Role → Resource**, granted by an **allow policy** attached at some level of
the **resource hierarchy** (Organisation → Folder → Project → Resource). **Policies are
inherited downward and are additive** — you cannot revoke at a child what was granted at a
parent (that's what **deny policies** are for, which are newer and evaluated first).

**Role types:** **basic** (Owner/Editor/Viewer — *never use in production*, far too broad),
**predefined** (`roles/bigquery.dataViewer`), **custom** (least privilege, but you own
maintaining it as Google adds permissions).

**Service accounts** — identity for workloads. The key points:
- **Never download JSON keys.** They don't expire, they leak into git, and they're the #1
  finding in every GCP security review. Use **Workload Identity Federation** (for GKE, and
  for external CI like GitHub Actions) or **service account impersonation**
  (`roles/iam.serviceAccountTokenCreator`) so credentials are short-lived.
- **One service account per workload**, not one shared "etl-sa" with Editor. Blast radius.
- **`roles/iam.serviceAccountUser`** is what lets a human deploy a job *as* a service
  account — a subtle and frequently-misconfigured permission.

**Groups, not users.** Grant to `data-engineers@company.com`; joining the team is an IdP
change, not 40 IAM edits.

**The BigQuery analyst answer** (they like this concrete one): `bigquery.jobUser` on the
**project** (jobs are billed to a project) plus `bigquery.dataViewer` on the **dataset**.
Only `dataViewer` → "I can see the table but every query fails."

**Least privilege in practice:** start from predefined roles, use the **IAM Recommender**
(it flags permissions granted but unused for 90 days), review quarterly, and use
**short-lived elevated access** rather than standing admin.

---

## 2. Cloud Logging & Monitoring

- **Cloud Logging**: log sinks → BigQuery/GCS/Pub/Sub. **Log-based metrics** turn a log
  pattern into a numeric metric you can alert on. Log buckets with retention; exclusion
  filters to control cost (logging bills on ingestion — a chatty debug logger is a real
  line item).
- **Audit logs**: Admin Activity (always on, free), **Data Access (off by default, costs
  money, but it's what auditors ask for)**, System Event, Policy Denied.
- **Cloud Monitoring**: metrics, dashboards, uptime checks, **alerting policies** →
  notification channels (Slack/PagerDuty/email/webhook). **SLOs** with error budgets.
- **Cloud Trace / Profiler / Error Reporting** for the application tier.

**The metrics I'd alert on for a data platform** — have this list ready:

| Layer | Metric | Why |
|---|---|---|
| Pub/Sub | `subscription/oldest_unacked_message_age` | *the* streaming health signal |
| Pub/Sub | dead-letter topic message count > 0 | poison messages |
| Dataflow | system lag, backlog seconds, worker restarts, elements dropped due to lateness | streaming correctness + throughput |
| Composer | task failure rate, scheduler heartbeat, **DAG parse time**, SLA misses | orchestration health |
| BigQuery | slot utilisation, query concurrency, **bytes billed per day**, job failure rate | cost + contention |
| Data | freshness (max event ts), row count vs trailing median, DQ check pass rate | **the one most teams forget** |

**The framing that lands:**
> "Most monitoring I inherit watches infrastructure, so it tells you the pipeline *ran*.
> It doesn't tell you the pipeline was *right*. The alerts that have actually saved me are
> data-level: freshness, row-count deltas and reconciliation ratios. A green DAG with zero
> rows loaded is the failure mode that costs a client real money, because nothing alerts
> and the dashboards keep rendering."

---

## 3. Terraform

**Why IaC:** reproducible environments, peer-reviewed infrastructure changes, a diff before
you apply, and dev/stage/prod that are actually the same.

**Core:** `init` / `plan` / `apply` / `destroy`; **state** (remote backend in a **GCS
bucket with versioning and object locking**, never local, never in git — it contains
secrets in plaintext); **modules** for reuse; `variables.tf` / `outputs.tf` /
`terraform.tfvars`; **workspaces** *or* (better) separate state files per environment;
`import` for existing resources; `for_each` over `count` (count reindexes on deletion and
destroys the wrong resource — a classic production incident); `lifecycle { prevent_destroy = true }`
on stateful things like a BigQuery dataset or a Cloud SQL instance; `depends_on` for
implicit ordering; **`terraform fmt` + `validate` + `tflint` + `checkov`/`tfsec` in CI**.

```hcl
resource "google_bigquery_table" "fct_paid_performance_daily" {
  dataset_id          = google_bigquery_dataset.marts.dataset_id
  table_id            = "fct_paid_performance_daily"
  deletion_protection = true

  time_partitioning {
    type                     = "DAY"
    field                    = "date"
    require_partition_filter = true
  }
  clustering = ["campaign_id", "ad_id"]
  schema     = file("${path.module}/schemas/fct_paid_performance_daily.json")
}
```

**The nuance that shows experience:**
> "I manage **infrastructure** in Terraform — datasets, buckets, topics, service accounts,
> Composer environments, IAM — but I don't manage rapidly-changing **table schemas** in it,
> because a column addition shouldn't require a `terraform apply` and Terraform's handling
> of schema drift on a table with data is unpleasant. Schemas belong with the
> transformation code, in dbt or migration scripts. Drawing that boundary wrong is how
> teams end up afraid to run `plan`."

---

## 4. CI/CD

**A pipeline for a data repo (say it as stages):**
1. **Pre-commit / lint** — `ruff`, `black`, `sqlfluff`, `terraform fmt`.
2. **Unit tests** — `pytest`, no cloud credentials needed. *(Your repo: 15 tests, no creds.)*
3. **DAG integrity test** — import the DagBag, assert zero import errors and that every
   DAG has owner/retries/SLA/tags.
4. **Build & scan** — container image, `trivy`/vulnerability scan, SBOM.
5. **Deploy to dev** — Terraform plan/apply, sync DAGs to the Composer GCS bucket,
   `dbt build` against a dev dataset.
6. **Integration / data tests** — `dbt build --select state:modified+` (Slim CI) on a
   sample; reconcile row counts.
7. **Promote** — manual approval gate → prod. Tagged release, and a **documented rollback**:
   for data, rollback means re-running the previous version *and* restating affected
   partitions, which is why idempotency is a deployment concern, not just a design one.

**Tools:** Cloud Build (GCP-native, triggers on push), GitHub Actions / GitLab CI / Jenkins
(the JD names Jenkins — declarative `Jenkinsfile`, shared libraries, agents, credentials
binding), Artifact Registry for images, Cloud Deploy for progressive delivery.

**Branching:** trunk-based with short-lived feature branches and PR review, or GitFlow for
clients with fixed release trains. Environment per branch for data is expensive — prefer
one dev dataset per developer with dbt's schema-per-target.

---

## 5. Agile (the JD asks)

Keep it short and unbuzzwordy:
> "Two-week sprints, refinement mid-sprint, story points, definition of done that includes
> tests and documentation, and a demo that shows working data, not slides. For data work I
> push hard on two things: **spikes** for anything involving an unknown source system,
> because estimating an undocumented API is fiction, and **treating data quality issues as
> defects with the same priority as code defects** — otherwise they get carried forever."

---

## 6. AI/ML & Gen AI (the "good to have")

Don't overclaim. Show a working model of where it fits:
- **BigQuery ML** — train inside the warehouse in SQL: `ARIMA_PLUS` for forecasting spend,
  `KMEANS` for segmentation, `LOGISTIC_REG` for lead scoring, `ML.PREDICT` / `ML.EVALUATE`.
  *"For lead scoring on my marketing mart, BQML is compelling because the features already
  live in the warehouse and there's no serving infrastructure to stand up."*
- **Vertex AI** — training, pipelines, **Feature Store**, model registry, endpoints, and
  the honest note that **the data engineer's job in ML is the feature pipeline and
  preventing training/serving skew**, not the model.
- **Gen AI in the warehouse** — `ML.GENERATE_EMBEDDING`, `VECTOR_SEARCH` with vector
  indexes, `AI.GENERATE_TEXT` for classification/extraction over text columns. RAG over
  warehouse data without a separate vector database.
- **Where I'd actually use an LLM in a data platform** (a good, grounded answer):
  *"Documentation and metadata generation, converting business questions to SQL against a
  governed semantic layer, classifying free-text fields, and drafting dbt tests from a
  profile. I'd be careful about anything where a plausible-but-wrong answer reaches a
  business user unlabelled — which is why I'd put it behind a governed semantic layer
  rather than over raw tables."*
