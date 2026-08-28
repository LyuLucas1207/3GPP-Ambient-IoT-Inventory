"""Occupancy-feedback access probability controller.

Reproduction assumption: the paper says the reader adjusts access
probability from previous AO occupancy / congestion, but does not give
the update equation.

Modes
-----
poisson_idle
    Idle-AO Poisson load estimate. Freeze p when actual Msg1 TX < n_AO/2
    (energy-limited guard — not in the paper).
poisson_idle_ungated
    Same estimator without the freeze.
occupancy_counts
    Default. Update from idle / singleton / collision AO counts (Schoute
    load estimate). Target ≈ 1 attempt per AO (slotted ALOHA). No T99
    fitting. Empty paging (n_eligible = 0) is not a load observation.
fixed
    p stays at p_init.
"""

from __future__ import annotations

import math


SCHOUTE_COLLISION = 2.39  # standard RFID collision-slot occupancy estimate


class AccessProbabilityController:
    def __init__(
        self,
        n_ao: int,
        n_devices: int,
        p_init: float | None = None,
        p_min: float = 0.002,
        smoothing: float = 0.45,
        target_attempts_per_ao: float = 1.0,
        mode: str = "occupancy_counts",
    ) -> None:
        self.n_ao = int(n_ao)
        self.p_min = float(p_min)
        self.smoothing = float(smoothing)
        self.target = float(target_attempts_per_ao)
        self.mode = str(mode)
        if p_init is None:
            p_init = min(1.0, self.n_ao / max(n_devices, 1) * 1.2)
        self.p = float(min(1.0, max(self.p_min, p_init)))
        self.history: list[float] = [self.p]

    def observe(
        self,
        idle_count: int,
        n_eligible: int | None = None,
        n_transmitted: int | None = None,
        singleton_ao_count: int | None = None,
        collision_ao_count: int | None = None,
    ) -> float:
        if self.mode == "fixed":
            return self.p
        if n_eligible is not None and int(n_eligible) <= 0:
            return self.p

        if self.mode in ("poisson_idle", "poisson_idle_ungated"):
            self.p = self._poisson_idle(idle_count, n_transmitted)
        elif self.mode == "occupancy_counts":
            self.p = self._occupancy_counts(
                idle_count, singleton_ao_count, collision_ao_count
            )
        else:
            raise ValueError(f"Unknown access_controller '{self.mode}'")
        self.history.append(self.p)
        return self.p

    def _blend(self, raw: float) -> float:
        raw = min(1.0, max(self.p_min, raw))
        p = (1.0 - self.smoothing) * self.p + self.smoothing * raw
        return min(1.0, max(self.p_min, p))

    def _poisson_idle(self, idle_count: int, n_transmitted: int | None) -> float:
        gated = self.mode != "poisson_idle_ungated"
        if gated and n_transmitted is not None and int(n_transmitted) < 0.5 * self.n_ao:
            return self.p
        m = self.n_ao
        i = int(idle_count)
        if i >= m:
            raw = min(1.0, self.p * 1.8)
        elif i <= 0:
            lam = -math.log(max(0.5 / m, 1e-12))
            a_hat = m * lam
            raw = self.p * (m * self.target) / max(a_hat, 1e-9)
        else:
            lam = -math.log(i / m)
            a_hat = m * lam
            raw = self.p * (m * self.target) / max(a_hat, 1e-9)
        return self._blend(raw)

    def _occupancy_counts(
        self,
        idle_count: int,
        singleton_ao_count: int | None,
        collision_ao_count: int | None,
    ) -> float:
        """Schoute n̂ = S + 2.39 C from AO occupancy; target λ = 1 per AO."""
        m = self.n_ao
        s = 0 if singleton_ao_count is None else int(singleton_ao_count)
        c = 0 if collision_ao_count is None else int(collision_ao_count)
        i = int(idle_count)
        n_hat = s + SCHOUTE_COLLISION * c
        if n_hat < 0.5:
            # All idle (or unresolved): offered load too low.
            raw = min(1.0, self.p * 1.8)
        else:
            raw = self.p * (m * self.target) / max(n_hat, 1e-9)
        # Extra collision pressure when C dominates (congestion).
        if c >= max(1, m // 2) and i == 0:
            raw = min(raw, self.p * 0.7)
        return self._blend(raw)
