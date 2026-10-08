"""Protocol-level reproduction (Figures 4, 5, 6 and Table IV).

Both protocols use PFSA/PZE with fixed L; RL and L adaptation are disabled.
Every curve of a panel shares the seed sequence ``base_seed + i``.
"""

import json
import time
from pathlib import Path

import numpy as np

from app.aperiodic_simulator.core.batch import BatchResult, run_batch
from app.aperiodic_simulator.core.config import EpisodeConfig, SystemParams, config_to_dict
from app.aperiodic_simulator.physics.harvesting import build_population, harvest_below_sleep_stats, incident_power_cdf
from app.aperiodic_simulator.analysis.metrics import CURVE_STEP_S
from app.aperiodic_simulator.analysis.reference_targets import PAPER_CAPTIONS, curve_t_targets, reference_curve, scalar_targets, table4
from app.aperiodic_simulator.core.states import ControllerName, HarvestingScenario, PagingMode
from app.common.metrics import mae_rmse

PROTOCOL_CURVES = {
    "aperiodic": dict(paging_mode=PagingMode.APERIODIC, N_g=1, enforce_midround_depletion=True),
    "periodic_Ng1": dict(paging_mode=PagingMode.PERIODIC, N_g=1, enforce_midround_depletion=True),
    "periodic_Ng1_wo_depletion": dict(paging_mode=PagingMode.PERIODIC, N_g=1, enforce_midround_depletion=False),
    "periodic_Ng4": dict(paging_mode=PagingMode.PERIODIC, N_g=4, enforce_midround_depletion=True),
    "periodic_Ng4_wo_depletion": dict(paging_mode=PagingMode.PERIODIC, N_g=4, enforce_midround_depletion=False),
}
CURVE_LABELS = {
    "aperiodic": "aperiodic paging",
    "periodic_Ng1": "periodic paging, N_g=1",
    "periodic_Ng1_wo_depletion": "periodic paging, N_g=1, w/o depletion",
    "periodic_Ng4": "periodic paging, N_g=4",
    "periodic_Ng4_wo_depletion": "periodic paging, N_g=4, w/o depletion",
}
FIGURES = {
    "figure5": {
        "scenario": HarvestingScenario.SINGLE_SOURCE,
        "curves": list(PROTOCOL_CURVES),
        "panels": {"a_L16": 16, "b_L1": 1},
        "x_max": 1200.0,
    },
    "figure6": {
        "scenario": HarvestingScenario.MULTI_SOURCE,
        "curves": ["aperiodic", "periodic_Ng1", "periodic_Ng4"],
        "panels": {"a_L16": 16, "b_L1": 1},
        "x_max": 800.0,
    },
}


def _jsonable(o):
    if isinstance(o, dict):
        return {str(k): _jsonable(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [_jsonable(v) for v in o]
    if isinstance(o, np.ndarray):
        return o.tolist()
    if isinstance(o, (np.floating, np.integer)):
        return o.item()
    return o


def compare_to_reference(figure: str, panel: str, curve: str, br: BatchResult, x_max: float) -> dict:
    ref = reference_curve(figure, f"{panel}_{curve}")
    if ref is None:
        return {}
    rx, ry = ref
    t = br.times
    m = t <= min(x_max, rx.max())
    y = br.aggregate["curve_mean"]
    return {
        "paper_T": curve_t_targets(rx, ry),
        **mae_rmse(t[m], y[m], rx, ry),
    }


def run_protocol_figure(
    figure: str,
    episodes: int = 100,
    base_seed: int = 0,
    workers: int | None = None,
    n_tot: int = 15000,
    panels: list[str] | None = None,
    curves: list[str] | None = None,
    progress=print,
) -> dict:
    spec = FIGURES[figure]
    out: dict = {
        "figure": figure,
        "scenario": spec["scenario"].value,
        "episodes": episodes,
        "base_seed": base_seed,
        "n_tot": n_tot,
        "controller": ControllerName.PFSA_PZE.value,
        "panels": {},
    }
    base = EpisodeConfig(n_tot=n_tot, harvesting_scenario=spec["scenario"], controller=ControllerName.PFSA_PZE, t_max_s=1200.0)
    out["config"] = config_to_dict(base)
    for panel, L in spec["panels"].items():
        if panels and panel not in panels:
            continue
        pdata = {"L": L, "curves": {}}
        for name in spec["curves"]:
            if curves and name not in curves:
                continue
            t0 = time.time()
            cfg = base.with_(L_fixed=L, **PROTOCOL_CURVES[name])
            br = run_batch(cfg, episodes, base_seed, label=name, workers=workers)
            agg = br.aggregate
            pdata["curves"][name] = {
                "label": CURVE_LABELS[name],
                "aggregate": {k: v for k, v in agg.items() if not k.startswith("curve_")},
                "times": br.times,
                "curve_mean": agg["curve_mean"],
                "curve_p05": agg["curve_p05"],
                "curve_p95": agg["curve_p95"],
                "per_episode": [
                    {k: m[k] for k in ("T50", "T90", "T95", "T99", "final_ratio", "depletion_by_stage", "n_eff")}
                    for m in br.episodes
                ],
                "reference": compare_to_reference(figure, panel, name, br, spec["x_max"]),
            }
            progress(f"{figure} {panel} {name}: {episodes} episodes in {time.time() - t0:.1f}s, T99={_fmt(agg['T99'])}")
        pdata["validation"] = panel_validation(figure, pdata)
        out["panels"][panel] = pdata
    if figure == "figure5":
        out["table_iv"] = table_iv(out)
    return out


def _fmt(v):
    return "n/a" if not v else f"{v['mean']:.1f}"


def _mean(curve: dict, key: str):
    v = curve["aggregate"].get(key)
    return v["mean"] if v else None


def panel_validation(figure: str, pdata: dict) -> dict:
    c = pdata["curves"]
    out = {}
    if "aperiodic" in c and "periodic_Ng4" in c:
        a, p = _mean(c["aperiodic"], "T99"), _mean(c["periodic_Ng4"], "T99")
        if a and p:
            out["t99_reduction_vs_periodic_Ng4_pct"] = 100.0 * (1 - a / p)
        if figure == "figure5":
            tgt = scalar_targets()["single_source"]["t99_reduction_vs_periodic_ng4_pct"]
            out["paper_t99_reduction_pct"] = tgt["L16" if pdata["L"] == 16 else "L1"]
    if "aperiodic" in c:
        out["aperiodic_midround_depletion_mean"] = _mean(c["aperiodic"], "depletion_total")
    order = sorted((k for k in c if _mean(c[k], "T99")), key=lambda k: _mean(c[k], "T99"))
    out["t99_order"] = order
    return out


def table_iv(fig5: dict) -> list[dict]:
    rows = []
    for ref in table4():
        panel = "a_L16" if ref["L"] == 16 else "b_L1"
        name = "aperiodic" if ref["protocol"] == "aperiodic" else f"periodic_Ng{ref['N_g']}"
        c = fig5["panels"].get(panel, {}).get("curves", {}).get(name)
        if not c:
            continue
        sim = c["aggregate"]["depletion_by_stage"]
        sim_row = {k: sim[k] for k in ("paging", "msg1", "EI", "msg2", "msg3")}
        sim_row["total"] = sum(sim_row.values())
        rows.append({"protocol": ref["protocol"], "L": ref["L"], "N_g": ref["N_g"], "simulated": sim_row, "paper": ref})
    return rows


def figure4_data(n_tot: int = 15000, seed: int = 0) -> dict:
    s = SystemParams()
    out = {"n_tot": n_tot, "seed": seed, "scenarios": {}}
    for scen in HarvestingScenario:
        pop = build_population(n_tot, np.random.default_rng(np.random.SeedSequence(seed).spawn(6)[0]), scen)
        ref = reference_curve("figure4", scen.value)
        cdf = incident_power_cdf(pop)
        entry = {
            "n_eff": pop.n_eff,
            "type_shares": pop.type_shares(),
            "type_counts": pop.type_counts(),
            "cdf": cdf,
            "harvest_below_sleep": harvest_below_sleep_stats(pop, s.p_sl_w),
            "paper_n_eff": scalar_targets()[scen.value]["n_eff"],
            "paper_type_shares_pct": scalar_targets()[scen.value]["type_shares_pct"],
        }
        if ref is not None:
            rx, ry = ref
            sim_x = np.asarray(cdf["pin_dbm"])
            sim_y = np.asarray(cdf["cdf"])
            # Horizontal distance (dBm) between the CDFs at common quantiles.
            q = np.linspace(0.02, 0.98, 49)
            ry_m = np.maximum.accumulate(ry)
            ref_q = np.interp(q, ry_m, rx)
            sim_q = np.interp(q, sim_y, sim_x)
            entry["paper_cdf_quantile_gap_db"] = {
                "mean_abs": float(np.mean(np.abs(sim_q - ref_q))),
                "max_abs": float(np.max(np.abs(sim_q - ref_q))),
            }
        out["scenarios"][scen.value] = entry
    return out


SLIM_STRIDE = 4


def slim_figure(data: dict) -> dict:
    """JSON form: curves at 2 s resolution (full resolution goes to CSV).

    ``paper_reference`` holds the extracted paper curves for overlay only.
    """
    slim = _jsonable(data)
    for panel, p in slim["panels"].items():
        for name, c in p["curves"].items():
            c.pop("times", None)
            for k in ("curve_mean", "curve_p05", "curve_p95"):
                c[k] = c[k][::SLIM_STRIDE]
            c["curve_step_s"] = CURVE_STEP_S * SLIM_STRIDE
            ref = reference_curve(data["figure"], f"{panel}_{name}")
            c["paper_reference"] = {"x": ref[0].tolist(), "y": ref[1].tolist()} if ref is not None else None
    return slim


def write_figure_outputs(data: dict, out_dir: Path, plot: bool = True) -> list[Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    fig = data["figure"]
    files = []
    jpath = out_dir / f"{fig}.json"
    jpath.write_text(json.dumps(slim_figure(data), indent=1))
    files.append(jpath)
    for panel, p in data["panels"].items():
        names = list(p["curves"])
        t = p["curves"][names[0]]["times"]
        cols = [t] + [p["curves"][n]["curve_mean"] for n in names]
        cpath = out_dir / f"{fig}_{panel}.csv"
        np.savetxt(cpath, np.column_stack(cols), delimiter=",", header="time_s," + ",".join(names), comments="", fmt="%.4f")
        files.append(cpath)
    if plot:
        files.append(plot_protocol_figure(data, out_dir / f"{fig}.png"))
    return files


COLORS = {
    "aperiodic": "#edb120",
    "periodic_Ng1": "#77ac30",
    "periodic_Ng1_wo_depletion": "#7e2f8e",
    "periodic_Ng4": "#d95319",
    "periodic_Ng4_wo_depletion": "#0072bd",
}


def plot_protocol_figure(data: dict, path: Path) -> Path:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig = data["figure"]
    x_max = FIGURES[fig]["x_max"]
    panels = data["panels"]
    f, axes = plt.subplots(len(panels), 1, figsize=(7, 3.2 * len(panels)), sharex=True, squeeze=False)
    for ax, (panel, p) in zip(axes[:, 0], panels.items()):
        for name, c in p["curves"].items():
            ax.plot(c["times"], c["curve_mean"], color=COLORS[name], lw=2, label=f"sim: {c['label']}")
            ax.fill_between(c["times"], c["curve_p05"], c["curve_p95"], color=COLORS[name], alpha=0.12, lw=0)
            ref = reference_curve(fig, f"{panel}_{name}")
            if ref is not None:
                ax.plot(ref[0], ref[1], color=COLORS[name], lw=1.2, ls="--")
        ax.set_xlim(0, x_max)
        ax.set_ylim(0, 100)
        ax.grid(alpha=0.3)
        num = fig.removeprefix("figure")
        ax.set_title(f"Paper Fig. {num}({panel[0]}): L = {p['L']}  —  solid: simulation mean (5–95% band), dashed: paper", fontsize=9)
        ax.set_ylabel("Inventoried ratio (%)")
        ax.legend(fontsize=7, loc="lower right")
    axes[-1, 0].set_xlabel("Time [s]")
    f.suptitle(f"{PAPER_CAPTIONS[fig]}\nN_tot={data['n_tot']}, {data['episodes']} episodes", fontsize=10)
    f.tight_layout()
    f.savefig(path, dpi=130)
    plt.close(f)
    return path


def plot_figure4(data: dict, path: Path) -> Path:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    f, ax = plt.subplots(figsize=(6, 4))
    col = {"single_source": "#0072bd", "multi_source": "#d95319"}
    for scen, e in data["scenarios"].items():
        ax.plot(e["cdf"]["pin_dbm"], e["cdf"]["cdf"], color=col[scen], lw=2, label=f"sim: {scen}")
        ref = reference_curve("figure4", scen)
        if ref is not None:
            ax.plot(ref[0], ref[1], color=col[scen], ls="--", lw=1.2, label=f"paper: {scen}")
    ax.set_xlim(-36, -16)
    ax.set_xlabel("P_in [dBm]")
    ax.set_ylabel("CDF")
    ax.grid(alpha=0.3)
    ax.legend(fontsize=8)
    ax.set_title(PAPER_CAPTIONS["figure4"], fontsize=9)
    f.tight_layout()
    f.savefig(path, dpi=130)
    plt.close(f)
    return path
