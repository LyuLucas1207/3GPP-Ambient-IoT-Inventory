"""D1T1 indoor-factory layout: 120 m x 60 m, 18 BSs on a square lattice.

TR 38.769 Table 4.2.2-2 / TR 38.901 InF: BSs at x = 10, 30, ..., 110 m and
y = 10, 30, 50 m (20 m spacing). One of the two central BSs, (50, 30) or
(70, 30), acts as reader; the default is (50, 30).
"""

import numpy as np

from app.aperiodic_simulator.core.config import Assumptions, SystemParams


def bs_positions(system: SystemParams | None = None) -> np.ndarray:
    s = system or SystemParams()
    half = s.bs_spacing_m / 2.0
    xs = np.arange(half, s.factory_length_m, s.bs_spacing_m)
    ys = np.arange(half, s.factory_width_m, s.bs_spacing_m)
    grid = np.array([(x, y) for y in ys for x in xs], dtype=np.float64)
    if grid.shape[0] != s.n_bs:
        raise ValueError(f"layout produced {grid.shape[0]} BSs, expected {s.n_bs}")
    return grid


def central_bs_indices(system: SystemParams | None = None) -> tuple[int, int]:
    s = system or SystemParams()
    pos = bs_positions(s)
    center = np.array([s.factory_length_m / 2.0, s.factory_width_m / 2.0])
    d = np.linalg.norm(pos - center, axis=1)
    order = np.argsort(d, kind="stable")
    return int(order[0]), int(order[1])


def reader_position(system: SystemParams | None = None, assumptions: Assumptions | None = None) -> np.ndarray:
    s = system or SystemParams()
    a = assumptions or Assumptions()
    idx = a.reader_bs_index
    if idx not in central_bs_indices(s):
        raise ValueError("reader must be one of the two central BSs")
    return bs_positions(s)[idx]


def sample_device_positions(n: int, rng: np.random.Generator, system: SystemParams | None = None) -> np.ndarray:
    s = system or SystemParams()
    x = rng.uniform(0.0, s.factory_length_m, size=n)
    y = rng.uniform(0.0, s.factory_width_m, size=n)
    return np.column_stack([x, y])
