"""Helpers shared by the thesis sweep scripts (scenes, parallel map, CSV)."""

from __future__ import annotations

import csv
import math
import os
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
from typing import Any, Callable, Iterable

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import numpy as np  # noqa: E402

from app.simulator_thesis.inventory.headless import HeadlessResult, synthetic_scene  # noqa: E402
from app.simulator_thesis.scenario import DEFAULT_ACTIVE_BS_XY, default_bs_positions  # noqa: E402


def active_subset(k: int) -> list[tuple[float, float]]:
    """``k`` lattice readers, spread by farthest-point sampling from the TR's
    default active reader; ``k = 2`` gives two readers >= 60 m apart (D1T1-A2)."""
    lattice = default_bs_positions()
    k = max(1, min(k, len(lattice)))
    chosen = [min(lattice, key=lambda p: math.dist(p, DEFAULT_ACTIVE_BS_XY))]
    while len(chosen) < k:
        rest = [p for p in lattice if p not in chosen]
        chosen.append(max(rest, key=lambda p: (min(math.dist(p, c) for c in chosen), -p[1], -p[0])))
    return chosen


def scene(n_devices: int, readers: int | list[tuple[float, float]], seed: int, mix: tuple[float, float, float] | None = None) -> dict[str, Any]:
    xy = active_subset(readers) if isinstance(readers, int) else readers
    kw = {"subtype_mix": mix} if mix else {}
    return synthetic_scene(n_devices, reader_xy=xy, seed=seed, **kw)


def times(res: HeadlessResult) -> dict[str, float | None]:
    t = res.identification_times()
    return {
        "t50": res.t_quantile(0.5),
        "t90": res.t_quantile(0.9),
        "t99": res.t_quantile(0.99),
        "t_mean": float(t.mean()) if t.size else None,
        "t_last": float(t[-1]) if t.size else None,
    }


def pmap(fn: Callable[[Any], Any], jobs: Iterable[Any], workers: int | None, progress: bool = True) -> list[Any]:
    jobs = list(jobs)
    workers = workers or max(1, (os.cpu_count() or 2) - 1)
    out: list[Any] = []
    if workers <= 1:
        for i, j in enumerate(jobs, 1):
            out.append(fn(j))
            if progress:
                print(f"  {i}/{len(jobs)}", flush=True)
        return out
    with ProcessPoolExecutor(max_workers=workers) as ex:
        for i, r in enumerate(ex.map(fn, jobs), 1):
            out.append(r)
            if progress and (i % max(1, len(jobs) // 20) == 0 or i == len(jobs)):
                print(f"  {i}/{len(jobs)}", flush=True)
    return out


def write_csv(rows: list[dict[str, Any]], path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    keys: list[str] = []
    for r in rows:
        for k in r:
            if k not in keys:
                keys.append(k)
    with path.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=keys)
        w.writeheader()
        w.writerows(rows)
    return path


def mean_or_none(values: Iterable[float | None]) -> float | None:
    v = [x for x in values if x is not None and np.isfinite(x)]
    return float(np.mean(v)) if v else None
