"""Device grouping assignment (paper § Device Grouping for Congestion Control).

The published text: a device that receives odd-numbered paging continues
monitoring odd-numbered paging (N_g = 2 example, Fig. 4). That is grouping
at first successful paging detection, with wake period N_g * T_pg.

The paper does *not* say that every device which hears the same first paging
must share one group. Dumping all t=0 ON devices into group 0 contradicts
Fig. 4's purpose (distribute devices across paging sets). Modes:

- even_id_mod: preconfigured g = device_id % N_g
- random_preconfigured: shuffled even split assigned before inventory
- first_paging_mod: g = first_paging_index % N_g (paper-literal, may unbalance)
- first_paging_spread: grouping happens at first detection; group is a
  per-device uniform draw in 0..N_g-1, *not* the paging index (default)
"""

from __future__ import annotations

import numpy as np


PRECONFIGURED = frozenset({"even_id_mod", "random_preconfigured"})
FIRST_PAGING = frozenset({"first_paging_mod", "first_paging_spread"})
ALL_MODES = tuple(sorted(PRECONFIGURED | FIRST_PAGING))


def preconfigured_groups(
    n: int,
    n_groups: int,
    mode: str,
    rng: np.random.Generator,
) -> np.ndarray:
    ng = max(1, int(n_groups))
    if mode == "even_id_mod":
        return (np.arange(n, dtype=np.int16) % ng).astype(np.int16)
    if mode == "random_preconfigured":
        g = np.array([i % ng for i in range(n)], dtype=np.int16)
        rng.shuffle(g)
        return g
    return np.full(n, -1, dtype=np.int16)


def assign_at_first_paging(
    newly: np.ndarray,
    paging_index: int,
    n_groups: int,
    mode: str,
    rng: np.random.Generator,
) -> np.ndarray:
    """Group ids for devices that just heard their first paging."""
    ng = max(1, int(n_groups))
    n_new = int(np.count_nonzero(newly)) if newly.dtype == np.bool_ else int(newly.size)
    if n_new <= 0:
        return np.array([], dtype=np.int16)
    if mode == "first_paging_mod":
        return np.full(n_new, np.int16(paging_index % ng))
    if mode == "first_paging_spread":
        return rng.integers(0, ng, size=n_new, dtype=np.int16)
    raise ValueError(f"not a first-paging mode: {mode}")


def group_populations(group: np.ndarray, n_groups: int) -> list[int]:
    g = group[group >= 0]
    if g.size == 0:
        return [0] * max(1, n_groups)
    counts = np.bincount(g.astype(int), minlength=max(1, n_groups))
    return [int(c) for c in counts[: max(1, n_groups)]]
