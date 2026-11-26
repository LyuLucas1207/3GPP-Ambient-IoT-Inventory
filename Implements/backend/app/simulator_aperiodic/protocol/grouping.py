"""Observed group populations for the new-paper periodic baseline (first catch)."""

import numpy as np


def group_populations(group: np.ndarray, n_groups: int) -> dict[str, float]:
    g = group[group >= 0]
    n = max(g.size, 1)
    return {f"group_{i + 1}": float((g == i).sum() / n) for i in range(n_groups)}


def group_counts(group: np.ndarray, n_groups: int) -> dict[str, int]:
    g = group[group >= 0]
    return {f"group_{i + 1}": int((g == i).sum()) for i in range(n_groups)}
