"""Backlog estimator per DCM group (last-wins port of
``Sources/.../estimators.py``).

Uses the empty-slot inversion from the final overriding definition of
``_estimate_n_from_frame_schoute_or_empty`` in the reference file; falls back
to Schoute's rule when there were no empty slots. One instance per reader.
"""

from __future__ import annotations

import math

from app.thesis_simulator.inventory.config import CONSTANTS, EngineConstants


class BacklogEstimator:
    def __init__(self, groups: int, consts: EngineConstants = CONSTANTS) -> None:
        if groups < 1:
            raise ValueError("groups must be >= 1")
        self._consts = consts
        self.mnot_next: list[int | None] = [None] * groups

    def p_star(self, k: int, group: int) -> float:
        est = self.mnot_next[group]
        if est is None or est <= 0:
            return self._consts.p0_init
        return min(1.0, k / float(est))

    def update(self, group: int, k: int, s: int, c: int, e: int, p_used: float) -> float | None:
        """Update the group's backlog estimate; return the population estimate n_hat."""
        c_total = s + c + e
        if c_total <= 0:
            return None
        p = max(self._consts.p_min, float(p_used))
        if e > 0:
            # Empty-slot inversion: n_hat = -(L/p) * log(E/L)
            l = max(1, k)
            ratio = min(1.0 - 1e-18, max(1e-18, float(e) / float(l)))
            n_hat = -(float(l) / p) * math.log(ratio)
        elif c > 0:
            n_hat = (float(s) + self._consts.schoute_const * float(c)) / p
        else:
            n_hat = float(s) / p
        if not math.isfinite(n_hat):
            n_hat = float(s)
        self.mnot_next[group] = max(0, int(round(n_hat - s)))
        return float(n_hat)
