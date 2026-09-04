"""BigQuery load layer.

Loads land in a staging table first, then MERGE into the target. The reason is
Meta's restatement behaviour: attributed conversions for a given day keep
changing for up to 28 days. An append-only load would produce duplicate rows
per ad per day, and any downstream SUM would be wrong in a way that is very
hard to spot -- the numbers stay plausible, they are just quietly inflated.

MERGE on ``(ad_id, date_start)`` makes re-reading a day idempotent, which in
turn makes backfills safe to re-run.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Iterable

from google.cloud import bigquery

logger = logging.getLogger(__name__)


class BigQueryLoader:
    """Loads connector output into partitioned, clustered BigQuery tables."""

    def __init__(
        self,
        project: str,
        dataset: str,
        client: bigquery.Client | None = None,
        location: str = "US",
    ) -> None:
        self.project = project
        self.dataset = dataset
        self.location = location
        self._client = client or bigquery.Client(project=project)

    # ------------------------------------------------------------------ #
    # Table management
    # ------------------------------------------------------------------ #

    def table_ref(self, table: str) -> str:
        return f"{self.project}.{self.dataset}.{table}"

    def ensure_table(
        self,
        table: str,
        schema: list[dict[str, str]],
        partition_field: str = "date_start",
        clustering: Iterable[str] = ("campaign_id", "adset_id", "ad_id"),
    ) -> bigquery.Table:
        """Create the table if absent.

        Partitioned on the reporting date and clustered on the campaign
        hierarchy. Almost every downstream query filters on a date range and
        groups by campaign, so this combination is what keeps a full-history
        table from scanning full history on every query.
        """
        table_id = self.table_ref(table)
        bq_schema = [
            bigquery.SchemaField(
                field["name"], field["type"], mode=field.get("mode", "NULLABLE")
            )
            for field in schema
        ]

        target = bigquery.Table(table_id, schema=bq_schema)
        target.time_partitioning = bigquery.TimePartitioning(
            type_=bigquery.TimePartitioningType.DAY, field=partition_field
        )
        target.clustering_fields = list(clustering)

        created = self._client.create_table(target, exists_ok=True)
        logger.info("Table ready: %s", table_id)
        return created

    # ------------------------------------------------------------------ #
    # Loading
    # ------------------------------------------------------------------ #

    def load_staging(
        self, table: str, rows: list[dict[str, Any]], schema: list[dict[str, str]]
    ) -> str:
        """Write a batch to a fresh staging table and return its name."""
        staging_table = f"_stg_{table}_{datetime.now(timezone.utc):%Y%m%d%H%M%S%f}"
        staging_id = self.table_ref(staging_table)

        ingested_at = datetime.now(timezone.utc).isoformat()
        payload = [{**row, "_ingested_at": ingested_at} for row in rows]

        job_config = bigquery.LoadJobConfig(
            schema=[
                bigquery.SchemaField(
                    field["name"], field["type"], mode=field.get("mode", "NULLABLE")
                )
                for field in schema
            ],
            write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE,
        )

        job = self._client.load_table_from_json(
            payload, staging_id, job_config=job_config, location=self.location
        )
        job.result()
        logger.info("Loaded %d rows into %s", len(payload), staging_id)
        return staging_table

    def merge(
        self,
        target_table: str,
        staging_table: str,
        merge_keys: list[str],
        schema: list[dict[str, str]],
    ) -> int:
        """MERGE staging into target on the natural key.

        Returns the number of affected rows. Drops the staging table
        afterwards -- staging tables that linger are how a dataset ends up
        with four hundred ``_stg_`` tables nobody dares delete.
        """
        target_id = self.table_ref(target_table)
        staging_id = self.table_ref(staging_table)

        columns = [field["name"] for field in schema]
        on_clause = " AND ".join(f"T.{key} = S.{key}" for key in merge_keys)
        update_clause = ", ".join(
            f"T.{column} = S.{column}" for column in columns if column not in merge_keys
        )
        insert_columns = ", ".join(columns)
        insert_values = ", ".join(f"S.{column}" for column in columns)

        query = f"""
        MERGE `{target_id}` AS T
        USING `{staging_id}` AS S
          ON {on_clause}
        WHEN MATCHED THEN
          UPDATE SET {update_clause}
        WHEN NOT MATCHED THEN
          INSERT ({insert_columns}) VALUES ({insert_values})
        """

        job = self._client.query(query, location=self.location)
        job.result()
        affected = job.num_dml_affected_rows or 0
        logger.info("MERGE into %s affected %d rows", target_id, affected)

        self._client.delete_table(staging_id, not_found_ok=True)
        return affected

    def upsert(
        self,
        table: str,
        rows: list[dict[str, Any]],
        schema: list[dict[str, str]],
        merge_keys: list[str],
    ) -> int:
        """Convenience wrapper: ensure, stage, merge."""
        if not rows:
            logger.warning("No rows to upsert into %s", table)
            return 0

        self.ensure_table(table, schema)
        staging_table = self.load_staging(table, rows, schema)
        return self.merge(table, staging_table, merge_keys, schema)
