#!/usr/bin/env python3
"""Scientific validation of the Device-1 Figure 5(b) comparison.

    python scripts/validate_fig5b.py           # one paper-scale seed
    python scripts/validate_fig5b.py --quick   # small-N CI
    python scripts/validate_fig5b.py --monte-carlo 20
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from simulator.config import paper_device1_config, results_dir
from simulator.fig5b_validation import evaluate_fig5b
from simulator.simulation import run_paper_comparison


def _mean_ci(xs: np.ndarray) -> dict:
    xs = xs[np.isfinite(xs)]
    if xs.size == 0:
        return {"n": 0, "mean": None, "std": None, "ci95": [None, None]}
    m = float(np.mean(xs))
    s = float(np.std(xs, ddof=1)) if xs.size > 1 else 0.0
    half = 1.96 * s / np.sqrt(xs.size) if xs.size > 1 else 0.0
    return {"n": int(xs.size), "mean": m, "std": s, "ci95": [m - half, m + half]}


def run_one(cfg) -> dict:
    bundle = run_paper_comparison(cfg)
    val = evaluate_fig5b(bundle["results"], bundle["scenario"].pin_dbm)
    row = {
        "seed": cfg.seed,
        "pass": val["pass"],
        "t99_s": val["t99_s"],
        "reduction_4_vs_em": val["reduction_4_vs_em"],
        "curve_error": val["curve_error"],
        "t50_s": {k: bundle["results"][k].metrics.get("t50_s") for k in bundle["results"]},
        "t90_s": {k: bundle["results"][k].metrics.get("t90_s") for k in bundle["results"]},
        "t95_s": {k: bundle["results"][k].metrics.get("t95_s") for k in bundle["results"]},
    }
    return row, val, bundle


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--quick", action="store_true")
    p.add_argument("--monte-carlo", type=int, default=0, help="number of seeds (paper-scale unless --quick)")
    p.add_argument("--seed", type=int, default=42)
    args = p.parse_args()
    if args.quick:
        n, tmax = 80, 8.0
    else:
        n, tmax = 600, 25.0
    n_mc = args.monte_carlo if args.monte_carlo > 0 else 1
    seeds = [args.seed + i for i in range(n_mc)]
    rows = []
    last_val = None
    for seed in seeds:
        cfg = paper_device1_config(
            num_devices=n,
            max_time_s=tmax,
            seed=seed,
            collect_snapshots=False,
            collect_paging_events=False,
        )
        row, val, _ = run_one(cfg)
        last_val = val
        rows.append(row)
        print(
            f"seed={seed} {val['status']}  "
            f"EM T99={val['t99_s']['em']}  1g={val['t99_s']['dcm_1_group']}  "
            f"4g={val['t99_s']['dcm_4_group']}  red={val['reduction_4_vs_em']}"
        )

    t99 = {k: np.array([r["t99_s"][k] if r["t99_s"][k] is not None else np.nan for r in rows], dtype=float)
           for k in ("em", "dcm_1_group", "dcm_4_group")}
    red = np.array([np.nan if r["reduction_4_vs_em"] is None else r["reduction_4_vs_em"] for r in rows])
    n_pass = sum(1 for r in rows if r["pass"])
    mae_means = []
    for r in rows:
        errs = r.get("curve_error") or {}
        if errs:
            mae_means.append(float(np.mean([v["mae"] for v in errs.values()])))
    summary = {
        "num_devices": n,
        "max_time_s": tmax,
        "n_seeds": n_mc,
        "seeds": seeds,
        "n_pass": n_pass,
        "pass_fraction": n_pass / max(n_mc, 1),
        "t50_em": _mean_ci(np.array([r["t50_s"]["em"] or np.nan for r in rows], dtype=float)),
        "t90_em": _mean_ci(np.array([r["t90_s"]["em"] or np.nan for r in rows], dtype=float)),
        "t99": {k: _mean_ci(v) for k, v in t99.items()},
        "reduction_4_vs_em": _mean_ci(red),
        "reference_mae_mean": None if not mae_means else {
            "mean": float(np.mean(mae_means)),
            "min": float(np.min(mae_means)),
            "max": float(np.max(mae_means)),
        },
        "last_validation": last_val,
        "runs": rows if n_mc <= 5 else "omitted (see JSON keys t99 / reduction)",
    }
    dest = results_dir()
    dest.mkdir(parents=True, exist_ok=True)
    path = dest / ("fig5b_validation_quick.json" if args.quick else "fig5b_validation.json")
    path.write_text(json.dumps(summary, indent=2, default=str))
    print(f"\n{n_pass}/{n_mc} seeds PASS")
    print(json.dumps({k: summary[k] for k in ("t99", "reduction_4_vs_em", "pass_fraction")}, indent=2))
    print(f"Saved {path}")
    return 0 if (n_pass == n_mc or (n_mc >= 5 and n_pass / n_mc >= 0.7)) else 1


if __name__ == "__main__":
    raise SystemExit(main())
