"""Inventory simulation engines for the thesis simulator.

Phase 1 ships a deterministic mock engine (``mock_engine``); the real FSA-based
engine will be ported from ``Sources/.../grouping_logic.py`` under the same
``InventoryEngine`` protocol in a later phase.
"""

from __future__ import annotations

from app.thesis_simulator.inventory.engine_base import InventoryEngine
from app.thesis_simulator.inventory.mock_engine import MockInventoryEngine


def make_engine(scheme: str) -> InventoryEngine:
    if scheme not in {"periodic", "aperiodic"}:
        raise ValueError(f"unknown scheme: {scheme!r}")
    return MockInventoryEngine(scheme=scheme)


__all__ = ["InventoryEngine", "MockInventoryEngine", "make_engine"]
