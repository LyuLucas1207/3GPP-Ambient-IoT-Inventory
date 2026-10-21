"""Common interface for inventory simulation engines."""

from __future__ import annotations

from typing import Protocol, TYPE_CHECKING

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

    from app.thesis_simulator.models import ThesisInventoryRun


class InventoryEngine(Protocol):
    scheme: str

    def run(self, session: "Session", run_row: "ThesisInventoryRun") -> None:
        """Execute one full inventory run.

        Mutates ``run_row`` (status/started_at/completed_at/duration_s) and
        writes ``ThesisRunRound``, ``ThesisDeviceEvent``, ``ThesisReaderEvent``,
        ``ThesisRunSummary`` rows. The caller commits.
        """
        ...
