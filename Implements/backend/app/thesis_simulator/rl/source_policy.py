"""How a thesis reader applies the original single-reader weights.

The zip was trained by Sources ``RL.py``. This module stays inside
``thesis_simulator`` so the three simulators do not import each other.
The multiplier bounds come from ``app.journal.tables``.
"""

from __future__ import annotations

import math

import numpy as np

from app.journal.tables import M_MAX, M_MIN, Q_MAX, Q_MIN

K_MAX_RL = 668  # resource cap in Sources constants.py, not Table III L_max
P_MIN = 0.001  # lowest access probability in Sources constants.py

SOURCE_OBSERVATION = "Sources RL.py raw counts (S2b, S2a, S1, empty, collisions, K_prev, p_prev)"
SOURCE_ACTION = {
    "policy_action_space": "Box([0.25, 0.1], [10, 10])",
    "m": "clip(a0, 0.25, 10)",
    "q": "clip(a1, 0.1, 10)",
    "K": "clip(round(m * K_prev), 2, 668)",
    "p": "clip(q * p_prev, 0.001, 1)",
    "m_range": [M_MIN, M_MAX],
    "q_range": [Q_MIN, Q_MAX],
}


def source_observation(s2b: float, s2a: float, s1: float, empty: float, collisions: float, k_prev: float, p_prev: float) -> np.ndarray:
    return np.array([s2b, s2a, s1, empty, collisions, k_prev, p_prev], dtype=np.float32)


def _on_grant(k: int, f_freq: int, f_r: int) -> int:
    """Keep Msg1 length when only ``f_r`` of ``f_freq`` subbands are granted."""
    if f_r >= f_freq:
        return k
    return max(1, math.ceil(k / f_freq)) * max(1, f_r)


def apply_source_action(action, k_prev: int, p_prev: float, f_r: int, f_freq: int) -> tuple[int, float, float, float]:
    """(K, p, m, q). ``K`` is then folded onto the subbands this reader was granted."""
    a = np.asarray(action, dtype=float).reshape(-1)
    m = float(np.clip(a[0], M_MIN, M_MAX))
    q = float(np.clip(a[1], Q_MIN, Q_MAX))
    k = int(np.clip(int(round(m * max(1, int(k_prev)))), 2, K_MAX_RL))
    k = _on_grant(k, int(f_freq), int(f_r))
    p = float(np.clip(q * float(p_prev), P_MIN, 1.0))
    if not math.isfinite(p):
        p = 1.0
    return int(k), p, m, q
