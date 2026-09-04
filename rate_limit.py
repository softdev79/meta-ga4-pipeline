"""Meta Marketing API rate-limit handling.

Meta does not return a simple ``Retry-After``. It returns utilisation
percentages in response headers and expects the client to slow down *before*
hitting the wall. Once you are throttled, ``estimated_time_to_regain_access``
is measured in minutes, so reactive backoff is far more expensive than
proactive throttling.

Headers we care about:

``X-Business-Use-Case-Usage``
    JSON object keyed by business ID. Each value is a list of per-use-case
    objects with ``call_count``, ``total_cputime``, ``total_time`` (each 0-100
    as a percentage of the quota) and ``estimated_time_to_regain_access``
    (minutes, 0 when not throttled).

``X-Ad-Account-Usage``
    Ad-account-level quota, ``acc_id_util_pct`` as a percentage.

Reference: developers.facebook.com/docs/graph-api/overview/rate-limiting
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import Mapping

logger = logging.getLogger(__name__)

# Below this utilisation we run at full speed. Above it we start inserting
# sleeps proportional to how close we are to the limit. 75 is deliberately
# conservative: an insights job that trips the limit costs minutes, whereas a
# few seconds of self-imposed delay costs almost nothing.
SOFT_LIMIT_PCT = 75.0
HARD_LIMIT_PCT = 95.0


@dataclass(frozen=True)
class UsageSnapshot:
    """Point-in-time view of our quota consumption."""

    call_count_pct: float = 0.0
    cpu_time_pct: float = 0.0
    total_time_pct: float = 0.0
    ad_account_pct: float = 0.0
    regain_access_minutes: int = 0

    @property
    def worst_pct(self) -> float:
        """The binding constraint. Any one of these can throttle us."""
        return max(
            self.call_count_pct,
            self.cpu_time_pct,
            self.total_time_pct,
            self.ad_account_pct,
        )

    @property
    def is_throttled(self) -> bool:
        return self.regain_access_minutes > 0

    def suggested_pause_seconds(self) -> float:
        """How long to wait before the next call.

        Zero below the soft limit. Between soft and hard limits we ramp
        quadratically so the slowdown is gentle at 76% and aggressive at 94%.
        """
        if self.is_throttled:
            return self.regain_access_minutes * 60.0

        pct = self.worst_pct
        if pct < SOFT_LIMIT_PCT:
            return 0.0

        span = HARD_LIMIT_PCT - SOFT_LIMIT_PCT
        position = min((pct - SOFT_LIMIT_PCT) / span, 1.0)
        return round(60.0 * (position**2), 2)


def _first_use_case(payload: str) -> dict:
    """Extract the first use-case entry from a BUC usage header.

    The header is keyed by business ID and we only ever authenticate as one
    business, so taking the first key is safe. Returns an empty dict on any
    malformed input -- a broken header must never break ingestion.
    """
    try:
        parsed = json.loads(payload)
    except (json.JSONDecodeError, TypeError):
        logger.warning("Could not parse X-Business-Use-Case-Usage header")
        return {}

    if not isinstance(parsed, dict):
        return {}

    for entries in parsed.values():
        if isinstance(entries, list) and entries and isinstance(entries[0], dict):
            return entries[0]
    return {}


def parse_usage(headers: Mapping[str, str]) -> UsageSnapshot:
    """Build a :class:`UsageSnapshot` from response headers."""
    buc = _first_use_case(headers.get("X-Business-Use-Case-Usage", ""))

    ad_account_pct = 0.0
    raw_account = headers.get("X-Ad-Account-Usage")
    if raw_account:
        try:
            ad_account_pct = float(
                json.loads(raw_account).get("acc_id_util_pct", 0.0)
            )
        except (json.JSONDecodeError, TypeError, ValueError):
            logger.warning("Could not parse X-Ad-Account-Usage header")

    return UsageSnapshot(
        call_count_pct=float(buc.get("call_count", 0.0)),
        cpu_time_pct=float(buc.get("total_cputime", 0.0)),
        total_time_pct=float(buc.get("total_time", 0.0)),
        ad_account_pct=ad_account_pct,
        regain_access_minutes=int(buc.get("estimated_time_to_regain_access", 0)),
    )
