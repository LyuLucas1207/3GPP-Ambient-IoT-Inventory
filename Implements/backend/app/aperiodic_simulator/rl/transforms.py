"""Deterministic observation scaling and action transform shared by training and inference.

Observation (paper Eq. 5): x_s = [S1, S2a, S2b, I, C, L_prev, p_prev] of the
previous round. Scaling (invertible given L_prev, so no information is lost):

    counts / (L_prev * F)   for S1, S2a, S2b, I, C   (fractions of the AOs offered)
    L_prev / L_max
    p_prev                  (already in (0, 1])

C2 and every other hidden quantity are never part of the observation.

Action: the policy emits a in [-1, 1]^2 (SB3 clips Gaussian samples to the
Box). The paper fixes only the ranges M = [0.25, 10] and Q = [0.1, 10]; the
mapping is ours and is log-uniform so that shrinking and growing factors get
equal resolution:

    m = exp(ln 0.25 + (a0 + 1)/2 * (ln 10 - ln 0.25))
    q = exp(ln 0.1  + (a1 + 1)/2 * (ln 10 - ln 0.1))

The environment then applies paper Eqs. (6)-(7):

    L_s = max(1, min(ceil(m * L_prev), L_max))
    p_s = clip(q * p_prev, p_floor, 1)

(p_floor = 1e-4 is the numerical stand-in for the open bound p > 0).
"""

import math

import numpy as np

M_RANGE = (0.25, 10.0)
Q_RANGE = (0.1, 10.0)
OBS_DIM = 7

ACTION_TRANSFORM = {
    "policy_action_space": "Box([-1, -1], [1, 1])",
    "m": "exp(ln(0.25) + (a0 + 1) / 2 * (ln(10) - ln(0.25)))",
    "q": "exp(ln(0.1) + (a1 + 1) / 2 * (ln(10) - ln(0.1)))",
    "L": "max(1, min(ceil(m * L_prev), L_max))",
    "p": "clip(q * p_prev, p_floor, 1)",
    "m_range": list(M_RANGE),
    "q_range": list(Q_RANGE),
}
OBSERVATION_NORMALIZATION = {
    "vector": ["S1", "S2a", "S2b", "I", "C", "L_prev", "p_prev"],
    "counts": "divided by L_prev * F (fraction of offered AOs)",
    "L_prev": "divided by L_max",
    "p_prev": "unchanged",
    "excluded": ["C2", "backlog", "energies", "wake times", "availability"],
}


def _log_map(a: float, lo: float, hi: float) -> float:
    a = min(max(float(a), -1.0), 1.0)
    return math.exp(math.log(lo) + (a + 1.0) / 2.0 * (math.log(hi) - math.log(lo)))


def action_to_multipliers(action) -> tuple[float, float]:
    a = np.asarray(action, dtype=float).reshape(-1)
    return _log_map(a[0], *M_RANGE), _log_map(a[1], *Q_RANGE)


def apply_action(m: float, q: float, L_prev: int, p_prev: float, L_max: int, p_floor: float) -> tuple[int, float]:
    L = max(1, min(math.ceil(m * L_prev), L_max))
    p = min(max(q * p_prev, p_floor), 1.0)
    return int(L), float(p)


def normalize_observation(obs: dict, F: int, L_max: int) -> np.ndarray:
    n_ao = max(obs["L"] * F, 1)
    return np.array(
        [obs["S1"] / n_ao, obs["S2a"] / n_ao, obs["S2b"] / n_ao, obs["I"] / n_ao, obs["C"] / n_ao, obs["L"] / L_max, obs["p"]],
        dtype=np.float32,
    )
