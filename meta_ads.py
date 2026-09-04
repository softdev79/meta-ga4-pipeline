"""Meta Marketing API insights connector.

Uses the **asynchronous** insights flow rather than the synchronous endpoint.
For anything beyond a few days at ad level the synchronous call either times
out or silently truncates; the async job is the only reliable path at
production volume.

The flow is three calls:

1. ``POST /{ad_account_id}/insights`` -> ``report_run_id``
2. ``GET /{report_run_id}`` -> poll ``async_status`` until completion
3. ``GET /{report_run_id}/insights`` -> page the materialised result set

Attribution is the part most implementations get wrong. Meta reports the same
conversion under multiple attribution windows, and if you sum the ``actions``
array without splitting by window you double-count. We request windows
explicitly and flatten each into its own column.
"""

from __future__ import annotations

import logging
import time
from datetime import date
from typing import Any, Iterator

from ..http.client import MetaAPIError, MetaHTTPClient
from .base import Connector, ExtractWindow

logger = logging.getLogger(__name__)

# Terminal states for an async report job.
STATUS_COMPLETE = "Job Completed"
STATUS_FAILED = {"Job Failed", "Job Skipped"}

# Windows we pull. Keeping 1d_view separate from 7d_click is what allows the
# mart layer to show platform-optimistic and conservative numbers side by side
# instead of blending them into a single unfalsifiable figure.
ATTRIBUTION_WINDOWS = ["1d_view", "7d_click"]

# Conversion actions worth promoting to their own columns. Everything else
# stays in the raw JSON so we never lose data we did not anticipate needing.
TRACKED_ACTIONS = {
    "lead": "leads",
    "offsite_conversion.fb_pixel_lead": "pixel_leads",
    "offsite_conversion.fb_pixel_complete_registration": "registrations",
    "offsite_conversion.fb_pixel_purchase": "purchases",
    "link_click": "link_clicks",
    "landing_page_view": "landing_page_views",
}

INSIGHT_FIELDS = [
    "account_id",
    "campaign_id",
    "campaign_name",
    "adset_id",
    "adset_name",
    "ad_id",
    "ad_name",
    "spend",
    "impressions",
    "reach",
    "frequency",
    "clicks",
    "inline_link_clicks",
    "actions",
    "action_values",
]


class MetaAdsInsightsConnector(Connector):
    """Daily ad-level insights for a single ad account."""

    source_name = "meta_ad_insights"
    merge_keys = ["ad_id", "date_start"]

    def __init__(
        self,
        client: MetaHTTPClient,
        ad_account_id: str,
        level: str = "ad",
        poll_interval: int = 5,
        poll_timeout: int = 1800,
        page_size: int = 500,
    ) -> None:
        # The API wants the act_ prefix; config files usually omit it.
        self.ad_account_id = (
            ad_account_id if ad_account_id.startswith("act_") else f"act_{ad_account_id}"
        )
        self.client = client
        self.level = level
        self.poll_interval = poll_interval
        self.poll_timeout = poll_timeout
        self.page_size = page_size

    # ------------------------------------------------------------------ #
    # Extraction
    # ------------------------------------------------------------------ #

    def extract(self, window: ExtractWindow) -> Iterator[list[dict[str, Any]]]:
        run_id = self._submit_job(window)
        self._await_completion(run_id)

        for page in self.client.paginate(
            f"{run_id}/insights", params={"limit": self.page_size}
        ):
            rows = [self._normalise(row) for row in page.get("data", [])]
            if rows:
                logger.info("Fetched %d rows from report %s", len(rows), run_id)
                yield rows

    def _submit_job(self, window: ExtractWindow) -> str:
        params = {
            "level": self.level,
            "fields": ",".join(INSIGHT_FIELDS),
            "time_increment": 1,  # one row per day, never a rolled-up range
            "time_range": _time_range(window.start, window.end),
            "action_attribution_windows": _json_list(ATTRIBUTION_WINDOWS),
            # Without this, Meta omits rows for ads that spent but had no
            # delivery, leaving unexplained gaps in the spend series.
            "filtering": "[]",
        }

        response = self.client.post(f"{self.ad_account_id}/insights", params=params)
        run_id = response.get("report_run_id")
        if not run_id:
            raise MetaAPIError(f"No report_run_id returned: {response}")

        logger.info(
            "Submitted insights job %s for %s (%s to %s)",
            run_id,
            self.ad_account_id,
            window.start,
            window.end,
        )
        return str(run_id)

    def _await_completion(self, run_id: str) -> None:
        """Poll until the report materialises.

        Note that ``async_percent_completion`` reaches 100 before
        ``async_status`` flips to complete. Treating 100% as done is a classic
        source of empty result sets -- we gate on the status field only.
        """
        deadline = time.time() + self.poll_timeout

        while time.time() < deadline:
            status = self.client.get(run_id)
            state = status.get("async_status", "")
            percent = status.get("async_percent_completion", 0)

            if state == STATUS_COMPLETE:
                logger.info("Report %s completed", run_id)
                return
            if state in STATUS_FAILED:
                raise MetaAPIError(f"Report {run_id} ended in state '{state}'")

            logger.debug("Report %s: %s (%s%%)", run_id, state, percent)
            time.sleep(self.poll_interval)

        raise MetaAPIError(
            f"Report {run_id} did not complete within {self.poll_timeout}s"
        )

    # ------------------------------------------------------------------ #
    # Normalisation
    # ------------------------------------------------------------------ #

    def _normalise(self, row: dict[str, Any]) -> dict[str, Any]:
        """Flatten one insights row into a warehouse-shaped record."""
        record: dict[str, Any] = {
            "account_id": row.get("account_id"),
            "campaign_id": row.get("campaign_id"),
            "campaign_name": row.get("campaign_name"),
            "adset_id": row.get("adset_id"),
            "adset_name": row.get("adset_name"),
            "ad_id": row.get("ad_id"),
            "ad_name": row.get("ad_name"),
            "date_start": row.get("date_start"),
            "date_stop": row.get("date_stop"),
            "spend": _to_float(row.get("spend")),
            "impressions": _to_int(row.get("impressions")),
            "reach": _to_int(row.get("reach")),
            "frequency": _to_float(row.get("frequency")),
            "clicks": _to_int(row.get("clicks")),
            "inline_link_clicks": _to_int(row.get("inline_link_clicks")),
        }

        record.update(self._flatten_actions(row.get("actions"), "count"))
        record.update(self._flatten_actions(row.get("action_values"), "value"))

        # Keep the untouched arrays. When someone asks in six months why a
        # number moved, the raw payload is the only thing that answers it.
        record["actions_raw"] = row.get("actions")
        record["action_values_raw"] = row.get("action_values")
        return record

    @staticmethod
    def _flatten_actions(
        actions: list[dict[str, Any]] | None, kind: str
    ) -> dict[str, float]:
        """Expand an actions array into one column per action x window.

        Produces e.g. ``leads_7d_click`` and ``leads_1d_view`` as separate
        columns. The ``value`` key present on every entry is Meta's default
        attribution setting; we ignore it in favour of the explicit windows so
        a change to the account's default setting cannot silently move history.
        """
        flattened: dict[str, float] = {}
        if not actions:
            return flattened

        suffix = "" if kind == "count" else "_value"

        for entry in actions:
            action_type = entry.get("action_type")
            column = TRACKED_ACTIONS.get(action_type)
            if not column:
                continue
            for attribution_window in ATTRIBUTION_WINDOWS:
                if attribution_window in entry:
                    key = f"{column}{suffix}_{attribution_window}"
                    flattened[key] = _to_float(entry[attribution_window])

        return flattened

    # ------------------------------------------------------------------ #
    # Schema
    # ------------------------------------------------------------------ #

    def schema(self) -> list[dict[str, str]]:
        fields = [
            {"name": "account_id", "type": "STRING", "mode": "REQUIRED"},
            {"name": "campaign_id", "type": "STRING"},
            {"name": "campaign_name", "type": "STRING"},
            {"name": "adset_id", "type": "STRING"},
            {"name": "adset_name", "type": "STRING"},
            {"name": "ad_id", "type": "STRING", "mode": "REQUIRED"},
            {"name": "ad_name", "type": "STRING"},
            {"name": "date_start", "type": "DATE", "mode": "REQUIRED"},
            {"name": "date_stop", "type": "DATE"},
            {"name": "spend", "type": "NUMERIC"},
            {"name": "impressions", "type": "INT64"},
            {"name": "reach", "type": "INT64"},
            {"name": "frequency", "type": "FLOAT64"},
            {"name": "clicks", "type": "INT64"},
            {"name": "inline_link_clicks", "type": "INT64"},
        ]

        for column in TRACKED_ACTIONS.values():
            for attribution_window in ATTRIBUTION_WINDOWS:
                fields.append(
                    {"name": f"{column}_{attribution_window}", "type": "FLOAT64"}
                )
                fields.append(
                    {"name": f"{column}_value_{attribution_window}", "type": "FLOAT64"}
                )

        fields += [
            {"name": "actions_raw", "type": "JSON"},
            {"name": "action_values_raw", "type": "JSON"},
            {"name": "_ingested_at", "type": "TIMESTAMP"},
        ]
        return fields


# ---------------------------------------------------------------------- #
# Helpers
# ---------------------------------------------------------------------- #


def _time_range(start: date, end: date) -> str:
    return f'{{"since":"{start.isoformat()}","until":"{end.isoformat()}"}}'


def _json_list(values: list[str]) -> str:
    inner = ",".join(f'"{value}"' for value in values)
    return f"[{inner}]"


def _to_float(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _to_int(value: Any) -> int:
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return 0
