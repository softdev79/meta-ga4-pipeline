"""Chapters: data quality & governance; DevOps for data; Linux & shell."""

from content_helpers import c, ch, h2, h3, p, ul, ol, code, co, tbl, cards

BLOCKS = [
    # ------------------------------------------------------------------ quality
    ch("Data Quality, Observability and Governance",
       "A pipeline that finishes on time with wrong data is worse than one that fails. "
       "Quality is where your operations mindset shines."),
    h2("Six dimensions of data quality"),
    tbl([
        ["Dimension", "Question", "Example check"],
        ["Completeness", "Is all expected data present?", "Row count within +/-20% of the "
                                                          "7-day average; no NULL keys"],
        ["Uniqueness", "Any unwanted duplicates?", "order_id is unique"],
        ["Validity", "Do values follow the rules/format?", "status IN (...); email matches a "
                                                           "pattern; amount >= 0"],
        ["Consistency", "Do related datasets agree?", "Sum of fact revenue = source system "
                                                      "total"],
        ["Accuracy", "Does data reflect reality?", "Spot-check against the source of record"],
        ["Timeliness / freshness", "Is it up to date?", "max(_loaded_at) within the last 6 "
                                                        "hours"],
    ], [1.3, 1.9, 2.6]),
    h2("Where to test"),
    ul("<b>At ingestion</b>: schema and type checks, required fields, file-level checks "
       "(size &gt; 0, expected row count from a trailer record).",
       "<b>After transformation</b>: dbt tests (unique, not_null, relationships), business "
       "rules, reconciliation against sources.",
       "<b>Before publishing</b>: block publishing a mart if critical tests fail (a "
       "'circuit breaker'), so consumers keep yesterday's good data rather than today's bad "
       "data.",
       "<b>Continuously</b>: freshness, volume and distribution anomaly monitoring "
       "(data observability tools: Monte Carlo, Elementary, Soda, Great Expectations / GX)."),
    code("python", r"""
from dataclasses import dataclass

import duckdb


@dataclass
class Check:
    name: str
    sql: str            # must return 0 rows / a zero count when the data is healthy
    severity: str = "error"   # 'error' blocks publish, 'warn' only alerts


CHECKS = [
    Check("orders_pk_unique",
          "SELECT order_id FROM silver.orders GROUP BY 1 HAVING COUNT(*) > 1"),
    Check("orders_amount_non_negative",
          "SELECT * FROM silver.orders WHERE amount < 0"),
    Check("orders_fresh",
          "SELECT 1 WHERE (SELECT MAX(_loaded_at) FROM silver.orders) "
          "< NOW() - INTERVAL 6 HOUR"),
    Check("orders_volume",
          '''SELECT 1 FROM (SELECT COUNT(*) n FROM silver.orders WHERE dt = $run_date) t
             WHERE n < 0.5 * (SELECT AVG(n) FROM ops.daily_counts WHERE tbl = 'orders')''',
          severity="warn"),
]


def run_checks(con: duckdb.DuckDBPyConnection, run_date: str) -> None:
    failures = []
    for chk in CHECKS:
        bad = con.execute(chk.sql, {"run_date": run_date}
                          if "$run_date" in chk.sql else None).fetchall()
        status = "FAIL" if bad else "PASS"
        print(f"[{status}] {chk.name} ({len(bad)} offending rows)")
        if bad and chk.severity == "error":
            failures.append(chk.name)
    if failures:
        raise SystemExit(f"blocking data-quality failures: {failures}")   # non-zero exit
""", "a minimal, framework-free check runner"),
    co("bridge", "A blocking quality check is a <b>job that ends NOTOK so downstream jobs "
                 "don't run</b>, exactly like a Control-M validation step that stops the "
                 "flow. Freshness monitoring is Control-M SLA / BIM for data instead of jobs."),
    h2("Observability: the five pillars"),
    ul("<b>Freshness</b>: when was the table last updated?",
       "<b>Volume</b>: did row counts change unexpectedly?",
       "<b>Schema</b>: did columns appear, disappear or change type?",
       "<b>Distribution</b>: did NULL rates or value ranges shift?",
       "<b>Lineage</b>: what is upstream and downstream of this table, and who is affected?"),
    h2("Governance, security and privacy"),
    ul("<b>Data catalog</b>: searchable metadata, owners, descriptions and lineage (DataHub, "
       "OpenMetadata, Unity Catalog, Dataplex, Purview, Atlan).",
       "<b>Lineage</b>: table- and column-level, ideally captured automatically (OpenLineage "
       "integrates with Airflow, Spark and dbt).",
       "<b>Access control</b>: role-based access, row-level security, column masking for PII.",
       "<b>PII handling</b>: classify sensitive columns; mask, hash/tokenise or drop them early "
       "(bronze to silver); encrypt; restrict raw access.",
       "<b>Regulations</b>: GDPR / DPDP Act (India) / CCPA: right to erasure (you must be able to "
       "delete a person's data, which shapes table design), data minimisation and retention "
       "limits.",
       "<b>Auditability</b>: who accessed or changed what, and when. Keep load metadata and "
       "query logs."),
    cards("Data quality and governance", [
        ("Six data-quality dimensions?",
         "Completeness, uniqueness, validity, consistency, accuracy, timeliness (freshness)."),
        ("What is a circuit breaker in a data pipeline?",
         "A blocking check that stops downstream publication when critical tests fail, so "
         "consumers see stale-but-correct data instead of fresh-but-wrong data."),
        ("Five pillars of data observability?",
         "Freshness, volume, schema, distribution, lineage."),
        ("What is data lineage and why does it matter?",
         "The map of where data comes from and where it flows. It's used for impact analysis, "
         "root-cause debugging, compliance and trust."),
        ("How do you protect PII in a warehouse?",
         "Classify it; minimise collection; mask, hash or tokenise; column-level security and "
         "masking policies; encryption; restricted raw zones; audit logs; retention policies."),
        ("What is OpenLineage?",
         "An open standard for emitting lineage metadata from tools like Airflow, Spark and dbt "
         "to a backend such as Marquez or a data catalog."),
        ("Warn vs error severity for tests?",
         "Error blocks the pipeline or publication. Warn alerts but lets data flow. Use it for "
         "soft anomalies like volume deviations."),
        ("Name three data quality / observability tools.",
         "dbt tests, Great Expectations (GX), Soda, Monte Carlo, Elementary, Datafold."),
    ]),

    # ------------------------------------------------------------------ devops
    ch("DevOps for Data: Git, Docker, CI/CD, IaC",
       "Software-engineering discipline applied to data. Your development background helps "
       "here; this chapter polishes it for data teams."),
    h2("Git workflow for data teams"),
    code("bash", r"""
git switch -c feat/orders-incremental        # short-lived feature branch
# ... edit models / DAGs / tests ...
git add -p                                     # review hunks before staging
git commit -m "orders: switch fct_orders to incremental merge with 3-day lookback"
git push -u origin feat/orders-incremental     # open a pull request; CI runs; peer review
# after approval: squash-merge to main -> CD deploys to prod
""", "feature-branch flow"),
    h2("Docker: package a pipeline"),
    code("dockerfile", r"""
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ ./src/
RUN useradd --create-home etl
USER etl                                   # never run as root

ENTRYPOINT ["python", "-m", "src.load_orders"]
CMD ["--date", "2024-03-10"]
""", "Dockerfile for a pipeline job"),
    code("bash", r"""
docker build -t orders-loader:1.4.0 .
docker run --rm -e DB_URL="$DB_URL" orders-loader:1.4.0 --date 2024-03-11
# In Airflow: KubernetesPodOperator(image="registry/orders-loader:1.4.0", arguments=[...])
""", "build and run"),
    h2("CI/CD with GitHub Actions"),
    code("yaml", r"""
name: data-ci
on:
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - run: pip install -r requirements-dev.txt
      - name: Lint and format
        run: |
          ruff check .
          ruff format --check .
          sqlfluff lint models/ --dialect bigquery
      - name: Unit tests
        run: pytest -q
      - name: DAG integrity
        run: pytest tests/test_dag_integrity.py -q
      - name: dbt build on CI schema
        env:
          DBT_PROFILES_DIR: ./ci
          GCP_SA_KEY: ${{ secrets.GCP_SA_KEY }}   # better: OIDC workload identity federation
        run: dbt build --target ci --select state:modified+ --defer --state ./prod-manifest
""", ".github/workflows/data-ci.yml"),
    h2("Infrastructure as Code with Terraform"),
    code("hcl", r"""
resource "google_storage_bucket" "lake" {
  name                        = "acme-data-lake-prod"
  location                    = "EU"
  uniform_bucket_level_access = true

  lifecycle_rule {
    condition { age = 90 }
    action {
      type          = "SetStorageClass"
      storage_class = "COLDLINE"
    }
  }
}

resource "google_bigquery_dataset" "analytics" {
  dataset_id = "analytics"
  location   = "EU"
  labels     = { team = "data-eng", env = "prod" }
}
""", "lake bucket + BigQuery dataset"),
    co("bridge", "Control-M Automation API brought <b>jobs-as-code</b>: JSON in Git, "
                 "build/deploy services, environments. If you've used it (or the Control-M "
                 "deploy descriptors), you've done CI/CD for workflows. Say so explicitly; it "
                 "maps straight onto 'DAGs in Git + CI + Terraform'."),
    cards("DevOps for data", [
        ("Why containerise pipeline jobs?",
         "Reproducible environments, dependency isolation, the same image in dev/CI/prod, and "
         "they're easy to run on Kubernetes (KubernetesPodOperator)."),
        ("What should CI run for a data repo?",
         "Lint/format (ruff, sqlfluff), unit tests, DAG import tests, dbt build/test on changed "
         "models in an isolated CI schema."),
        ("What is Infrastructure as Code?",
         "Defining cloud resources (buckets, datasets, IAM, clusters) in versioned code "
         "(Terraform, Pulumi) so environments are reproducible, reviewed and auditable."),
        ("Terraform plan vs apply?",
         "plan shows the diff between the code and real infrastructure without changing "
         "anything; apply executes those changes. State tracks what Terraform manages."),
        ("How should CI authenticate to the cloud?",
         "OIDC / workload identity federation, which gives short-lived tokens, instead of "
         "long-lived JSON keys stored as secrets."),
        ("Dev / staging / prod for data: how?",
         "Separate projects/accounts or schemas, parameterised by target (dbt targets, Airflow "
         "connections), with promotion through pull requests and CI/CD."),
    ]),

    # ------------------------------------------------------------------ linux
    ch("Linux and Shell for Data Engineers",
       "Probably your strongest area. A quick refresher focused on data tasks, plus a "
       "robust wrapper you can show off."),
    code("bash", r"""
head -5 orders.csv; wc -l orders.csv              # peek and count
cut -d',' -f3 orders.csv | sort | uniq -c | sort -rn | head   # value frequencies
awk -F',' 'NR>1 {s+=$5} END {print s}' orders.csv  # sum a column
grep -c ',cancelled,' orders.csv                   # count matching rows
zcat big.csv.gz | tail -n +2 | split -l 1000000 - part_   # stream + split a big file
jq -c '.data[] | {id, status}' response.json       # reshape JSON
find /data/in -name 'orders_*.csv' -mtime +7 -delete  # housekeeping
du -sh /data/* | sort -h                           # what is eating disk
""", "everyday one-liners"),
    code("bash", r"""
#!/usr/bin/env bash
# run_load.sh <YYYY-MM-DD> : wrapper suitable for Control-M, cron or Airflow BashOperator
set -Eeuo pipefail          # exit on error, unset vars, failures inside pipes
IFS=$'\n\t'

RUN_DATE="${1:?usage: run_load.sh YYYY-MM-DD}"
LOG_DIR="/var/log/etl"; mkdir -p "$LOG_DIR"
LOG="$LOG_DIR/load_${RUN_DATE}_$(date +%H%M%S).log"
LOCK="/tmp/run_load.lock"

exec 9>"$LOCK"
flock -n 9 || { echo "another run is active"; exit 75; }   # mutex, like a control resource

trap 'echo "FAILED at line $LINENO (exit $?)" | tee -a "$LOG"' ERR

echo "$(date -Is) start run_date=$RUN_DATE" | tee -a "$LOG"
python -m src.load_orders --date "$RUN_DATE" >>"$LOG" 2>&1
python -m src.quality_checks --date "$RUN_DATE" >>"$LOG" 2>&1
echo "$(date -Is) success" | tee -a "$LOG"
""", "production-grade job wrapper"),
    cards("Linux", [
        ("What does set -euo pipefail do?",
         "-e exits on any error, -u errors on unset variables, -o pipefail makes a pipeline fail "
         "if any command in it fails (not just the last)."),
        ("How do you prevent two copies of a script running at once?",
         "Use a lock: flock on a lock file (or a scheduler mutex/pool such as a Control-M "
         "control resource or max_active_runs=1)."),
        ("Five-field cron syntax?",
         "minute hour day-of-month month day-of-week. E.g. '0 2 * * 1-5' = 02:00 on weekdays."),
        ("Quickly find the most frequent values in column 3 of a CSV?",
         "cut -d',' -f3 file.csv | sort | uniq -c | sort -rn | head"),
    ]),
]
