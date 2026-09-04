"""Metadata-driven DAG generation for marketing sources.

One DAG per configured ad account, generated at parse time from
``config/sources.yaml``. Adding an account is a config entry, not a new file --
the same pattern as the 600-DAG framework this is modelled on.

Each DAG runs two extraction windows:

``incremental``
    Yesterday. The routine daily pull.

``restatement``
    A trailing 28-day window. Meta keeps revising attributed conversions for
    28 days after the fact, so a day loaded once is not final. Both windows
    MERGE on the same key, which makes re-reading a day idempotent.
"""

from __future__ import annotations

import logging
import os
from datetime import datetime, timedelta
from pathlib import Path

import yaml
from airflow.decorators import dag, task
from airflow.models import Variable
from airflow.providers.google.cloud.operators.bigquery import (
    BigQueryInsertJobOperator,
)

logger = logging.getLogger(__name__)

CONFIG_PATH = Path(__file__).parent.parent / "config" / "sources.yaml"
SQL_PATH = Path(__file__).parent.parent / "sql"

# Meta's conversion restatement window. Anything inside this many days is
# still subject to revision.
RESTATEMENT_DAYS = 28

DEFAULT_ARGS = {
    "owner": "data-engineering",
    "retries": 3,
    "retry_delay": timedelta(minutes=5),
    "retry_exponential_backoff": True,
    "max_retry_delay": timedelta(minutes=30),
    "depends_on_past": False,
}


def load_config() -> dict:
    with open(CONFIG_PATH) as handle:
        return yaml.safe_load(handle)


def render_sql(name: str) -> str:
    return (SQL_PATH / name).read_text()


def build_dag(account: dict, defaults: dict):
    """Construct one DAG for one ad account."""

    account_key = account["key"]
    project = defaults["bq_project"]
    dataset = defaults["bq_dataset"]

    @dag(
        dag_id=f"marketing__meta_ads__{account_key}",
        description=f"Meta Ads ingestion for {account['name']}",
        schedule=account.get("schedule", defaults["schedule"]),
        start_date=datetime.fromisoformat(account.get("start_date", "2026-01-01")),
        catchup=False,
        max_active_runs=1,
        default_args=DEFAULT_ARGS,
        tags=["marketing", "meta-ads", account_key],
    )
    def pipeline():

        @task
        def extract_and_load(window_type: str, **context) -> dict:
            """Pull one window from the Marketing API and MERGE it."""
            # Imported inside the task so DAG parsing stays fast -- the
            # scheduler re-parses every file on a short interval, and heavy
            # top-level imports are the usual cause of parse-time blowups.
            from marketing_pipeline.connectors.base import ExtractWindow
            from marketing_pipeline.connectors.meta_ads import (
                MetaAdsInsightsConnector,
            )
            from marketing_pipeline.http.client import MetaHTTPClient
            from marketing_pipeline.warehouse.bigquery import BigQueryLoader

            run_date = context["data_interval_end"].date()

            if window_type == "restatement":
                window = ExtractWindow(
                    start=run_date - timedelta(days=RESTATEMENT_DAYS),
                    end=run_date - timedelta(days=1),
                    is_restatement=True,
                )
            else:
                yesterday = run_date - timedelta(days=1)
                window = ExtractWindow(start=yesterday, end=yesterday)

            client = MetaHTTPClient(
                access_token=Variable.get("meta_access_token"),
                api_version=defaults.get("api_version", "v21.0"),
            )
            connector = MetaAdsInsightsConnector(
                client=client, ad_account_id=account["ad_account_id"]
            )
            loader = BigQueryLoader(project=project, dataset=dataset)

            total = 0
            for batch in connector.extract(window):
                total += loader.upsert(
                    table="stg_meta_ad_insights_daily",
                    rows=batch,
                    schema=connector.schema(),
                    merge_keys=connector.merge_keys,
                )

            logger.info("%s window loaded %d rows", window_type, total)
            return {"window": window_type, "rows": total}

        @task
        def check_freshness(**context) -> None:
            """Fail loudly if yesterday produced no spend rows.

            A pipeline that succeeds while loading nothing is worse than one
            that fails: the dashboards keep rendering, they just quietly stop
            moving, and nobody notices until someone asks why spend fell off
            a cliff.
            """
            from google.cloud import bigquery

            client = bigquery.Client(project=project)
            target = f"{project}.{dataset}.stg_meta_ad_insights_daily"
            query = f"""
                SELECT COUNT(*) AS row_count, SUM(spend) AS total_spend
                FROM `{target}`
                WHERE date_start = DATE_SUB(
                    DATE('{{{{ data_interval_end | ds }}}}'), INTERVAL 1 DAY
                )
                  AND account_id = '{account["ad_account_id"].replace("act_", "")}'
            """
            result = list(client.query(query).result())[0]

            if result.row_count == 0:
                raise ValueError(
                    f"Freshness check failed: no rows for {account_key} yesterday"
                )
            logger.info(
                "Freshness OK: %d rows, %.2f spend", result.row_count, result.total_spend or 0
            )

        build_sessions = BigQueryInsertJobOperator(
            task_id="build_ga4_sessions",
            configuration={
                "query": {
                    "query": render_sql("staging/stg_ga4_sessions.sql"),
                    "useLegacySql": False,
                    "destinationTable": {
                        "projectId": project,
                        "datasetId": dataset,
                        "tableId": "stg_ga4_sessions",
                    },
                    "writeDisposition": "WRITE_TRUNCATE",
                }
            },
            params={
                "ga4_project": defaults["ga4_project"],
                "ga4_dataset": defaults["ga4_dataset"],
                "start_date": "{{ macros.ds_add(ds, -%d) }}" % RESTATEMENT_DAYS,
                "end_date": "{{ ds }}",
            },
        )

        build_fact = BigQueryInsertJobOperator(
            task_id="build_paid_performance",
            configuration={
                "query": {
                    "query": render_sql("marts/fct_paid_performance_daily.sql"),
                    "useLegacySql": False,
                    "destinationTable": {
                        "projectId": project,
                        "datasetId": dataset,
                        "tableId": "fct_paid_performance_daily",
                    },
                    "writeDisposition": "WRITE_TRUNCATE",
                }
            },
            params={
                "project": project,
                "dataset": dataset,
                "start_date": "{{ macros.ds_add(ds, -%d) }}" % RESTATEMENT_DAYS,
                "end_date": "{{ ds }}",
            },
        )

        incremental = extract_and_load.override(task_id="extract_incremental")(
            "incremental"
        )
        restatement = extract_and_load.override(task_id="extract_restatement")(
            "restatement"
        )

        incremental >> restatement >> check_freshness() >> build_sessions >> build_fact

    return pipeline()


# Generate one DAG per configured account. This loop is the whole point of the
# metadata-driven pattern: onboarding an account is a YAML entry.
_config = load_config()
for _account in _config["accounts"]:
    if not _account.get("enabled", True):
        continue
    globals()[f"marketing__meta_ads__{_account['key']}"] = build_dag(
        _account, _config["defaults"]
    )
