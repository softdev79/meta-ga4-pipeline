"""The ingestion contract.

Every source implements this interface, which is what lets the orchestration
layer stay source-agnostic: adding Google Ads or LinkedIn Ads later means
writing one class, not a new pipeline.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import date
from typing import Any, Iterator


@dataclass(frozen=True)
class ExtractWindow:
    """The date range to pull, plus why.

    ``is_restatement`` distinguishes a routine incremental pull from a
    deliberate re-read of already-loaded days. Meta revises attributed
    conversions for up to 28 days after the fact, so yesterday's numbers are
    not final -- ingestion has to be an upsert, never an append.
    """

    start: date
    end: date
    is_restatement: bool = False

    def __post_init__(self) -> None:
        if self.end < self.start:
            raise ValueError(f"end ({self.end}) precedes start ({self.start})")


@dataclass
class ExtractResult:
    """What a connector hands back to the loader."""

    rows: list[dict[str, Any]]
    source: str
    window: ExtractWindow
    merge_keys: list[str] = field(default_factory=list)

    @property
    def row_count(self) -> int:
        return len(self.rows)


class Connector(ABC):
    """Base class for all source connectors."""

    #: Short identifier used in table names, logs and config.
    source_name: str

    #: Natural key for the MERGE. Rows sharing these values are the same fact.
    merge_keys: list[str]

    @abstractmethod
    def extract(self, window: ExtractWindow) -> Iterator[list[dict[str, Any]]]:
        """Yield batches of normalised rows for the given window.

        Yields batches rather than returning one list so that a multi-month
        backfill does not have to fit in memory.
        """

    @abstractmethod
    def schema(self) -> list[dict[str, str]]:
        """Return the BigQuery schema for this source's staging table."""
