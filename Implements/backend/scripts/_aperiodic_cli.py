"""Shared CLI for the aperiodic-paging protocol-figure scripts."""

import argparse
import json

from app.aperiodic_simulator.analysis.reference_targets import results_dir
from app.aperiodic_simulator.reproduction.reproduce import run_protocol_figure, write_figure_outputs


def protocol_figure_main(figure: str) -> dict:
    ap = argparse.ArgumentParser(description=f"Reproduce {figure} of the aperiodic-paging paper")
    ap.add_argument("--episodes", type=int, default=100, help="seeded episodes per curve (paper: 100)")
    ap.add_argument("--base-seed", type=int, default=0)
    ap.add_argument("--workers", type=int, default=None)
    ap.add_argument("--n-tot", type=int, default=15000)
    ap.add_argument("--panels", nargs="*", default=None, help="e.g. a_L16 b_L1")
    ap.add_argument("--no-plot", action="store_true")
    args = ap.parse_args()
    data = run_protocol_figure(
        figure, args.episodes, args.base_seed, args.workers, args.n_tot, panels=args.panels
    )
    out = results_dir() / figure
    files = write_figure_outputs(data, out, plot=not args.no_plot)
    print_summary(data)
    if "table_iv" in data:
        tdir = results_dir() / "tables"
        tdir.mkdir(parents=True, exist_ok=True)
        (tdir / "table_iv.json").write_text(json.dumps({"episodes": data["episodes"], "rows": data["table_iv"]}, indent=1))
        files.append(tdir / "table_iv.json")
    for f in files:
        print(f"wrote {f}")
    return data


def controller_target_main(target: str) -> dict:
    from app.aperiodic_simulator.reproduction import controller_reproduce as cr

    ap = argparse.ArgumentParser(description=f"Reproduce {target} of the aperiodic-paging paper (controller level)")
    ap.add_argument("--episodes", type=int, default=100, help="seeded episodes per method/point (paper: 100)")
    ap.add_argument("--base-seed", type=int, default=0)
    ap.add_argument("--workers", type=int, default=None)
    ap.add_argument("--no-plot", action="store_true")
    ap.add_argument("--force", action="store_true", help="overwrite a cached result that used more episodes")
    args = ap.parse_args()
    run = {"figure7": cr.figure7, "figure8": cr.figure8, "tables": cr.tables}[target]
    data = run(args.episodes, args.base_seed, args.workers, progress=lambda s: print(s, flush=True))
    for name, reason in data.get("unavailable", {}).items():
        print(f"unavailable: {name}: {reason}")
    for a, ck in data.get("checkpoints", {}).items():
        if ck.get("available") and not ck["fully_trained"]:
            print(f"note: RL alpha={a} checkpoint has {ck['training_steps']} of 1,000,000 paper steps; RL numbers are not a paper reproduction")
    if target == "figure7":
        print(f"validation: {data['panels']['multi_source']['validation']}")
    files = cr.write_outputs(data, plot=not args.no_plot, force=args.force)
    for f in files:
        print(f"wrote {f}")
    if not files:
        print("kept the existing cached result (it used more episodes); pass --force to overwrite")
    return data


def print_summary(data: dict) -> None:
    for panel, p in data["panels"].items():
        print(f"\n{data['figure']} {panel} (L={p['L']}), {data['episodes']} episodes")
        for name, c in p["curves"].items():
            a = c["aggregate"]
            sim = " ".join(f"{k}={a[k]['mean']:.1f}" if a.get(k) else f"{k}=n/a" for k in ("T50", "T90", "T99"))
            ref = c["reference"].get("paper_T", {})
            pap = " ".join(f"{k}={ref[k]:.1f}" if ref.get(k) else f"{k}=n/a" for k in ("T50", "T90", "T99"))
            err = f"MAE={c['reference']['mae']:.2f} RMSE={c['reference']['rmse']:.2f}" if "mae" in c["reference"] else ""
            print(f"  {name:27s} sim {sim} | paper {pap} | {err}")
        print(f"  validation: {p['validation']}")
    for row in data.get("table_iv", []):
        s, r = row["simulated"], row["paper"]
        keys = ("paging", "msg1", "EI", "msg2", "msg3", "total")
        print(
            f"  Table IV {row['protocol']} L={row['L']} N_g={row['N_g']}: sim "
            + "/".join(f"{s[k]:.0f}" for k in keys)
            + " | paper "
            + "/".join(f"{r[k]:.0f}" for k in keys)
        )
