"""Occupancy-feedback access probability controller.

Reproduction assumption: the paper says the reader adjusts access
probability from previous AO occupancy / congestion, but does not give
the update equation. Isolated here so it can be replaced.

Poisson idle-AO load estimate:

    I / M ≈ exp(-λ)  ⇒  λ̂ = -ln(I / M)
    Â = M λ̂
    p ← clip(p * (M / Â) * target, p_min, 1)
"""

import math


class AccessProbabilityController:
    def __init__(
        self,
        n_ao: int,
        n_devices: int,
        p_init: float | None = None,
        p_min: float = 0.002,
        smoothing: float = 0.45,
        target_attempts_per_ao: float = 1.0,
        mode: str = "poisson_idle",
    ) -> None:
        self.n_ao = int(n_ao)
        self.p_min = float(p_min)
        self.smoothing = float(smoothing)
        self.target = float(target_attempts_per_ao)
        self.mode = str(mode)
        if p_init is None:
            p_init = min(1.0, self.n_ao / max(n_devices, 1) * 1.2)
        self.p = float(min(1.0, max(self.p_min, p_init)))

    def observe(
        self,
        idle_count: int,
        n_eligible: int | None = None,
        n_transmitted: int | None = None,
    ) -> float:
        if self.mode == "fixed":
            return self.p
        # No listeners: occupancy is not a load observation — leave p unchanged.
        if n_eligible is not None and int(n_eligible) <= 0:
            return self.p
        gated = self.mode != "poisson_idle_ungated"
        # Energy-limited paging: few actual Msg1 transmissions. Idle AOs then
        # mean devices are harvesting, not that p is too small for the group.
        if gated and n_transmitted is not None and int(n_transmitted) < 0.5 * self.n_ao:
            return self.p
        m = self.n_ao
        i = int(idle_count)
        if i >= m:
            # No attempts observed: offered load too low.
            raw = min(1.0, self.p * 1.8)
        elif i <= 0:
            # Fully occupied: treat as high load without taking ln(0).
            lam = -math.log(max(0.5 / m, 1e-12))
            a_hat = m * lam
            raw = self.p * (m * self.target) / max(a_hat, 1e-9)
        else:
            lam = -math.log(i / m)
            a_hat = m * lam
            raw = self.p * (m * self.target) / max(a_hat, 1e-9)
        raw = min(1.0, max(self.p_min, raw))
        self.p = (1.0 - self.smoothing) * self.p + self.smoothing * raw
        self.p = min(1.0, max(self.p_min, self.p))
        return self.p
