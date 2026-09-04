"""HTTP client for the Meta Graph API.

Wraps ``requests`` with the three things every Meta connector needs and that
are tedious to get right: proactive rate-limit throttling, retry with
exponential backoff and jitter, and classification of Meta's error codes into
retryable vs terminal.
"""

from __future__ import annotations

import logging
import random
import time
from typing import Any

import requests

from .rate_limit import UsageSnapshot, parse_usage

logger = logging.getLogger(__name__)

# Meta returns HTTP 400 for throttling as often as 429, with the real signal in
# the JSON body's error.code. Treating these as retryable is the difference
# between a pipeline that survives a busy hour and one that pages you.
RETRYABLE_ERROR_CODES = {
    1,      # Unknown / transient
    2,      # Service temporarily unavailable
    4,      # Application request limit reached
    17,     # User request limit reached
    32,     # Page-level throttle
    341,    # Application limit reached
    613,    # Custom-level throttle
    80000,  # Ads Insights throttle (generic)
    80004,  # Ads Insights throttle (account level)
}

TERMINAL_ERROR_CODES = {
    100,  # Invalid parameter -- retrying will not help
    190,  # Access token expired or revoked
    200,  # Permission error
}


class MetaAPIError(RuntimeError):
    """Non-retryable API failure."""

    def __init__(self, message: str, code: int | None = None, subcode: int | None = None):
        super().__init__(message)
        self.code = code
        self.subcode = subcode


class RetryableAPIError(RuntimeError):
    """Transient failure -- safe to retry after backoff."""


class MetaHTTPClient:
    """A thin, rate-aware Graph API client.

    Parameters
    ----------
    access_token:
        A long-lived system-user token. Never a short-lived user token -- those
        expire mid-backfill and are the most common cause of 190s in production.
    api_version:
        Pinned deliberately. Meta deprecates versions on a schedule; pinning
        means an upstream deprecation shows up as a planned upgrade rather than
        a silent behaviour change.
    max_retries:
        Attempts per request, including the first.
    """

    BASE_URL = "https://graph.facebook.com"

    def __init__(
        self,
        access_token: str,
        api_version: str = "v21.0",
        max_retries: int = 5,
        timeout: int = 120,
        session: requests.Session | None = None,
    ) -> None:
        self._token = access_token
        self.api_version = api_version
        self.max_retries = max_retries
        self.timeout = timeout
        self._session = session or requests.Session()
        self.last_usage = UsageSnapshot()

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #

    def get(self, path: str, params: dict[str, Any] | None = None) -> dict:
        return self._request("GET", path, params=params)

    def post(self, path: str, params: dict[str, Any] | None = None) -> dict:
        return self._request("POST", path, params=params)

    def paginate(self, path: str, params: dict[str, Any] | None = None):
        """Yield every page of a cursor-paginated edge.

        Follows ``paging.next`` rather than reconstructing the URL, because
        Meta embeds opaque cursor state in it. Reconstructing the URL by hand
        is how you end up silently re-reading page one forever.
        """
        page = self.get(path, params=params)
        yield page

        while True:
            next_url = (page.get("paging") or {}).get("next")
            if not next_url:
                return
            page = self._request("GET", next_url, absolute=True)
            yield page

    # ------------------------------------------------------------------ #
    # Internals
    # ------------------------------------------------------------------ #

    def _url(self, path: str, absolute: bool) -> str:
        if absolute:
            return path
        return f"{self.BASE_URL}/{self.api_version}/{path.lstrip('/')}"

    def _respect_rate_limit(self) -> None:
        pause = self.last_usage.suggested_pause_seconds()
        if pause > 0:
            logger.info(
                "Throttling: quota at %.1f%%, pausing %.1fs",
                self.last_usage.worst_pct,
                pause,
            )
            time.sleep(pause)

    def _request(
        self,
        method: str,
        path: str,
        params: dict[str, Any] | None = None,
        absolute: bool = False,
    ) -> dict:
        url = self._url(path, absolute)
        payload = dict(params or {})
        # An absolute paging URL already carries the token as a query param.
        if not absolute:
            payload["access_token"] = self._token

        last_error: Exception | None = None

        for attempt in range(1, self.max_retries + 1):
            self._respect_rate_limit()

            try:
                response = self._session.request(
                    method, url, params=payload, timeout=self.timeout
                )
            except requests.RequestException as exc:
                last_error = RetryableAPIError(f"Transport failure: {exc}")
                self._sleep_backoff(attempt)
                continue

            self.last_usage = parse_usage(response.headers)

            if response.ok:
                return response.json()

            last_error = self._classify(response)
            if isinstance(last_error, MetaAPIError):
                raise last_error

            logger.warning(
                "Retryable error on attempt %d/%d: %s",
                attempt,
                self.max_retries,
                last_error,
            )
            self._sleep_backoff(attempt)

        raise MetaAPIError(
            f"Exhausted {self.max_retries} attempts for {url}: {last_error}"
        )

    def _classify(self, response: requests.Response) -> Exception:
        """Map a failed response onto a retryable or terminal error."""
        try:
            error = response.json().get("error", {})
        except ValueError:
            error = {}

        code = error.get("code")
        subcode = error.get("error_subcode")
        message = error.get("message", response.text[:300])

        if code in TERMINAL_ERROR_CODES:
            return MetaAPIError(message, code=code, subcode=subcode)
        if code in RETRYABLE_ERROR_CODES or response.status_code in (429, 500, 502, 503, 504):
            return RetryableAPIError(f"code={code} {message}")
        return MetaAPIError(message, code=code, subcode=subcode)

    def _sleep_backoff(self, attempt: int) -> None:
        """Exponential backoff with full jitter.

        Jitter matters when several ad accounts are ingesting in parallel:
        without it, they all back off in lockstep and retry simultaneously,
        reproducing the thundering herd that caused the throttle.
        """
        ceiling = min(2**attempt, 60)
        time.sleep(random.uniform(0, ceiling))
