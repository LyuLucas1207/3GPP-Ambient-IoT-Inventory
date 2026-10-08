"""CMEBE: capture-aware minimum-error backlog estimation (Figure 7 baseline).

B. Li and J. Wang, "Efficient anti-collision algorithm utilizing the capture
effect for ISO 18000-6C RFID protocol", IEEE Commun. Lett. 15(3), 2011.

Li & Wang extend Vogt's minimum-error estimator to readers with capture. For
a frame of N slots, n contenders and probability alpha that a collided slot
is captured (decoded as a success), the expected slot counts are

    E[e](n)        = N (1 - 1/N)^n
    A(n)           = n (1 - 1/N)^(n-1)                 (singleton slots)
    B(n)           = N - E[e](n) - A(n)                (physically collided)
    E[s](n, a)     = A(n) + a B(n)
    E[c](n, a)     = (1 - a) B(n)

and (n_hat, alpha_hat) minimise the distance to the observed (e, s, c):

    eps(n, a) = (E[e]-e)^2 + (E[s]-s)^2 + (E[c]-c)^2,   n >= s + 2c.

For fixed n, eps is quadratic in a with minimiser
    a*(n) = (s - A + B - c) / (2B), clipped to [0, 1],
so the search is a 1-D scan over integer n.

Frame length with capture: for load x = n/N the expected decoded slots per
slot are x e^-x + a (1 - e^-x - x e^-x); d/dx = e^-x (1 - x + a x) = 0 gives
x* = 1 / (1 - a), i.e. the optimal frame length is N* = (1 - a) * backlog,
which is Li & Wang's capture-aware frame rule. The backlog after the frame is
n_hat minus the identified devices S of the round.

Mapping to the A-IoT round (paper Sec. V-C): slot = AO, N = L*F, observed
e = I, s = decoded (= N - I - C), c = C; L = ceil(N* / F) clipped to
[1, L_max]; p = 1 (DFSA does not control the access probability).

Search bound: n is scanned up to s + 2c + 4 * L_max * F. When every AO
collides the error decreases monotonically in n; any estimate beyond the
bound already yields L = L_max, so the bound only affects the reported
n_hat, never the action.
"""

import math

import numpy as np

from app.aperiodic_simulator.controllers.base import Action, Controller


def cmebe_estimate(e: float, s: float, c: float, N: int, n_upper: int) -> tuple[float, float]:
    """Return (n_hat, alpha_hat) for one observed frame."""
    if N <= 0:
        raise ValueError("N must be positive")
    n_lo = int(s + 2 * c)
    if c == 0:
        # No collision observed: every contender is accounted for by s.
        return float(s), 0.0
    n = np.arange(max(n_lo, 2), max(n_upper, n_lo + 1) + 1, dtype=float)
    q = 1.0 - 1.0 / N
    Ee = N * q**n
    A = n * q ** (n - 1)
    B = np.maximum(N - Ee - A, 1e-12)
    a = np.clip((s - A + B - c) / (2.0 * B), 0.0, 1.0)
    err = (Ee - e) ** 2 + (A + a * B - s) ** 2 + ((1.0 - a) * B - c) ** 2
    k = int(np.argmin(err))
    return float(n[k]), float(a[k])


class CMEBEController(Controller):
    name = "cmebe"
    adapts_L = True
    adapts_p = False

    def __init__(self, F: int, L_max: int, p_floor: float):
        super().__init__(F, L_max, p_floor)
        self.L = 1

    def reset(self, L0: int, p0: float) -> Action:
        self.L, _ = self.clip(L0, 1.0)
        return Action(self.L, 1.0, {"n_hat": None, "backlog_hat": None, "alpha_hat": None})

    def update(self, obs: dict) -> Action:
        N = obs["L"] * self.F
        S = obs["S1"] + obs["S2a"] + obs["S2b"]
        n_hat, alpha = cmebe_estimate(obs["I"], obs["decoded"], obs["C"], N, int(obs["decoded"] + 2 * obs["C"] + 4 * self.L_max * self.F))
        backlog = max(n_hat - S, 0.0)
        self.L, _ = self.clip(math.ceil((1.0 - alpha) * backlog / self.F), 1.0)
        return Action(self.L, 1.0, {"n_hat": n_hat, "backlog_hat": backlog, "alpha_hat": alpha})
