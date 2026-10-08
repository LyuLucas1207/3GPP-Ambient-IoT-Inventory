#!/usr/bin/env python3
"""Validation report for the aperiodic-paging paper reproduction (spec section 30).

Fast checks (RF utilities, timing, Lmax, Figure 4 populations, checkpoint
integrity) run every time. Figures 5-8 and Tables IV-VI are read from the
reproduction scripts' cached outputs in results/aperiodic/; a missing
output is reported as MISSING together with the command that produces it.

Status:
    PASS / FAIL     hard checks with a stated tolerance
    OK / OFF        diagnostics: inside / outside the stated tolerance
    MISSING         result not produced yet

Tolerances are listed in TOL and printed in the report; they are never
widened to turn a miss into a pass.

    python scripts/validate_aperiodic_paper.py [--json-only]
"""

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import numpy as np

from app.aperiodic_simulator.analysis.reference_targets import results_dir, scalar_targets, table4, table5, table6

TOL = {
    "cdf_gap_mean_db": 1.0,
    "n_eff_rel_pct": 3.0,
    "type_share_pp": 2.0,
    "below_sleep_pp": 3.0,
    "interval_L1_ms": 0.5,
    "interval_L16_ms": 1.0,
    "ng4_group_pp": 2.0,
    "t99_reduction_pp": 5.0,
    "table4_total_rel_pct": 15.0,
    "fig7_gain_pp": 8.0,
    "table5_rel_pct": 15.0,
    "table6_rel_pct": 15.0,
}

LAYERS = {
    "rf": "shared RF utilities",
    "fig4": "layout/link budget",
    "neff": "layout/link budget",
    "below_sleep": "harvesting model",
    "interval": "round timing",
    "lmax": "round timing; energy state transitions",
    "groups": "initial availability; group synchronization",
    "fig5": "energy state transitions; group synchronization; PFSA/PZE",
    "fig6": "PFSA/PZE; capture/detection; harvesting model",
    "table4": "energy state transitions; round timing",
    "ppo": "PPO action transform/training",
    "fig7": "PPO action transform/training; capture/detection",
    "table5_pfsa": "PFSA/PZE; round timing; initial availability",
    "table5_rl": "PPO action transform/training",
    "table6": "PPO action transform/training",
}

ROWS: list[dict] = []


def add(name: str, status: str, detail: str, layer_key: str, values: dict | None = None):
    row = {"check": name, "status": status, "detail": detail, "values": values or {}}
    if status in ("FAIL", "OFF"):
        row["likely_layer"] = LAYERS[layer_key]
    ROWS.append(row)


def load(path: Path):
    return json.loads(path.read_text()) if path.exists() else None


def missing(name: str, cmd: str):
    ROWS.append({"check": name, "status": "MISSING", "detail": f"run: {cmd}", "values": {}})


# ------------------------------------------------------------------ fast checks
def check_rf():
    from app.common.rf import dbm_to_watts, harvest_power_w, watts_to_dbm
    from app.simulator.physics import channel as legacy

    x = np.linspace(-60, 30, 91)
    rt = float(np.max(np.abs(watts_to_dbm(dbm_to_watts(x)) - x)))
    same = legacy.dbm_to_watts is dbm_to_watts and legacy.harvest_power_w is harvest_power_w
    ok = rt < 1e-9 and same
    add("Shared RF utility regression", "PASS" if ok else "FAIL", f"dBm<->W round-trip err {rt:.1e}; legacy re-exports identical: {same}", "rf")


def check_timing_lmax():
    from app.aperiodic_simulator.physics.energy import compute_global_lmax
    from app.aperiodic_simulator.core.timing import periodic_round_interval_s

    for L, target, tol in ((1, 82.0, TOL["interval_L1_ms"]), (16, 1089.14, TOL["interval_L16_ms"])):
        v = periodic_round_interval_s(L) * 1e3
        add(f"L={L} periodic interval", "PASS" if abs(v - target) <= tol else "FAIL", f"{v:.2f} ms vs {target} ms (±{tol})", "interval")
    lm = compute_global_lmax()
    add("Lmax = 83", "PASS" if lm == 83 else "FAIL", f"Lmax = {lm}", "lmax")


def check_figure4():
    from app.aperiodic_simulator.reproduction.reproduce import figure4_data

    st = scalar_targets()
    d = figure4_data(15000, 0)
    gaps = {k: e["paper_cdf_quantile_gap_db"]["mean_abs"] for k, e in d["scenarios"].items()}
    ok = all(g <= TOL["cdf_gap_mean_db"] for g in gaps.values())
    add("Figure 4 CDF/channel checks", "PASS" if ok else "FAIL", "mean |ΔP_in| at equal CDF: " + ", ".join(f"{k} {v:.2f} dB" for k, v in gaps.items()) + f" (≤{TOL['cdf_gap_mean_db']})", "fig4", gaps)
    for scen, label in (("single_source", "Single-source"), ("multi_source", "Multi-source")):
        e = d["scenarios"][scen]
        ref = st[scen]
        rel = 100 * (e["n_eff"] - ref["n_eff"]) / ref["n_eff"]
        share_err = max(abs(100 * e["type_shares"][t] - ref["type_shares_pct"][t]) for t in ("1", "2a", "2b"))
        ok = abs(rel) <= TOL["n_eff_rel_pct"] and share_err <= TOL["type_share_pp"]
        add(
            f"{label} N_eff/type shares",
            "PASS" if ok else "FAIL",
            f"N_eff {e['n_eff']} vs {ref['n_eff']} ({rel:+.1f}%), shares "
            + "/".join(f"{100 * e['type_shares'][t]:.1f}" for t in ("1", "2a", "2b"))
            + " vs "
            + "/".join(f"{ref['type_shares_pct'][t]}" for t in ("1", "2a", "2b"))
            + f" % (max {share_err:.1f} pp)",
            "neff",
        )
    hb = d["scenarios"]["single_source"]["harvest_below_sleep"]
    ref = st["single_source"]
    err = max(abs(100 * hb["share_of_n_eff"] - ref["harvest_below_sleep_pct"]), abs(100 * hb["type2_share_of_below"] - ref["harvest_below_sleep_type2_pct"]))
    add(
        "Single-source P_harv < P_sl share",
        "OK" if err <= TOL["below_sleep_pp"] else "OFF",
        f"{100 * hb['share_of_n_eff']:.1f}% (type 2: {100 * hb['type2_share_of_below']:.1f}%) vs {ref['harvest_below_sleep_pct']}% ({ref['harvest_below_sleep_type2_pct']}%)",
        "below_sleep",
    )


def check_ppo():
    from app.aperiodic_simulator.rl.checkpoint import CheckpointMissing, load_meta

    out = []
    ok = True
    for a in (0.5, 0.0, 0.25, 0.75):
        try:
            m = load_meta(a)
            out.append(f"α={a}: sha256 ok, {m['training_steps']:,} steps" + ("" if m["training_steps"] >= 1_000_000 else " (under-trained)"))
        except CheckpointMissing as exc:
            ok = ok and a != 0.5
            out.append(f"α={a}: {'missing' if 'not available' in str(exc) else 'INTEGRITY FAILURE'}")
    add("PPO checkpoint integrity", "PASS" if ok else "FAIL", "; ".join(out), "ppo")


# ------------------------------------------------------------------ cached results
def check_groups_fig6(rd: Path):
    f6 = load(rd / "figure6" / "figure6.json")
    if not f6:
        missing("N_g=4 group distribution", "python scripts/reproduce_aperiodic_fig6.py --episodes 100")
        missing("Figure 6 qualitative ordering", "python scripts/reproduce_aperiodic_fig6.py --episodes 100")
        return
    gp = f6["panels"]["a_L16"]["curves"]["periodic_Ng4"]["aggregate"].get("group_populations") or {}
    sim = [100 * gp.get(f"group_{i}", 0.0) for i in range(1, 5)]
    ref = scalar_targets()["multi_source"]["ng4_group_population_pct"]
    err = max(abs(s - r) for s, r in zip(sim, ref))
    add(
        "N_g=4 group distribution",
        "OK" if err <= TOL["ng4_group_pp"] else "OFF",
        "Fig. 6(a): " + "/".join(f"{s:.1f}" for s in sim) + " vs " + "/".join(str(r) for r in ref) + f" % (max {err:.1f} pp)",
        "groups",
    )
    orders = {p: v["validation"]["t99_order"] for p, v in f6["panels"].items()}
    ok = all(o[:3] == ["aperiodic", "periodic_Ng1", "periodic_Ng4"] for o in orders.values())
    t99 = {
        p: {n: round(c["aggregate"]["T99"]["mean"], 1) for n, c in v["curves"].items() if c["aggregate"].get("T99")} for p, v in f6["panels"].items()
    }
    mae = {p: {n: round(c["reference"].get("mae", float("nan")), 2) for n, c in v["curves"].items()} for p, v in f6["panels"].items()}
    add("Figure 6 qualitative ordering", "OK" if ok else "OFF", f"T99 order aperiodic < Ng1 < Ng4 in both panels: {ok}; T99 {t99}; MAE pp {mae}; {f6['episodes']} episodes", "fig6")


def check_fig5_table4(rd: Path):
    f5 = load(rd / "figure5" / "figure5.json")
    if not f5:
        missing("Figure 5 T99 reductions", "python scripts/reproduce_aperiodic_fig5.py --episodes 100")
        missing("Table IV depletion counts", "python scripts/reproduce_aperiodic_fig5.py --episodes 100")
        return
    parts, ok = [], True
    for p, v in f5["panels"].items():
        val = v["validation"]
        sim, ref = val.get("t99_reduction_vs_periodic_Ng4_pct"), val.get("paper_t99_reduction_pct")
        if sim is None or ref is None:
            ok = False
            continue
        ok = ok and abs(sim - ref) <= TOL["t99_reduction_pp"]
        parts.append(f"{p}: {sim:.1f}% vs {ref}%")
    add("Figure 5 T99 reductions", "OK" if ok else "OFF", "; ".join(parts) + f" (±{TOL['t99_reduction_pp']} pp, {f5['episodes']} episodes)", "fig5")
    rows = f5.get("table_iv") or []
    worst, parts, ok = None, [], True
    stages = ("paging", "msg1", "EI", "msg2", "msg3")
    for r in rows:
        s, p = r["simulated"], r["paper"]
        if p["total"] == 0:
            parts.append(f"{r['protocol']} L={r['L']}: {s['total']:.0f} vs 0")
            ok = ok and s["total"] == 0
            continue
        rel = 100 * (s["total"] - p["total"]) / p["total"]
        ok = ok and abs(rel) <= TOL["table4_total_rel_pct"]
        st = max(stages, key=lambda k: abs(s[k] - p[k]))
        parts.append(f"{r['protocol']} L={r['L']} Ng={r['N_g']}: total {s['total']:.0f} vs {p['total']:.0f} ({rel:+.1f}%), largest stage gap {st} {s[st]:.0f} vs {p[st]:.0f}")
    add("Table IV depletion counts", "OK" if ok else "OFF", "; ".join(parts) + f" (total ±{TOL['table4_total_rel_pct']}%)", "table4")


def check_fig7(rd: Path):
    f7 = load(rd / "figure7" / "figure7.json")
    if not f7:
        missing("Figure 7 RL vs CMEBE gain", "python scripts/reproduce_aperiodic_fig7.py --episodes 100")
        return
    v = f7["panels"]["multi_source"]["validation"]
    gain = v.get("rl_total_time_reduction_vs_best_dfsa_pct")
    curves = f7["panels"]["multi_source"]["curves"]
    tt = {n: round(c["aggregate"]["T_total_s"]["mean"], 1) for n, c in curves.items() if c["aggregate"].get("T_total_s")}
    mae = {n: round(c["reference"].get("mae", float("nan")), 2) for n, c in curves.items()}
    ck = f7.get("checkpoints", {}).get("0.5", {})
    note = "" if ck.get("fully_trained") else f"; RL checkpoint has {ck.get('training_steps')} of 1,000,000 steps"
    if gain is None:
        add("Figure 7 RL vs CMEBE gain", "OFF", f"RL unavailable: {f7.get('unavailable')}", "fig7")
        return
    ok = abs(gain - v["paper_rl_reduction_vs_cmebe_pct"]) <= TOL["fig7_gain_pp"]
    add(
        "Figure 7 RL vs CMEBE gain",
        "OK" if ok else "OFF",
        f"RL total-time reduction vs best DFSA ({v['best_dfsa_baseline']}) {gain:.1f}% vs paper {v['paper_rl_reduction_vs_cmebe_pct']}% (±{TOL['fig7_gain_pp']} pp); "
        f"T_total {tt}; curve MAE pp {mae}; {f7['episodes']} episodes{note}",
        "fig7",
    )


def check_fig8(rd: Path):
    f8 = load(rd / "figure8" / "figure8.json")
    if not f8:
        missing("Figure 8 resource efficiency", "python scripts/reproduce_aperiodic_fig8.py --episodes 100")
        return
    s = f8["series"]
    mae = {n: round(v["reference"].get("mae", float("nan")), 2) for n, v in s.items()}
    rl_best = None
    if "recurrent_ppo" in s:
        rl = np.array([p["re_pct"]["mean"] for p in s["recurrent_ppo"]["points"]])
        others = [np.array([p["re_pct"]["mean"] for p in v["points"]]) for k, v in s.items() if k != "recurrent_ppo"]
        rl_best = float(np.mean(rl >= np.max(others, axis=0)))
    add(
        "Figure 8 resource efficiency",
        "OK" if rl_best is not None and rl_best >= 0.8 else "OFF",
        f"RE MAE vs paper (pp) {mae}; RL ≥ every PFSA variant at {rl_best if rl_best is None else f'{100 * rl_best:.0f}%'} of N points (paper: all); {f8['episodes']} episodes",
        "fig7",
    )


def check_tables(rd: Path):
    t = load(rd / "tables" / "tables.json")
    if not t:
        missing("Table V values", "python scripts/reproduce_aperiodic_tables.py --episodes 100")
        missing("Table VI alpha trends", "python scripts/reproduce_aperiodic_tables.py --episodes 100")
        return
    for group, key in (("PFSA", "table5_pfsa"), ("RL", "table5_rl")):
        rows = [r for r in t["table_v"] if (r["method"] == "recurrent_ppo") == (group == "RL")]
        avail = [r for r in rows if r.get("available") and r.get("rel_err_pct") is not None]
        inside = [r for r in avail if abs(r["rel_err_pct"]) <= TOL["table5_rel_pct"]]
        detail = "; ".join(f"{r['scenario'][:5]} N={r['n_tot']} {r['method']}: {r['sim_s']:.1f} vs {r['paper_s']} ({r['rel_err_pct']:+.0f}%)" for r in avail)
        status = "OK" if avail and len(inside) == len(avail) else "OFF"
        add(f"Table V values ({group})", status, f"{len(inside)}/{len(avail)} within ±{TOL['table5_rel_pct']}%: {detail}", key)
    rows = [r for r in t["table_vi"] if r.get("available")]
    if not rows:
        add("Table VI alpha trends", "OFF", "no RL checkpoints available", "table6")
        return
    parts, ok = [], True
    for scen in ("multi_source", "single_source"):
        rs = sorted((r for r in rows if r["scenario"] == scen), key=lambda r: r["alpha"])
        if not rs:
            continue
        best = min(rs, key=lambda r: r["sim_time_s"] or np.inf)["alpha"]
        for r in rs:
            rel = 100 * (r["sim_time_s"] - r["paper_time_s"]) / r["paper_time_s"]
            ok = ok and abs(rel) <= TOL["table6_rel_pct"]
        parts.append(
            f"{scen}: best α {best} (paper 0.5); "
            + ", ".join(f"α={r['alpha']}: {r['sim_time_s']:.0f}s/{r['sim_re_pct']:.1f}% vs {r['paper_time_s']}s/{r['paper_re_pct']}%" for r in rs)
        )
        ok = ok and best == 0.5
    under = [a for a, c in t.get("checkpoints", {}).items() if c.get("available") and not c.get("fully_trained")]
    note = f"; under-trained checkpoints: α={', '.join(under)}" if under else ""
    add("Table VI alpha trends", "OK" if ok else "OFF", "; ".join(parts) + note, "table6")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--json-only", action="store_true")
    args = ap.parse_args()
    rd = results_dir()
    check_rf()
    check_figure4()
    check_timing_lmax()
    check_groups_fig6(rd)
    check_fig5_table4(rd)
    check_ppo()
    check_fig7(rd)
    check_fig8(rd)
    check_tables(rd)
    assert table4() and table5() and table6()

    out = rd / "validation"
    out.mkdir(parents=True, exist_ok=True)
    report = {"tolerances": TOL, "checks": ROWS}
    (out / "validation_report.json").write_text(json.dumps(report, indent=1))
    lines = ["# Aperiodic-paging validation report", "", "| Check | Status | Detail | Likely layer if off |", "|---|---|---|---|"]
    for r in ROWS:
        lines.append(f"| {r['check']} | {r['status']} | {r['detail']} | {r.get('likely_layer', '')} |")
    lines += ["", "Tolerances: " + ", ".join(f"{k}={v}" for k, v in TOL.items())]
    (out / "validation_report.md").write_text("\n".join(lines) + "\n")
    if not args.json_only:
        w = max(len(r["check"]) for r in ROWS) + 2
        for r in ROWS:
            print(f"{r['check']:<{w}} {r['status']:<8} {r['detail']}")
            if "likely_layer" in r:
                print(f"{'':<{w}} {'':<8} -> likely layer: {r['likely_layer']}")
        print(f"\nwrote {out / 'validation_report.md'}")
    if any(r["status"] == "FAIL" for r in ROWS):
        sys.exit(1)


if __name__ == "__main__":
    main()
