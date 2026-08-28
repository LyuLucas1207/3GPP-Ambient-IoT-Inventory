#!/usr/bin/env python3
"""Compare unpublished grouping / init / access-controller / DCM-ON assumptions.

    python scripts/compare_assumptions.py --quick
    python scripts/compare_assumptions.py --paper --which grouping
    python scripts/compare_assumptions.py --paper --which dcm_on
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import replace
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from simulator.config import paper_device1_config, results_dir
from simulator.scenario import Scenario
from simulator.simulation import run_strategy

GROUP_MODES = ("even_id_mod", "first_paging_mod", "first_paging_spread", "random_preconfigured")
WARMUPS = (
    ("stationary", 60.0),
    ("explicit", 20.0),
    ("explicit", 60.0),
    ("harvest_only", 20.0),
    ("harvest_only", 60.0),
)
CONTROLLERS = ("occupancy_counts", "poisson_idle", "poisson_idle_ungated", "fixed")
FIXED_P = (0.02, 0.05, 0.10, 0.25, 1.0)
STRATS = ("em", "dcm_1_group", "dcm_4_group")


def _metrics(res) -> dict:
    m = res.metrics
    return {
        "t50_s": m.get("t50_s"),
        "t90_s": m.get("t90_s"),
        "t95_s": m.get("t95_s"),
        "t99_s": m.get("t99_s"),
        "collision_rate": m.get("collision_rate"),
        "n_msg1_attempts": m.get("n_msg1_attempts"),
        "group_population": m.get("group_population"),
        "idle_ao_frac_mean": m.get("idle_ao_frac_mean"),
        "attempts_per_ao_mean": m.get("attempts_per_ao_mean"),
    }


def run_matrix(base, scenario, which: str) -> dict:
    out: dict = {"which": which, "rows": []}
    if which in ("grouping", "all"):
        for mode in GROUP_MODES:
            cfg = replace(base, assumptions=replace(base.assumptions, group_assignment=mode))
            row = {"group_assignment": mode, "strategies": {}}
            for s in STRATS:
                res = run_strategy(cfg, scenario, s)
                row["strategies"][s] = _metrics(res)
                print(f"group={mode:22s} {s:14s} T99={res.metrics.get('t99_s')} pop={res.metrics.get('group_population')}")
            out["rows"].append(row)
    if which in ("init", "all"):
        for mode, dur in WARMUPS:
            cfg = replace(
                base,
                assumptions=replace(base.assumptions, warmup_mode=mode, warmup_s=dur),
            )
            row = {"warmup_mode": mode, "warmup_s": dur, "strategies": {}}
            for s in STRATS:
                res = run_strategy(cfg, scenario, s)
                row["strategies"][s] = _metrics(res)
                print(f"init={mode:13s} {dur:5.0f}s {s:14s} T99={res.metrics.get('t99_s')}")
            out["rows"].append(row)
    if which in ("access", "all"):
        for mode in CONTROLLERS:
            cfg = replace(base, assumptions=replace(base.assumptions, access_controller=mode))
            row = {"access_controller": mode, "strategies": {}}
            for s in STRATS:
                res = run_strategy(cfg, scenario, s)
                hist = res.p_access_history
                row["strategies"][s] = {
                    **_metrics(res),
                    "p_access_first": None if not hist else hist[0][1],
                    "p_access_last": None if not hist else hist[-1][1],
                    "p_access_n": len(hist),
                }
                print(f"ctrl={mode:22s} {s:14s} T99={res.metrics.get('t99_s')} coll={res.metrics.get('collision_rate')}")
            out["rows"].append(row)
        for pfix in FIXED_P:
            cfg = replace(
                base,
                assumptions=replace(
                    base.assumptions, access_controller="fixed", p_access_init=pfix, p_access_min=pfix
                ),
            )
            row = {"access_controller": "fixed", "p_fixed": pfix, "strategies": {}}
            for s in STRATS:
                res = run_strategy(cfg, scenario, s)
                row["strategies"][s] = _metrics(res)
                print(f"fixed p={pfix:.2f} {s:14s} T99={res.metrics.get('t99_s')}")
            out["rows"].append(row)
    if which in ("dcm_on", "all"):
        for early in (False, True):
            label = (
                "experimental_early_sleep"
                if early
                else "strict_paper_fixed_ton_dcm"
            )
            cfg = replace(
                base,
                assumptions=replace(base.assumptions, sleep_when_not_attempting=early),
            )
            row = {
                "sleep_when_not_attempting": early,
                "dcm_on_mode": label,
                "strategies": {},
            }
            for s in STRATS:
                res = run_strategy(cfg, scenario, s)
                row["strategies"][s] = _metrics(res)
                print(f"dcm_on={label:34s} {s:14s} T99={res.metrics.get('t99_s')}")
            out["rows"].append(row)
    return out


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--paper", action="store_true")
    p.add_argument("--quick", action="store_true")
    p.add_argument("--which", choices=("grouping", "init", "access", "dcm_on", "all"), default="all")
    args = p.parse_args()
    if args.paper:
        n, tmax = 600, 25.0
    else:
        n, tmax = 80, 6.0
    base = paper_device1_config(
        num_devices=n, max_time_s=tmax, seed=42,
        collect_snapshots=False, collect_paging_events=True,
    )
    scenario = Scenario.generate(base)
    out = run_matrix(base, scenario, args.which)
    dest = results_dir() / f"assumption_compare_{args.which}.json"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(out, indent=2))
    print(f"Saved {dest}")


if __name__ == "__main__":
    main()
