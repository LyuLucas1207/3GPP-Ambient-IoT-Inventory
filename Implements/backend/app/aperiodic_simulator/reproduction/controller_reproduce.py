"""Controller-level reproduction (Figures 7, 8 and Tables V, VI).

The protocol is fixed to the proposed aperiodic framework; only the
controller changes. Every method of a comparison uses the same seed sequence
``base_seed + i`` (same layouts, availability and impairment draws).

Recurrent PPO results come from the verified checkpoint for the requested
alpha. If a checkpoint is missing, that method is reported as unavailable,
never substituted. An under-trained checkpoint is flagged in ``checkpoints``.
"""

import json
import time
from pathlib import Path

import numpy as np

from app.aperiodic_simulator.core.batch import run_batch
from app.aperiodic_simulator.core.config import EpisodeConfig
from app.aperiodic_simulator.analysis.metrics import CURVE_STEP_S
from app.aperiodic_simulator.analysis.reference_targets import (
    PAPER_CAPTIONS,
    curve_t_targets,
    reference_curve,
    results_dir,
    scalar_targets,
    table5,
    table6,
)
from app.aperiodic_simulator.reproduction.reproduce import _jsonable
from app.aperiodic_simulator.rl.checkpoint import CheckpointMissing, load_meta
from app.aperiodic_simulator.core.states import ControllerName, HarvestingScenario, PagingMode
from app.common.metrics import mae_rmse

T_MAX_S = 1500.0
FIG7_T_CURVE_S = 300.0
SLIM_STRIDE = 4
FIG8_N_TOT = tuple(range(1000, 15001, 1000))
TABLE5_N_TOT = (1000, 7500, 15000)
TABLE6_ALPHAS = (0.0, 0.25, 0.5, 0.75)
PFSA_L = (1, 8, 32)

LABELS = {
    "recurrent_ppo": "RL (Recurrent PPO)",
    "dfsa_schoute": "DFSA-Schoute",
    "cmebe": "CMEBE",
    "pfsa_L1": "PFSA, L_s = 1",
    "pfsa_L8": "PFSA, L_s = 8",
    "pfsa_L32": "PFSA, L_s = 32",
}


def _base(scenario: HarvestingScenario, n_tot: int, alpha: float = 0.5) -> EpisodeConfig:
    return EpisodeConfig(
        n_tot=n_tot, harvesting_scenario=scenario, paging_mode=PagingMode.APERIODIC, alpha=alpha, t_max_s=T_MAX_S, p_initial=1.0
    )


def _ppo_factory(alpha: float):
    from app.aperiodic_simulator.controllers.recurrent_ppo import ppo_controller_factory

    return ppo_controller_factory(alpha)


def checkpoint_summary(alphas=TABLE6_ALPHAS) -> dict:
    out = {}
    for a in alphas:
        try:
            m = load_meta(a)
            out[str(a)] = {
                "available": True,
                "training_steps": m["training_steps"],
                "paper_training_steps": 1_000_000,
                "fully_trained": m["training_steps"] >= 1_000_000,
                "sha256": m["sha256"],
                "seed": m["seed"],
            }
        except CheckpointMissing as exc:
            out[str(a)] = {"available": False, "reason": str(exc)}
    return out


def method_batch(method: str, scenario, n_tot: int, episodes: int, base_seed: int, workers, alpha: float = 0.5, t_curve=None):
    """Run one method; returns BatchResult or raises CheckpointMissing for RL."""
    cfg = _base(scenario, n_tot, alpha)
    factory = None
    if method == "recurrent_ppo":
        cfg = cfg.with_(controller=ControllerName.RECURRENT_PPO, L_initial=1, L_fixed=1)
        factory = _ppo_factory(alpha)
    elif method in ("dfsa_schoute", "cmebe"):
        cfg = cfg.with_(controller=ControllerName(method), L_initial=1, L_fixed=1)
    elif method.startswith("pfsa_L"):
        cfg = cfg.with_(controller=ControllerName.PFSA_PZE, L_fixed=int(method[len("pfsa_L"):]))
    else:
        raise ValueError(method)
    return run_batch(cfg, episodes, base_seed, label=method, workers=workers, t_curve=t_curve, controller_factory=factory)


def _stat(agg: dict, key: str, scale: float = 1.0):
    v = agg.get(key)
    if not v:
        return None
    return {k: v[k] * scale if k in ("mean", "std", "ci95", "p05", "p50", "p95") else v[k] for k in v}


# ----------------------------------------------------------------- Figure 7
def figure7(episodes: int, base_seed: int = 0, workers=None, n_tot: int = 15000, progress=print) -> dict:
    scen = HarvestingScenario.MULTI_SOURCE
    curves, unavailable = {}, {}
    for name in ("recurrent_ppo", "dfsa_schoute", "cmebe"):
        t0 = time.time()
        try:
            br = method_batch(name, scen, n_tot, episodes, base_seed, workers, t_curve=FIG7_T_CURVE_S)
        except CheckpointMissing as exc:
            unavailable[name] = str(exc)
            progress(f"figure7 {name}: unavailable ({exc})")
            continue
        agg = br.aggregate
        ref = reference_curve("figure7", name)
        reference = {}
        if ref is not None:
            m = br.times <= min(FIG7_T_CURVE_S, ref[0].max())
            reference = {"paper_T": curve_t_targets(*ref), **mae_rmse(br.times[m], agg["curve_mean"][m], *ref)}
        curves[name] = {
            "label": LABELS[name],
            "aggregate": {k: v for k, v in agg.items() if not k.startswith("curve_")},
            "times": br.times,
            "curve_mean": agg["curve_mean"],
            "curve_p05": agg["curve_p05"],
            "curve_p95": agg["curve_p95"],
            "reference": reference,
        }
        progress(f"figure7 {name}: {episodes} episodes in {time.time() - t0:.1f}s, T_total={_fmt(agg, 'T_total_s')}")
    validation = {}
    tt = {k: c["aggregate"]["T_total_s"]["mean"] for k, c in curves.items() if c["aggregate"].get("T_total_s")}
    mean_id = {k: c["aggregate"]["mean_identification_time_s"]["mean"] for k, c in curves.items() if c["aggregate"].get("mean_identification_time_s")}
    dfsa = {k: v for k, v in tt.items() if k != "recurrent_ppo"}
    if dfsa:
        best = min(dfsa, key=dfsa.get)
        validation["best_dfsa_baseline"] = best
        validation["paper_best_dfsa_baseline"] = "cmebe"
        if "recurrent_ppo" in tt:
            validation["rl_total_time_reduction_vs_best_dfsa_pct"] = 100.0 * (1 - tt["recurrent_ppo"] / dfsa[best])
            if "recurrent_ppo" in mean_id and best in mean_id:
                validation["rl_mean_id_time_reduction_vs_best_dfsa_pct"] = 100.0 * (1 - mean_id["recurrent_ppo"] / mean_id[best])
    validation["paper_rl_reduction_vs_cmebe_pct"] = scalar_targets()["figure7"]["rl_vs_cmebe_mean_time_reduction_pct"]
    return {
        "figure": "figure7",
        "scenario": scen.value,
        "n_tot": n_tot,
        "episodes": episodes,
        "base_seed": base_seed,
        "L_initial": 1,
        "panels": {"multi_source": {"L": None, "curves": curves, "validation": validation}},
        "unavailable": unavailable,
        "checkpoints": checkpoint_summary((0.5,)),
    }


# ----------------------------------------------------------------- Figure 8
def figure8(episodes: int, base_seed: int = 0, workers=None, n_grid=FIG8_N_TOT, progress=print) -> dict:
    scen = HarvestingScenario.MULTI_SOURCE
    series, unavailable = {}, {}
    for name in ("recurrent_ppo", "pfsa_L1", "pfsa_L8", "pfsa_L32"):
        rows = []
        for n in n_grid:
            try:
                br = method_batch(name, scen, n, episodes, base_seed, workers, t_curve=1.0)
            except CheckpointMissing as exc:
                unavailable[name] = str(exc)
                break
            a = br.aggregate
            rows.append({"n_tot": n, "re_pct": _stat(a, "resource_efficiency", 100.0), "T_total_s": _stat(a, "T_total_s"), "incomplete": a["episodes_incomplete"]})
        if not rows:
            progress(f"figure8 {name}: unavailable")
            continue
        ref = reference_curve("figure8", name)
        paper = None
        if ref is not None:
            paper = {"n_tot": (ref[0] * 1000).round().astype(int).tolist(), "re_pct": ref[1].tolist()}
        sim_x = np.array([r["n_tot"] for r in rows], dtype=float)
        sim_y = np.array([r["re_pct"]["mean"] for r in rows])
        err = mae_rmse(sim_x, sim_y, np.array(paper["n_tot"], dtype=float), np.array(paper["re_pct"])) if paper else {}
        series[name] = {"label": LABELS[name], "points": rows, "paper_reference": paper, "reference": err}
        progress(f"figure8 {name}: RE " + " ".join(f"{r['n_tot'] // 1000}k={r['re_pct']['mean']:.1f}" for r in rows))
    return {
        "figure": "figure8",
        "scenario": scen.value,
        "episodes": episodes,
        "base_seed": base_seed,
        "series": series,
        "unavailable": unavailable,
        "checkpoints": checkpoint_summary((0.5,)),
    }


# ----------------------------------------------------------------- Tables V / VI
def table_v(episodes: int, base_seed: int = 0, workers=None, progress=print) -> list[dict]:
    rows = []
    for ref in table5():
        scen = HarvestingScenario(ref["scenario"])
        for method in ("recurrent_ppo", *(f"pfsa_L{L}" for L in PFSA_L)):
            paper = ref[method]
            row = {"scenario": scen.value, "n_tot": ref["n_tot"], "method": method, "paper_s": paper}
            try:
                br = method_batch(method, scen, ref["n_tot"], episodes, base_seed, workers, t_curve=1.0)
            except CheckpointMissing as exc:
                rows.append({**row, "available": False, "reason": str(exc)})
                continue
            st = _stat(br.aggregate, "T_total_s")
            row.update(
                available=True,
                sim_s=st["mean"] if st else None,
                ci95_s=st["ci95"] if st else None,
                rel_err_pct=100.0 * (st["mean"] - paper) / paper if st else None,
                incomplete=br.aggregate["episodes_incomplete"],
            )
            rows.append(row)
            progress(f"Table V {scen.value} N={ref['n_tot']} {method}: sim {_fmt(br.aggregate, 'T_total_s')} | paper {paper}")
    return rows


def table_vi(episodes: int, base_seed: int = 0, workers=None, n_tot: int = 15000, progress=print) -> list[dict]:
    rows = []
    for ref in table6():
        alpha = ref["alpha"]
        for scen, tkey, rkey in (
            (HarvestingScenario.MULTI_SOURCE, "multi_time_s", "multi_re_pct"),
            (HarvestingScenario.SINGLE_SOURCE, "single_time_s", "single_re_pct"),
        ):
            row = {"alpha": alpha, "scenario": scen.value, "paper_time_s": ref[tkey], "paper_re_pct": ref[rkey]}
            try:
                br = method_batch("recurrent_ppo", scen, n_tot, episodes, base_seed, workers, alpha=alpha, t_curve=1.0)
            except CheckpointMissing as exc:
                rows.append({**row, "available": False, "reason": str(exc)})
                progress(f"Table VI alpha={alpha} {scen.value}: checkpoint unavailable")
                continue
            a = br.aggregate
            t, r = _stat(a, "T_total_s"), _stat(a, "resource_efficiency", 100.0)
            row.update(
                available=True,
                sim_time_s=t["mean"] if t else None,
                sim_time_ci95_s=t["ci95"] if t else None,
                sim_re_pct=r["mean"] if r else None,
                incomplete=a["episodes_incomplete"],
            )
            rows.append(row)
            progress(f"Table VI alpha={alpha} {scen.value}: time {_fmt(a, 'T_total_s')} RE {r['mean']:.1f}% | paper {ref[tkey]} / {ref[rkey]}%")
    return rows


def tables(episodes: int, base_seed: int = 0, workers=None, progress=print) -> dict:
    return {
        "figure": "tables",
        "episodes": episodes,
        "base_seed": base_seed,
        "table_v": table_v(episodes, base_seed, workers, progress),
        "table_vi": table_vi(episodes, base_seed, workers, progress=progress),
        "checkpoints": checkpoint_summary(),
        "metric": "T_total_s = time until all N_eff devices are identified (Eq. 4), mean over episodes",
    }


def _fmt(agg: dict, key: str) -> str:
    v = agg.get(key)
    return "n/a" if not v else f"{v['mean']:.1f}"


# ----------------------------------------------------------------- output
def slim(data: dict) -> dict:
    out = _jsonable(data)
    if out.get("figure") == "figure7":
        for name, c in out["panels"]["multi_source"]["curves"].items():
            c.pop("times", None)
            for k in ("curve_mean", "curve_p05", "curve_p95"):
                c[k] = c[k][::SLIM_STRIDE]
            c["curve_step_s"] = CURVE_STEP_S * SLIM_STRIDE
            ref = reference_curve("figure7", name)
            c["paper_reference"] = {"x": ref[0].tolist(), "y": ref[1].tolist()} if ref is not None else None
    return out


def cached_episodes(path: Path) -> int:
    try:
        return int(json.loads(path.read_text()).get("episodes", 0))
    except (OSError, ValueError):
        return 0


def write_outputs(data: dict, plot: bool = True, force: bool = False) -> list[Path]:
    """Write JSON (+PNG); never replace a cached result computed with more episodes unless forced."""
    fig = data["figure"]
    out_dir = results_dir() / fig
    out_dir.mkdir(parents=True, exist_ok=True)
    jpath = out_dir / f"{fig}.json"
    if not force and cached_episodes(jpath) > data["episodes"]:
        return []
    jpath.write_text(json.dumps(slim(data), indent=1))
    files = [jpath]
    if plot and fig == "figure7":
        files.append(plot_figure7(data, out_dir / "figure7.png"))
    if plot and fig == "figure8":
        files.append(plot_figure8(data, out_dir / "figure8.png"))
    return files


COLORS = {"recurrent_ppo": "#0072bd", "dfsa_schoute": "#d95319", "cmebe": "#edb120", "pfsa_L1": "#d95319", "pfsa_L8": "#edb120", "pfsa_L32": "#7e2f8e"}


def _plt():
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    return plt


def plot_figure7(data: dict, path: Path) -> Path:
    plt = _plt()
    f, ax = plt.subplots(figsize=(7, 4))
    for name, c in data["panels"]["multi_source"]["curves"].items():
        ax.plot(c["times"], c["curve_mean"], color=COLORS[name], lw=2, label=f"sim: {c['label']}")
        ax.fill_between(c["times"], c["curve_p05"], c["curve_p95"], color=COLORS[name], alpha=0.12, lw=0)
        ref = reference_curve("figure7", name)
        if ref is not None:
            ax.plot(ref[0], ref[1], color=COLORS[name], lw=1.2, ls="--")
    ax.set_xlim(0, 200)
    ax.set_ylim(0, 100)
    ax.grid(alpha=0.3)
    ax.set_xlabel("Time [s]")
    ax.set_ylabel("Inventoried ratio (%)")
    ax.legend(fontsize=8, loc="lower right")
    ck = data["checkpoints"].get("0.5", {})
    note = f"RL checkpoint: {ck.get('training_steps')} steps" if ck.get("available") else "RL checkpoint unavailable"
    ax.set_title(f"{PAPER_CAPTIONS['figure7']}\nN_tot={data['n_tot']}, {data['episodes']} episodes; dashed: paper; {note}", fontsize=8)
    f.tight_layout()
    f.savefig(path, dpi=130)
    plt.close(f)
    return path


def plot_figure8(data: dict, path: Path) -> Path:
    plt = _plt()
    f, ax = plt.subplots(figsize=(7, 4))
    for name, s in data["series"].items():
        x = [p["n_tot"] / 1000 for p in s["points"]]
        y = [p["re_pct"]["mean"] for p in s["points"]]
        ax.plot(x, y, "o-", color=COLORS[name], lw=1.8, ms=3, label=f"sim: {s['label']}")
        if s["paper_reference"]:
            ax.plot(np.array(s["paper_reference"]["n_tot"]) / 1000, s["paper_reference"]["re_pct"], color=COLORS[name], ls="--", lw=1.2)
    ax.set_xlabel("N_tot [×10³]")
    ax.set_ylabel("Average resource efficiency [%]")
    ax.grid(alpha=0.3)
    ax.legend(fontsize=8)
    ax.set_title(f"{PAPER_CAPTIONS['figure8']}\nmulti-source, {data['episodes']} episodes per point; dashed: paper", fontsize=8)
    f.tight_layout()
    f.savefig(path, dpi=130)
    plt.close(f)
    return path


def compute_controller_target(target: str, episodes: int, base_seed: int = 0, workers=None, progress=print) -> dict:
    if target == "figure7":
        data = figure7(episodes, base_seed, workers, progress=progress)
    elif target == "figure8":
        data = figure8(episodes, base_seed, workers, progress=progress)
    elif target == "tables":
        data = tables(episodes, base_seed, workers, progress=progress)
    else:
        raise ValueError(target)
    write_outputs(data)
    return slim(data)
