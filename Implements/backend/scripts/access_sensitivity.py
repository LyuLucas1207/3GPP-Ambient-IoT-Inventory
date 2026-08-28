#!/usr/bin/env python3
"""Access-controller sensitivity (unpublished). Default is poisson_idle.

Quick mode uses a small N so it can run in CI-like checks. Paper-scale:

    python scripts/access_sensitivity.py --paper
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

MODES = ("poisson_idle", "poisson_idle_ungated", "fixed")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--paper", action="store_true", help="N=600, 25 s (slow)")
    args = p.parse_args()
    if args.paper:
        n, tmax, seed = 600, 25.0, 42
    else:
        n, tmax, seed = 80, 3.0, 42
    base = paper_device1_config(
        num_devices=n,
        max_time_s=tmax,
        seed=seed,
        collect_snapshots=False,
        collect_paging_events=False,
    )
    scenario = Scenario.generate(base)
    out = {"seed": seed, "num_devices": n, "max_time_s": tmax, "modes": {}}
    for mode in MODES:
        cfg = replace(base, assumptions=replace(base.assumptions, access_controller=mode))
        row = {}
        for strat in base.strategies:
            res = run_strategy(cfg, scenario, strat)
            row[strat] = {
                "t90_s": res.metrics["t90_s"],
                "t99_s": res.metrics["t99_s"],
                "collision_rate": res.metrics["collision_rate"],
                "n_msg1_attempts": res.metrics["n_msg1_attempts"],
                "n_heard_no_attempt": res.metrics["n_heard_no_attempt"],
            }
            print(
                f"{mode:24s} {strat:14s} T90={res.metrics['t90_s']} "
                f"T99={res.metrics['t99_s']} coll={res.metrics['collision_rate']:.3f}"
            )
        out["modes"][mode] = row
    dest = results_dir() / "access_sensitivity.json"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(out, indent=2))
    print(f"Saved {dest}")


if __name__ == "__main__":
    main()
