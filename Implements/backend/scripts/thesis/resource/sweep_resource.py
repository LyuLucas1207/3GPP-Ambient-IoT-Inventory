#!/usr/bin/env python3
"""Resource-sharing policies: how much of the ideal multi-reader gain survives.

For every (scheme, active readers, F, CW suppression, start offsets, seed) the
script runs the ``independent`` ideal (each reader its own F subbands, no
interference), a ``serial`` baseline (one reader on the air at a time: TDMA
with every reader in its own slot) and each policy. The ideal-gain retention

    G = (T_serial - T_policy) / (T_serial - T_ideal)

is 1 when a policy keeps the whole multi-reader speed-up, 0 when it is no
better than serial and negative when it is worse. It is reported for T99 and
for the mean identification time.

Outputs under ``results/``: ``resource_sweep.csv`` (one row per run),
``resource_retention.csv`` (means per configuration) and
``resource_retention_<scheme>.png``.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

from _common import mean_or_none, pmap, scene, times, write_csv  # noqa: E402

from app.simulator_thesis.inventory.headless import reader_ids, run_headless  # noqa: E402
from app.simulator_thesis.inventory.state import EpisodeConfig  # noqa: E402

POLICIES = ("shared", "fdma", "tdma", "hybrid", "lbt")
SERIAL = {"mode": "tdma", "conflict_distance_m": 1e9}


def _offsets(sc: dict, kind: str, step_s: float) -> dict[str, float]:
    if kind == "none":
        return {}
    ids = reader_ids(sc)
    if kind == "staggered":
        return {str(r): i * step_s for i, r in enumerate(ids)}
    if kind == "two_groups":
        return {str(r): (step_s if i % 2 else 0.0) for i, r in enumerate(ids)}
    raise ValueError(kind)


def _run(job: dict) -> dict:
    sc = scene(job["n"], job["readers"], job["seed"])
    cfg = {
        "k_initial": job["k"], "adaptive_k": True, "max_time_s": job["max_time"], "stall_timeout_s": job["stall"],
        "use_grouping": job["scheme"] == "periodic", "g": 2, "f_freq": job["f"],
        "reader_start_offsets": _offsets(sc, job["offsets"], job["offset_step"]),
        "resource": {**job["resource"], "other_cw_suppression_db": job["cw"]},
    }
    res = run_headless(sc, EpisodeConfig.from_json(job["scheme"], cfg), job["seed"], keep_rounds=False)
    st = res.state
    ix = {k: sum(r.interference.get(k, 0) for r in st.readers) for k in ("frames_hit", "r2d_lost", "m1_lost", "m2_lost", "m3_lost", "deferrals", "deferred_s")}
    w = st.world
    return {
        "scheme": job["scheme"], "readers": job["readers"], "f": job["f"], "cw_supp_db": job["cw"],
        "offsets": job["offsets"], "seed": job["seed"], "n": job["n"], "policy": job["label"],
        "n_colors": st.coord.n_colors if st.coord else 1,
        "identified": res.identified, "reachable": int(w.N - (w.dropped & (w.drop_cause == 1)).sum()),
        "frames": st.rounds_total, "sim_time_s": st.sim_time, **times(res), **ix,
    }


def retention(rows: list[dict]) -> list[dict]:
    key = lambda r: (r["scheme"], r["readers"], r["f"], r["cw_supp_db"], r["offsets"], r["seed"])  # noqa: E731
    by: dict[tuple, dict[str, dict]] = {}
    for r in rows:
        by.setdefault(key(r), {})[r["policy"]] = r
    per_seed = []
    for k, runs in by.items():
        ideal, serial = runs.get("ideal"), runs.get("serial")
        if not ideal or not serial:
            continue
        for name, r in runs.items():
            out = {"scheme": k[0], "readers": k[1], "f": k[2], "cw_supp_db": k[3], "offsets": k[4], "seed": k[5], "policy": name}
            # A mean over the few devices a collapsed policy did identify is not comparable.
            complete = all(x["identified"] >= 0.99 * max(1, x["reachable"]) for x in (r, ideal, serial))
            for metric in ("t99", "t_mean"):
                ts, ti, tp = serial[metric], ideal[metric], r[metric]
                ok = complete and None not in (ts, ti, tp) and abs(ts - ti) > 1e-9
                out[f"G_{metric}"] = (ts - tp) / (ts - ti) if ok else None
                out[metric] = tp
            out["identified_fraction"] = r["identified"] / max(1, r["reachable"])
            per_seed.append(out)
    groups: dict[tuple, list[dict]] = {}
    for r in per_seed:
        groups.setdefault((r["scheme"], r["readers"], r["f"], r["cw_supp_db"], r["offsets"], r["policy"]), []).append(r)
    return [
        {
            "scheme": g[0], "readers": g[1], "f": g[2], "cw_supp_db": g[3], "offsets": g[4], "policy": g[5], "seeds": len(rs),
            "G_t99": mean_or_none(r["G_t99"] for r in rs), "G_t_mean": mean_or_none(r["G_t_mean"] for r in rs),
            "t99": mean_or_none(r["t99"] for r in rs), "t_mean": mean_or_none(r["t_mean"] for r in rs),
            "identified_fraction": mean_or_none(r["identified_fraction"] for r in rs),
            "t99_missing": sum(1 for r in rs if r["t99"] is None),
        }
        for g, rs in groups.items()
    ]


def plot(summary: list[dict], out_dir: Path) -> list[Path]:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    files = []
    for scheme in sorted({s["scheme"] for s in summary}):
        sub = [s for s in summary if s["scheme"] == scheme and s["policy"] not in ("ideal", "serial")]
        variants = sorted({(s["f"], s["cw_supp_db"], s["offsets"]) for s in sub})
        fig, axes = plt.subplots(1, len(variants), figsize=(5.2 * len(variants), 4.2), squeeze=False)
        for ax, (f, cw, off) in zip(axes[0], variants):
            for policy in POLICIES:
                pts = sorted((s["readers"], s["G_t_mean"]) for s in sub if (s["f"], s["cw_supp_db"], s["offsets"], s["policy"]) == (f, cw, off, policy) and s["G_t_mean"] is not None)
                if pts:
                    ax.plot([p[0] for p in pts], [p[1] for p in pts], marker="o", label=policy)
            ax.axhline(1.0, color="k", lw=0.8, ls="--")
            ax.axhline(0.0, color="grey", lw=0.8, ls=":")
            ax.set_xlabel("active readers")
            ax.set_ylabel("ideal-gain retention G (mean ID time)")
            ax.set_title(f"{scheme}, F={f}, CW supp. {cw:g} dB, offsets={off}", fontsize=9)
            ax.grid(True, alpha=0.3)
            ax.legend(fontsize=8)
        fig.tight_layout()
        path = out_dir / f"resource_retention_{scheme}.png"
        fig.savefig(path, dpi=150)
        plt.close(fig)
        files.append(path)
    return files


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--schemes", nargs="+", default=["aperiodic"], choices=["aperiodic", "periodic"])
    ap.add_argument("--readers", nargs="+", type=int, default=[2, 6, 12, 18], help="active readers (2 = TR D1T1-A2)")
    ap.add_argument("--policies", nargs="+", default=list(POLICIES), choices=list(POLICIES))
    ap.add_argument("--f", nargs="+", type=int, default=[8], help="subbands F")
    ap.add_argument("--cw-supp", nargs="+", type=float, default=[61.0], help="other-reader CW suppression (dB); TR 6.7.5: 61")
    ap.add_argument("--offsets", nargs="+", default=["none"], choices=["none", "staggered", "two_groups"])
    ap.add_argument("--offset-step", type=float, default=0.5, help="seconds between start groups")
    ap.add_argument("--n", type=int, default=300, help="devices in the hall")
    ap.add_argument("--seeds", type=int, default=5)
    ap.add_argument("--base-seed", type=int, default=0)
    ap.add_argument("--k-initial", type=int, default=32)
    ap.add_argument("--max-time", type=float, default=300.0)
    ap.add_argument("--stall-timeout", type=float, default=300.0)
    ap.add_argument("--tdma-window", type=float, default=0.5)
    ap.add_argument("--workers", type=int, default=None)
    ap.add_argument("--out", type=Path, default=HERE / "results")
    args = ap.parse_args()

    variants = [("ideal", {"mode": "independent"}), ("serial", {**SERIAL, "tdma_window_s": args.tdma_window})]
    variants += [(p, {"mode": p, "tdma_window_s": args.tdma_window}) for p in args.policies]
    jobs = [
        {"scheme": s, "readers": r, "f": f, "cw": cw, "offsets": off, "offset_step": args.offset_step,
         "seed": args.base_seed + i, "n": args.n, "k": args.k_initial, "max_time": args.max_time,
         "stall": args.stall_timeout, "label": label, "resource": res}
        for s in args.schemes for r in args.readers for f in args.f for cw in args.cw_supp
        for off in args.offsets for i in range(args.seeds) for label, res in variants
    ]
    print(f"{len(jobs)} runs", flush=True)
    rows = pmap(_run, jobs, args.workers)
    summary = retention(rows)
    files = [write_csv(rows, args.out / "resource_sweep.csv"), write_csv(summary, args.out / "resource_retention.csv")]
    files += plot(summary, args.out)
    for s in sorted(summary, key=lambda s: (s["scheme"], s["f"], s["cw_supp_db"], s["offsets"], s["readers"], s["policy"])):
        g = s["G_t_mean"]
        print(f"  {s['scheme']:9s} R={s['readers']:>2} F={s['f']} cw={s['cw_supp_db']:g} {s['offsets']:10s} {s['policy']:8s} "
              f"G(mean)={'   n/a' if g is None else f'{g:6.2f}'}  t_mean={s['t_mean'] or float('nan'):8.2f}s  id={100 * (s['identified_fraction'] or 0):5.1f}%")
    for f in files:
        print(f"wrote {f}")


if __name__ == "__main__":
    main()
