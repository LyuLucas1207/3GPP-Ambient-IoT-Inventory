#!/usr/bin/env python3
"""Termination rules: missed devices against extra paging time (Pareto).

One oracle episode per (scheme, readers, N, seed) is simulated; every rule is
then scored by replaying its round log (``inventory.termination.replay``).
On a single reader the replay is exact; with several readers it is an
approximation, so ``--online`` also simulates each rule live.

Outputs (next to this script, under ``results/``): ``termination_sweep.csv``
(one row per rule x episode), ``termination_pareto.csv`` (means per rule) and
``termination_pareto_<scheme>_<readers>r.png``.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

from _common import mean_or_none, pmap, scene, times, write_csv  # noqa: E402

from app.thesis_simulator.inventory.headless import run_headless  # noqa: E402
from app.thesis_simulator.inventory.state import EpisodeConfig  # noqa: E402
from app.thesis_simulator.inventory.termination import TerminationSpec, replay  # noqa: E402


def rule_grid(quick: bool) -> list[dict]:
    q = [2, 4, 8, 16, 32] if quick else [2, 4, 8, 16, 32, 64, 128]
    rules: list[dict] = [{"kind": "oracle"}]
    rules += [{"kind": "quiet_rounds", "quiet_rounds": n} for n in q]
    for w in ([10, 50] if quick else [10, 20, 50, 100]):
        for r in ([0.01, 0.05] if quick else [0.002, 0.01, 0.05, 0.1]):
            rules.append({"kind": "id_rate", "window_mode": "rounds", "window": w, "r_rel": r})
    for w in ([2.0, 10.0] if quick else [1.0, 2.0, 5.0, 10.0, 30.0]):
        rules.append({"kind": "id_rate", "window_mode": "seconds", "window": w, "r_rel": 0.01})
    for a in ([0.1] if quick else [0.05, 0.1, 0.2]):
        for r in ([0.01, 0.05] if quick else [0.005, 0.01, 0.05]):
            rules.append({"kind": "id_rate", "window_mode": "ewma", "ewma_alpha": a, "r_rel": r})
    for m in ([0.0, 0.5] if quick else [0.0, 0.25, 0.5, 1.0]):
        rules.append({"kind": "energy_bound", "margin": m, "energy_source": "edge"})
    rules.append({"kind": "energy_bound", "margin": 0.0, "energy_source": "actual"})
    rules.append({"kind": "combined", "combine": "any", "rules": [{"kind": "quiet_rounds", "quiet_rounds": 32}, {"kind": "energy_bound"}]})
    rules.append({"kind": "combined", "combine": "all", "rules": [{"kind": "quiet_rounds", "quiet_rounds": 8}, {"kind": "energy_bound", "margin": 0.25}]})
    return rules


def _episode(job: dict) -> list[dict]:
    sc = scene(job["n"], job["readers"], job["seed"])
    base = {
        "k_initial": job["k"], "adaptive_k": True, "stall_timeout_s": job["stall"],
        "max_time_s": job["max_time"], "use_grouping": job["scheme"] == "periodic", "g": 2,
    }
    oracle = run_headless(sc, EpisodeConfig.from_json(job["scheme"], base), job["seed"])
    t_wc = {r.reader_id: r.t_wc_s for r in oracle.state.readers}
    # t_wc depends on the energy source; rebuild for "actual" rules.
    t_wc_actual = None
    w = oracle.state.world
    reachable = int(w.N - (w.dropped & (w.drop_cause == 1)).sum())
    ot = times(oracle)
    rows = []
    for rule in job["rules"]:
        spec = TerminationSpec.from_json(rule)
        uses_actual = "actual" in json.dumps(rule)
        if uses_actual and t_wc_actual is None:
            from app.thesis_simulator.inventory.episode import build_episode
            import numpy as np

            st = build_episode(sc, EpisodeConfig.from_json(job["scheme"], {**base, "termination": {"kind": "energy_bound", "energy_source": "actual"}}), np.random.default_rng(0))
            t_wc_actual = {r.reader_id: r.t_wc_s for r in st.readers}
        out = replay(spec, oracle.rounds, t_wc_by_reader=t_wc_actual if uses_actual else t_wc, reachable=reachable)
        row = {
            "scheme": job["scheme"], "readers": job["readers"], "n": job["n"], "seed": job["seed"],
            "rule": spec.label(), "kind": spec.kind, "method": "replay",
            "reachable": reachable, "identified_oracle": out.identified_total,
            "missed": out.missed, "missed_fraction": out.missed / max(1, out.identified_total),
            "t_stop": out.t_stop, "t_last_id": out.t_last_id, "t99": ot["t99"],
            "extra_time_s": out.extra_time_s, "extra_vs_t99_s": out.extra_vs_t99_s,
            "t_wc_max_s": max((v for v in (t_wc_actual if uses_actual else t_wc).values() if v is not None), default=None),
        }
        rows.append(row)
        if job["online"] and not spec.is_oracle:
            live = run_headless(sc, EpisodeConfig.from_json(job["scheme"], {**base, "termination": rule}), job["seed"])
            t_stop = max((r.term.stopped_t or r.clock_s) for r in live.state.readers)
            rows.append({
                **row, "method": "online", "missed": out.identified_total - live.identified,
                "missed_fraction": (out.identified_total - live.identified) / max(1, out.identified_total),
                "t_stop": t_stop,
                "extra_time_s": None if ot["t_last"] is None else t_stop - ot["t_last"],
                "extra_vs_t99_s": None if ot["t99"] is None else t_stop - ot["t99"],
            })
    return rows


def pareto(rows: list[dict]) -> list[dict]:
    groups: dict[tuple, list[dict]] = {}
    for r in rows:
        groups.setdefault((r["scheme"], r["readers"], r["method"], r["rule"]), []).append(r)
    out = []
    for (scheme, readers, method, rule), rs in groups.items():
        out.append({
            "scheme": scheme, "readers": readers, "method": method, "rule": rule, "kind": rs[0]["kind"], "episodes": len(rs),
            "missed_fraction": mean_or_none(r["missed_fraction"] for r in rs),
            "extra_vs_t99_s": mean_or_none(r["extra_vs_t99_s"] for r in rs),
            "extra_time_s": mean_or_none(r["extra_time_s"] for r in rs),
            "t_stop": mean_or_none(r["t_stop"] for r in rs),
        })
    for o in out:
        o["reference"] = o["kind"] == "oracle"
        if o["reference"]:
            o["pareto_optimal"] = False
            continue
        same = [p for p in out if p["kind"] != "oracle" and (p["scheme"], p["readers"], p["method"]) == (o["scheme"], o["readers"], o["method"])]
        o["pareto_optimal"] = not any(
            (p["missed_fraction"] or 0) <= (o["missed_fraction"] or 0) and (p["extra_time_s"] or 0) <= (o["extra_time_s"] or 0)
            and ((p["missed_fraction"] or 0) < (o["missed_fraction"] or 0) or (p["extra_time_s"] or 0) < (o["extra_time_s"] or 0))
            for p in same
        )
    return out


def plot(points: list[dict], out_dir: Path) -> list[Path]:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    files = []
    colors = {"oracle": "#000000", "quiet_rounds": "#4c78a8", "id_rate": "#f58518", "energy_bound": "#54a24b", "combined": "#b279a2"}
    for key in sorted({(p["scheme"], p["readers"]) for p in points}):
        fig, ax = plt.subplots(figsize=(7.2, 4.8))
        for p in points:
            if (p["scheme"], p["readers"]) != key or p["method"] != "replay" or p["extra_time_s"] is None or p["reference"]:
                continue
            ax.scatter(p["extra_time_s"], 100 * (p["missed_fraction"] or 0), color=colors.get(p["kind"], "grey"),
                       edgecolor="k" if p["pareto_optimal"] else "none", s=46, zorder=3)
        for kind, c in colors.items():
            if kind != "oracle":
                ax.scatter([], [], color=c, label=kind)
        ax.axvline(0.0, color="k", lw=0.8, ls="--", label="oracle (stops at the last ID)")
        ax.set_xscale("symlog", linthresh=1.0)
        ax.set_xlabel("extra paging time after the last ID (s)")
        ax.set_ylabel("missed devices (% of oracle)")
        ax.set_title(f"Termination rules - {key[0]}, {key[1]} reader(s) (black edge = Pareto-optimal)")
        ax.grid(True, alpha=0.3)
        ax.legend(fontsize=8)
        fig.tight_layout()
        path = out_dir / f"termination_pareto_{key[0]}_{key[1]}r.png"
        fig.savefig(path, dpi=150)
        plt.close(fig)
        files.append(path)
    return files


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--schemes", nargs="+", default=["aperiodic", "periodic"], choices=["aperiodic", "periodic"])
    ap.add_argument("--readers", nargs="+", type=int, default=[1, 18], help="active readers per scene (1 = single reader)")
    ap.add_argument("--n", nargs="+", type=int, default=[300], help="device counts")
    ap.add_argument("--seeds", type=int, default=10)
    ap.add_argument("--base-seed", type=int, default=0)
    ap.add_argument("--k-initial", type=int, default=32)
    ap.add_argument("--stall-timeout", type=float, default=5000.0, help="oracle runs: 2a devices can need ~1500 s to recharge")
    ap.add_argument("--max-time", type=float, default=None)
    ap.add_argument("--online", action="store_true", help="also simulate every rule live")
    ap.add_argument("--quick", action="store_true", help="smaller rule grid")
    ap.add_argument("--workers", type=int, default=None)
    ap.add_argument("--out", type=Path, default=HERE / "results")
    args = ap.parse_args()

    rules = rule_grid(args.quick)
    jobs = [
        {"scheme": s, "readers": r, "n": n, "seed": args.base_seed + i, "rules": rules, "k": args.k_initial,
         "stall": args.stall_timeout, "max_time": args.max_time, "online": args.online}
        for s in args.schemes for r in args.readers for n in args.n for i in range(args.seeds)
    ]
    print(f"{len(jobs)} oracle episodes x {len(rules)} rules", flush=True)
    rows = [row for chunk in pmap(_episode, jobs, args.workers) for row in chunk]
    points = pareto(rows)
    files = [write_csv(rows, args.out / "termination_sweep.csv"), write_csv(points, args.out / "termination_pareto.csv")]
    files += plot(points, args.out)
    best = sorted((p for p in points if p["pareto_optimal"] and p["method"] == "replay"), key=lambda p: (p["scheme"], p["readers"], p["extra_time_s"] or 0))
    for p in best:
        print(f"  pareto {p['scheme']:9s} {p['readers']:>2}r  {p['rule']:50s} missed={100 * (p['missed_fraction'] or 0):6.2f}%  extra={p['extra_time_s'] or 0:8.2f}s")
    for f in files:
        print(f"wrote {f}")


if __name__ == "__main__":
    main()
