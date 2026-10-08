"""PFSA with a Probability-of-Zero-Estimation (PZE) access-probability update.

Used by Figures 5/6 (fixed L, both protocols) and as the fixed-L PFSA
baselines of Figure 8 / Table V.

PZE (Kodialam & Nandagopal, "Fast and reliable estimation schemes in RFID
systems", MobiCom 2006, zero estimator): with n contenders that each transmit
with probability p in one of N = L*F equiprobable AOs, the expected fraction
of empty AOs is

    E[I]/N = (1 - p/N)^n      =>      n_hat = ln(I/N) / ln(1 - p/N).

n_hat estimates the backlog that heard the previous page. Removing the
identified devices gives the residual backlog n_res = n_hat - S, and the
throughput-optimal access probability for N AOs is

    p_next = min(1, N / n_res).

Degenerate cases:
    * I = N (all AOs idle): n_hat = 0 -> p_next = 1 (paper's fallback, avoids
      stalling).
    * I = 0 (no idle AO): ln(0) diverges; I is floored to
      ``Assumptions.pze_all_collided_idle_floor`` (= 1), the usual
      finite-sample correction.
    * n_res <= N: p_next = 1.
"""

import math

from app.aperiodic_simulator.controllers.base import Action, Controller


def pze_backlog_estimate(I: float, N: int, p: float, idle_floor: float = 1.0) -> float:
    if N <= 0:
        raise ValueError("N must be positive")
    if I >= N:
        return 0.0
    i_eff = max(float(I), idle_floor)
    q = p / N
    if q >= 1.0:  # N = 1 and p = 1: one AO; any activity -> unbounded, use floor ratio
        q = 1.0 - 1e-12
    return math.log(i_eff / N) / math.log(1.0 - q)


def pze_next_p(I: float, S: int, N: int, p: float, idle_floor: float = 1.0) -> tuple[float, float]:
    n_hat = pze_backlog_estimate(I, N, p, idle_floor)
    if I >= N:
        return 1.0, n_hat
    n_res = n_hat - S
    if n_res <= N:
        return 1.0, n_hat
    return N / n_res, n_hat


class PFSAPZEController(Controller):
    name = "pfsa_pze"
    adapts_L = False

    def __init__(self, F: int, L_max: int, p_floor: float, idle_floor: float = 1.0):
        super().__init__(F, L_max, p_floor)
        self.idle_floor = idle_floor
        self.L = 1
        self.p = 1.0

    def reset(self, L0: int, p0: float) -> Action:
        self.L, self.p = self.clip(L0, p0)
        return Action(self.L, self.p, {"n_hat": None})

    def update(self, obs: dict) -> Action:
        N = obs["L"] * self.F
        S = obs["S1"] + obs["S2a"] + obs["S2b"]
        p_next, n_hat = pze_next_p(obs["I"], S, N, obs["p"], self.idle_floor)
        _, self.p = self.clip(self.L, p_next)
        return Action(self.L, self.p, {"n_hat": n_hat})
