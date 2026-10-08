"""Loaders for the paper's reference data (validation only, never simulation input)."""

import csv
import json
from functools import lru_cache
from pathlib import Path

import numpy as np

BACKEND_DIR = Path(__file__).resolve().parents[3]
DATA_DIR = BACKEND_DIR / "data" / "aperiodic"


def results_dir() -> Path:
    """``Implements/results/aperiodic`` (separate from ``results/periodic``)."""
    d = BACKEND_DIR.parent / "results" / "aperiodic"
    d.mkdir(parents=True, exist_ok=True)
    return d


@lru_cache
def scalar_targets() -> dict:
    return json.loads((DATA_DIR / "scalar_targets.json").read_text())


def _rows(name: str) -> list[dict]:
    with open(DATA_DIR / name, newline="") as f:
        return list(csv.DictReader(f))


@lru_cache
def table4() -> list[dict]:
    out = []
    for r in _rows("table4_depletion.csv"):
        out.append(
            {
                "protocol": r["protocol"],
                "L": int(r["L"]),
                "N_g": int(r["N_g"]) if r["N_g"] else None,
                **{k: float(r[k]) for k in ("paging", "msg1", "EI", "msg2", "msg3", "total")},
            }
        )
    return out


@lru_cache
def table5() -> list[dict]:
    return [
        {"scenario": r["scenario"], "n_tot": int(r["n_tot"]), **{k: float(v) for k, v in r.items() if k not in ("scenario", "n_tot")}}
        for r in _rows("table5_identification_time.csv")
    ]


@lru_cache
def table6() -> list[dict]:
    return [{k: float(v) for k, v in r.items()} for r in _rows("table6_alpha.csv")]


PAPER_CAPTIONS = {
    "figure4": "Paper Fig. 4 — CDF of the received power P_in at the devices",
    "figure5": "Paper Fig. 5 — Inventoried ratio vs time, single-source (with / w/o mid-round depletion)",
    "figure6": "Paper Fig. 6 — Inventoried ratio vs time, multi-source",
    "figure7": "Paper Fig. 7 — Recurrent PPO vs DFSA-Schoute vs CMEBE (multi-source, L1 = 1)",
    "figure8": "Paper Fig. 8 — Average resource efficiency vs N_tot: RL vs PFSA (L = 1, 8, 32)",
}


def reference_curve(figure: str, name: str) -> tuple[np.ndarray, np.ndarray] | None:
    """Extracted paper curve (x, y); None if not available."""
    path = DATA_DIR / figure / f"{name}.csv"
    if not path.exists():
        return None
    d = np.loadtxt(path, delimiter=",", skiprows=1, ndmin=2)
    return d[:, 0], d[:, 1]


def curve_t_targets(x: np.ndarray, y: np.ndarray, targets=(50, 90, 95, 99)) -> dict[str, float | None]:
    ymono = np.maximum.accumulate(y)
    return {f"T{q}": (float(np.interp(q, ymono, x)) if ymono.max() >= q else None) for q in targets}
