"""Tests for rate-limit handling and the Meta insights connector."""

from __future__ import annotations

import json
from datetime import date

import pytest
import responses

from marketing_pipeline.connectors.base import ExtractWindow
from marketing_pipeline.connectors.meta_ads import MetaAdsInsightsConnector
from marketing_pipeline.http.client import MetaAPIError, MetaHTTPClient
from marketing_pipeline.http.rate_limit import (
    HARD_LIMIT_PCT,
    SOFT_LIMIT_PCT,
    parse_usage,
)

BASE = "https://graph.facebook.com/v21.0"


def buc_header(call_count=0, cputime=0, total_time=0, regain=0) -> str:
    return json.dumps(
        {
            "123456789": [
                {
                    "type": "ads_insights",
                    "call_count": call_count,
                    "total_cputime": cputime,
                    "total_time": total_time,
                    "estimated_time_to_regain_access": regain,
                }
            ]
        }
    )


# --------------------------------------------------------------------- #
# Rate limiting
# --------------------------------------------------------------------- #


class TestRateLimitParsing:
    def test_parses_all_usage_dimensions(self):
        usage = parse_usage(
            {
                "X-Business-Use-Case-Usage": buc_header(
                    call_count=40, cputime=55, total_time=30
                ),
                "X-Ad-Account-Usage": json.dumps({"acc_id_util_pct": 12.5}),
            }
        )
        assert usage.call_count_pct == 40
        assert usage.cpu_time_pct == 55
        assert usage.ad_account_pct == 12.5

    def test_worst_pct_is_the_binding_constraint(self):
        """Any single dimension can throttle us, so the max is what matters."""
        usage = parse_usage(
            {"X-Business-Use-Case-Usage": buc_header(call_count=10, cputime=88)}
        )
        assert usage.worst_pct == 88

    def test_malformed_header_does_not_raise(self):
        """A broken header must never break ingestion."""
        usage = parse_usage({"X-Business-Use-Case-Usage": "not json at all"})
        assert usage.worst_pct == 0.0

    def test_missing_headers_yield_zero_usage(self):
        assert parse_usage({}).worst_pct == 0.0

    def test_no_pause_below_soft_limit(self):
        usage = parse_usage(
            {"X-Business-Use-Case-Usage": buc_header(call_count=SOFT_LIMIT_PCT - 1)}
        )
        assert usage.suggested_pause_seconds() == 0.0

    def test_pause_ramps_between_soft_and_hard_limits(self):
        low = parse_usage(
            {"X-Business-Use-Case-Usage": buc_header(call_count=80)}
        ).suggested_pause_seconds()
        high = parse_usage(
            {"X-Business-Use-Case-Usage": buc_header(call_count=HARD_LIMIT_PCT - 1)}
        ).suggested_pause_seconds()
        assert 0 < low < high

    def test_throttled_response_waits_full_regain_window(self):
        usage = parse_usage(
            {"X-Business-Use-Case-Usage": buc_header(call_count=100, regain=7)}
        )
        assert usage.is_throttled
        assert usage.suggested_pause_seconds() == 420.0


# --------------------------------------------------------------------- #
# Error classification
# --------------------------------------------------------------------- #


class TestErrorHandling:
    @responses.activate
    def test_expired_token_fails_fast_without_retrying(self):
        """Code 190 is terminal. Retrying an expired token wastes quota."""
        responses.add(
            responses.GET,
            f"{BASE}/act_123/insights",
            json={"error": {"code": 190, "message": "Session expired"}},
            status=400,
        )
        client = MetaHTTPClient(access_token="stale", max_retries=5)

        with pytest.raises(MetaAPIError) as exc:
            client.get("act_123/insights")

        assert exc.value.code == 190
        assert len(responses.calls) == 1, "must not retry a terminal error"

    @responses.activate
    def test_throttle_error_is_retried_then_succeeds(self):
        """Code 17 arrives as HTTP 400, not 429. The body is the real signal."""
        responses.add(
            responses.GET,
            f"{BASE}/act_123/insights",
            json={"error": {"code": 17, "message": "User request limit reached"}},
            status=400,
        )
        responses.add(
            responses.GET,
            f"{BASE}/act_123/insights",
            json={"data": [{"ad_id": "1"}]},
            status=200,
        )

        client = MetaHTTPClient(access_token="tok", max_retries=3)
        client._sleep_backoff = lambda attempt: None  # keep the test fast

        result = client.get("act_123/insights")
        assert result["data"][0]["ad_id"] == "1"
        assert len(responses.calls) == 2


# --------------------------------------------------------------------- #
# Async job lifecycle
# --------------------------------------------------------------------- #


class TestAsyncInsightsJob:
    @responses.activate
    def test_polls_until_complete_then_pages_results(self):
        responses.add(
            responses.POST,
            f"{BASE}/act_123/insights",
            json={"report_run_id": "999"},
            status=200,
        )
        # 100% complete but status still running -- must NOT be treated as done.
        responses.add(
            responses.GET,
            f"{BASE}/999",
            json={"async_status": "Job Running", "async_percent_completion": 100},
            status=200,
        )
        responses.add(
            responses.GET,
            f"{BASE}/999",
            json={"async_status": "Job Completed", "async_percent_completion": 100},
            status=200,
        )
        responses.add(
            responses.GET,
            f"{BASE}/999/insights",
            json={
                "data": [
                    {
                        "ad_id": "a1",
                        "campaign_id": "c1",
                        "account_id": "123",
                        "date_start": "2026-09-01",
                        "date_stop": "2026-09-01",
                        "spend": "125.50",
                        "impressions": "10000",
                        "clicks": "250",
                        "actions": [
                            {"action_type": "lead", "7d_click": "12", "1d_view": "3"}
                        ],
                    }
                ],
                "paging": {},
            },
            status=200,
        )

        client = MetaHTTPClient(access_token="tok")
        connector = MetaAdsInsightsConnector(
            client=client, ad_account_id="123", poll_interval=0
        )
        window = ExtractWindow(start=date(2026, 9, 1), end=date(2026, 9, 1))

        batches = list(connector.extract(window))
        assert len(batches) == 1

        row = batches[0][0]
        assert row["spend"] == 125.50
        assert row["impressions"] == 10000
        # Attribution windows land in separate columns and are never summed.
        assert row["leads_7d_click"] == 12.0
        assert row["leads_1d_view"] == 3.0

    @responses.activate
    def test_failed_job_raises(self):
        responses.add(
            responses.POST,
            f"{BASE}/act_123/insights",
            json={"report_run_id": "888"},
            status=200,
        )
        responses.add(
            responses.GET,
            f"{BASE}/888",
            json={"async_status": "Job Failed"},
            status=200,
        )

        client = MetaHTTPClient(access_token="tok")
        connector = MetaAdsInsightsConnector(
            client=client, ad_account_id="123", poll_interval=0
        )

        with pytest.raises(MetaAPIError, match="Job Failed"):
            list(connector.extract(ExtractWindow(date(2026, 9, 1), date(2026, 9, 1))))

    def test_ad_account_prefix_is_normalised(self):
        client = MetaHTTPClient(access_token="tok")
        assert MetaAdsInsightsConnector(client, "123").ad_account_id == "act_123"
        assert MetaAdsInsightsConnector(client, "act_123").ad_account_id == "act_123"


# --------------------------------------------------------------------- #
# Normalisation
# --------------------------------------------------------------------- #


class TestNormalisation:
    @pytest.fixture
    def connector(self):
        return MetaAdsInsightsConnector(MetaHTTPClient("tok"), "123")

    def test_untracked_action_types_are_ignored_but_raw_is_kept(self, connector):
        row = connector._normalise(
            {
                "ad_id": "a1",
                "account_id": "123",
                "date_start": "2026-09-01",
                "actions": [
                    {"action_type": "some_future_event", "7d_click": "5"},
                    {"action_type": "lead", "7d_click": "9"},
                ],
            }
        )
        assert row["leads_7d_click"] == 9.0
        assert "some_future_event" not in row
        # The raw payload is retained so nothing is lost.
        assert len(row["actions_raw"]) == 2

    def test_missing_numerics_default_to_zero_not_none(self, connector):
        """NULLs propagate through SUM() in surprising ways. Default to 0."""
        row = connector._normalise({"ad_id": "a1", "date_start": "2026-09-01"})
        assert row["spend"] == 0.0
        assert row["impressions"] == 0

    def test_window_rejects_inverted_range(self):
        with pytest.raises(ValueError, match="precedes start"):
            ExtractWindow(start=date(2026, 9, 10), end=date(2026, 9, 1))
