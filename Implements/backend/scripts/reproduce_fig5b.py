#!/usr/bin/env python3
"""Reproduce published Figure 5(b) for Device 1. Independent of FastAPI / React."""

import csv
import json
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from simulator.config import paper_device1_config, results_dir, strategy_label
from simulator.scenario import Scenario
from simulator.simulation import run_paper_comparison


def _fmt(value):
    if value is None:
        return "not reached"
    return f"{value:.3f} s  ({value * 1e3:.1f} ms)"


def main():
    cfg = paper_device1_config(
        collect_snapshots=False,
        collect_paging_events=False,
    )
    print("Running Device-1 Figure 5(b) reproduction...")
    print(f"N: {cfg.num_devices}")
    print(f"Seed: {cfg.seed}")
    print(f"dt: {cfg.dt_s * 1e3:.1f} ms")
    print("Loading Fig. 5(a) p_in distribution...")
    print("Generating 600 Device-1 tags...")

    bundle = run_paper_comparison(cfg)
    results = bundle["results"]
    scenario = bundle["scenario"]
    pin = scenario.pin_dbm
    peh = scenario.peh_w * 1e9
    qs = [0, 1, 10, 50, 90, 99, 100]
    print("p_in dBm quantiles:", {q: float(np.percentile(pin, q)) for q in qs})
    print("P_eh nW quantiles:", {q: float(np.percentile(peh, q)) for q in qs})
    print(f"p_in median={float(np.median(pin)):.2f} dBm (paper Fig. 5(a) ≈ −30 dBm)")
    print()
    out = results_dir()
    out.mkdir(parents=True, exist_ok=True)

    print()
    rows = []
    summary = {
        "seed": cfg.seed,
        "num_devices": cfg.num_devices,
        "device_type": 1,
        "strategies": {},
        "warnings": bundle["warnings"],
    }
    fig, ax = plt.subplots(figsize=(8.2, 5.2))
    styles = {
        "em": {"color": "#4c78a8", "ls": "--", "lw": 1.8},
        "dcm_1_group": {"color": "#f58518", "ls": "-.", "lw": 1.8},
        "dcm_4_group": {"color": "#54a24b", "ls": "-", "lw": 2.2},
    }
    for key, res in results.items():
        m = res.metrics
        print(f"{res.label}:")
        print(f"  T50 = {_fmt(m['t50_s'])}")
        print(f"  T90 = {_fmt(m['t90_s'])}")
        print(f"  T95 = {_fmt(m['t95_s'])}")
        print(f"  T99 = {_fmt(m['t99_s'])}")
        print(f"  final = {m['final_ratio_pct']:.2f}%")
        print(f"  paging={m['n_paging']} attempts={m['n_msg1_attempts']} collisions={m['n_collisions']}")
        print()
        st = styles.get(key, {})
        ax.plot(np.array(res.times_s) * 1e3, res.ratio_pct, label=res.label, **st)
        summary["strategies"][key] = {
            "label": res.label,
            "t50_s": m["t50_s"],
            "t90_s": m["t90_s"],
            "t95_s": m["t95_s"],
            "t99_s": m["t99_s"],
            "final_ratio_pct": m["final_ratio_pct"],
            "n_paging": m["n_paging"],
            "n_msg1_attempts": m["n_msg1_attempts"],
            "n_collisions": m["n_collisions"],
            "collision_rate": m["collision_rate"],
        }
        for t, y in zip(res.times_s, res.ratio_pct):
            rows.append({"strategy": key, "time_ms": t * 1e3, "ratio_pct": y})

    ax.set_xlabel("Time (ms)")
    ax.set_ylabel("Successfully inventoried A-IoT device ratio (%)")
    ax.set_title("Figure 5(b) reproduction — Device 1")
    ax.set_xlim(0, cfg.max_time_s * 1e3)
    ax.set_ylim(0, 105)
    ax.grid(True, alpha=0.35)
    ax.legend(frameon=False)
    fig.tight_layout()

    out = results_dir()
    out.mkdir(parents=True, exist_ok=True)
    png = out / "fig5b_reproduced.png"
    csv_path = out / "fig5b_reproduced.csv"
    json_path = out / "fig5b_metrics.json"
    try:
        fig.savefig(png, dpi=160)
        with csv_path.open("w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=["strategy", "time_ms", "ratio_pct"])
            writer.writeheader()
            writer.writerows(rows)
        json_path.write_text(json.dumps(summary, indent=2))
    except PermissionError:
        png = out / "fig5b_latest.png"
        csv_path = out / "fig5b_latest.csv"
        json_path = out / "fig5b_latest.json"
        fig.savefig(png, dpi=160)
        with csv_path.open("w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=["strategy", "time_ms", "ratio_pct"])
            writer.writeheader()
            writer.writerows(rows)
        json_path.write_text(json.dumps(summary, indent=2))
    print("Saved:")
    print(f"  {png}")
    print(f"  {csv_path}")
    print(f"  {json_path}")


if __name__ == "__main__":
    main()
