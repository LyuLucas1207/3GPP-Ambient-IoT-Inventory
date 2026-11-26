"""Generalization matrix: policies x test deployments, against the DFSA baseline.

Each test cell fixes (active readers, resource policy, start offsets); every
candidate (trained policies, ``dfsa``) runs the same seeded episodes, so cells
are paired. Comparing a randomized policy with policies trained on one
configuration each (``ps_ppo_fixed2`` ...) gives the "train once vs retrain
per configuration" comparison.

    python -m training.evaluate --runs training/outputs/ps_ppo_randomized/<run> training/outputs/mappo/<run> \
        --grid standard --episodes 3 --out training/outputs/_eval/<name>

``train.py`` calls ``evaluate_run`` for each trained job (written to the run's
``eval_matrix.csv``).
"""

from __future__ import annotations

import argparse
import itertools
import math
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
from typing import Any

from training.common import CsvLog, OUTPUTS_DIR, load_config, utc_stamp, write_json

EVAL_GRIDS: dict[str, dict[str, list]] = {
    "mini": {"readers": [2], "resource_modes": ["independent"], "offsets": ["none"]},
    "standard": {"readers": [2, 6, 18], "resource_modes": ["independent", "fdma", "tdma"], "offsets": ["none", "groups"]},
    "full": {"readers": [2, 6, 12, 18], "resource_modes": ["independent", "fdma", "tdma", "hybrid", "lbt"], "offsets": ["none", "groups", "random"]},
}
METRICS = ("identified_fraction", "t99", "t_mean", "resource_efficiency", "sim_time")


def cells(grid: str | dict) -> list[dict[str, Any]]:
    g = EVAL_GRIDS[grid] if isinstance(grid, str) else grid
    return [{"readers": n, "resource": m, "offsets": o} for n, m, o in itertools.product(g["readers"], g["resource_modes"], g["offsets"])]


def cell_id(c: dict[str, Any]) -> str:
    return f"R{c['readers']}_{c['resource']}_{c['offsets']}"


def run_episode(candidate: dict[str, Any], cell: dict[str, Any], env_cfg: dict[str, Any], seed: int) -> dict[str, Any]:
    """One seeded episode of ``candidate`` (``{"kind": "dfsa"}`` or ``{"kind": "policy", "meta_path": ...}``)."""
    import numpy as np

    from app.simulator_thesis.inventory.episode import build_episode, mark_unreachable
    from app.simulator_thesis.inventory.headless import drive
    from app.simulator_thesis.inventory.events import EventEmitter
    from app.simulator_thesis.rl.env import MultiReaderInventoryEnv, outcome

    spec = {**env_cfg, "readers": [cell["readers"], cell["readers"]], "resource_modes": [cell["resource"]], "offsets": [cell["offsets"]],
            "subset": "spread"}
    sampler = MultiReaderInventoryEnv(spec)
    sampler.np_random = np.random.default_rng(seed)  # the deployment depends only on (cell, seed)
    scene, config, _ = sampler.sample_deployment(sampler.cfg)
    state = build_episode(scene, config, np.random.default_rng(seed + 7919))
    if candidate["kind"] == "policy":
        from app.simulator_thesis.rl.policy import PolicyController, load_meta, load_meta_file

        meta = load_meta(candidate["policy_id"]) if candidate.get("policy_id") else load_meta_file(Path(candidate["meta_path"]))
        for r in state.readers:
            r.controller = PolicyController.from_meta(meta)
    emit = EventEmitter(run_id=0)
    mark_unreachable(state, emit)
    emit.discard()
    tally = {"s": 0, "k": 0}

    def on_frame(_st, res) -> None:
        tally["s"] += res.success
        tally["k"] += res.k

    drive(state, keep_rounds=False, max_frames=int(env_cfg.get("max_frames", 20_000)), on_frame=on_frame)
    return outcome(state, tally["s"], tally["k"])


def _task(args):
    name, candidate, cell, env_cfg, seed = args
    out = run_episode(candidate, cell, env_cfg, seed)
    return {"candidate": name, "cell": cell_id(cell), **cell, "seed": seed, **out}


def evaluate(candidates: dict[str, dict[str, Any]], grid: str | dict, episodes: int, env_cfg: dict[str, Any], *,
             seed0: int = 10_000, jobs: int = 1) -> list[dict[str, Any]]:
    tasks = [(name, cand, c, env_cfg, seed0 + e) for c in cells(grid) for e in range(episodes) for name, cand in candidates.items()]
    if jobs > 1:
        with ProcessPoolExecutor(jobs) as ex:
            return list(ex.map(_task, tasks))
    return [_task(t) for t in tasks]


def matrix(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Mean per (candidate, cell) plus the ratio of T_99 to DFSA in the same cell."""
    groups: dict[tuple[str, str], list[dict]] = {}
    for r in rows:
        groups.setdefault((r["candidate"], r["cell"]), []).append(r)
    out = []
    for (cand, cell), rs in sorted(groups.items()):
        row = {"candidate": cand, "cell": cell, "readers": rs[0]["readers"], "resource": rs[0]["resource"], "offsets": rs[0]["offsets"], "episodes": len(rs)}
        for m in METRICS:
            vals = [x[m] for x in rs if x.get(m) is not None]
            row[m] = sum(vals) / len(vals) if vals and len(vals) == len(rs) else None
        out.append(row)
    base = {r["cell"]: r for r in out if r["candidate"] == "dfsa"}
    for r in out:
        b = base.get(r["cell"])
        r["t99_vs_dfsa"] = (r["t99"] / b["t99"]) if b and r["t99"] and b["t99"] else None
        r["t_mean_vs_dfsa"] = (r["t_mean"] / b["t_mean"]) if b and r["t_mean"] and b["t_mean"] else None
    return out


def write_matrix(rows: list[dict[str, Any]], out_dir: Path) -> list[dict[str, Any]]:
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "plots").mkdir(exist_ok=True)
    for name in ("eval_episodes.csv", "eval_matrix.csv"):
        (out_dir / name).unlink(missing_ok=True)
    ep = CsvLog(out_dir / "eval_episodes.csv")
    for r in rows:
        ep.write(r)
    mat = matrix(rows)
    mlog = CsvLog(out_dir / "eval_matrix.csv")
    for r in mat:
        mlog.write(r)
    plot_heatmap(mat, out_dir / "plots" / "eval_heatmap.png")
    return mat


def plot_heatmap(mat: list[dict[str, Any]], path: Path) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np

    cands = sorted({r["candidate"] for r in mat if r["candidate"] != "dfsa"})
    cell_ids = sorted({r["cell"] for r in mat}, key=lambda c: (int(c.split("_")[0][1:]), c))
    if not cands or not cell_ids:
        return
    z = np.full((len(cands), len(cell_ids)), np.nan)
    for r in mat:
        if r["candidate"] in cands and r["t99_vs_dfsa"] is not None:
            z[cands.index(r["candidate"]), cell_ids.index(r["cell"])] = r["t99_vs_dfsa"]
    fig, ax = plt.subplots(figsize=(max(6, 0.55 * len(cell_ids) + 2), 0.6 * len(cands) + 2.2))
    lim = np.nanmax(np.abs(np.log2(z))) if np.isfinite(z).any() else 1.0
    im = ax.imshow(np.log2(z), cmap="RdYlGn_r", vmin=-max(lim, 0.1), vmax=max(lim, 0.1), aspect="auto")
    for i in range(z.shape[0]):
        for j in range(z.shape[1]):
            if math.isfinite(z[i, j]):
                ax.text(j, i, f"{z[i, j]:.2f}", ha="center", va="center", fontsize=7)
    ax.set_xticks(range(len(cell_ids)), cell_ids, rotation=60, ha="right", fontsize=7)
    ax.set_yticks(range(len(cands)), cands, fontsize=8)
    ax.set_title("T99 relative to DFSA (lower is better, NaN = 99% not reached)")
    fig.colorbar(im, ax=ax, label="log2(T99 / T99_DFSA)")
    fig.tight_layout()
    fig.savefig(path, dpi=130)
    plt.close(fig)


def evaluate_run(run_dir: Path, env_cfg: dict[str, Any], grid: str, episodes: int, jobs: int = 1) -> dict[str, Any]:
    meta_path = run_dir / "checkpoints" / "final.json"
    rows = evaluate({"policy": {"kind": "policy", "meta_path": str(meta_path)}, "dfsa": {"kind": "dfsa"}}, grid, episodes, env_cfg, jobs=jobs)
    mat = write_matrix(rows, run_dir)
    return summarize(mat)


def summarize(mat: list[dict[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for cand in sorted({r["candidate"] for r in mat}):
        rs = [r for r in mat if r["candidate"] == cand]
        ratios = [r["t99_vs_dfsa"] for r in rs if r["t99_vs_dfsa"] is not None]
        out[cand] = {
            "cells": len(rs),
            "cells_reaching_99": sum(r["t99"] is not None for r in rs),
            "mean_identified_fraction": sum(r["identified_fraction"] or 0 for r in rs) / len(rs),
            "geo_mean_t99_vs_dfsa": math.exp(sum(math.log(x) for x in ratios) / len(ratios)) if ratios else None,
            "mean_resource_efficiency": _mean([r["resource_efficiency"] for r in rs]),
        }
    return out


def _mean(xs):
    xs = [x for x in xs if x is not None]
    return sum(xs) / len(xs) if xs else None


def _candidate_for(path_or_id: str) -> tuple[str, dict[str, Any]]:
    p = Path(path_or_id)
    if p.is_dir():
        meta = p / "checkpoints" / "final.json"
        return f"{p.parent.name}/{p.name.split('__', 1)[-1]}", {"kind": "policy", "meta_path": str(meta)}
    return path_or_id, {"kind": "policy", "policy_id": path_or_id}


def main(argv: list[str] | None = None) -> None:
    from training.scales import resolve_scale

    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--runs", nargs="*", default=[], help="training run directories or registry policy ids")
    ap.add_argument("--grid", default="standard", choices=sorted(EVAL_GRIDS))
    ap.add_argument("--episodes", type=int, default=3)
    ap.add_argument("--scale", default="small", help="device range / time cap of the test episodes (training.scales)")
    ap.add_argument("--config", default=None, help="take env settings (alpha, schemes, ...) from this training config")
    ap.add_argument("--jobs", type=int, default=1)
    ap.add_argument("--no-dfsa", action="store_true")
    ap.add_argument("--out", default=None)
    a = ap.parse_args(argv)
    scale = resolve_scale(a.scale)
    env_cfg = {"n_devices": list(scale.n_devices), "t_max_s": scale.t_max_s, "max_frames": scale.max_frames,
               "stall_timeout_s": scale.t_max_s}
    if a.config:
        env_cfg = {**load_config(a.config).get("env", {}), **env_cfg}
    cands = dict(_candidate_for(r) for r in a.runs)
    if not a.no_dfsa:
        cands["dfsa"] = {"kind": "dfsa"}
    out = Path(a.out) if a.out else OUTPUTS_DIR / "_eval" / utc_stamp()
    rows = evaluate(cands, a.grid, a.episodes, env_cfg, jobs=a.jobs)
    mat = write_matrix(rows, out)
    write_json(out / "summary.json", {"grid": a.grid, "episodes": a.episodes, "scale": scale.to_json(), "candidates": cands, "summary": summarize(mat)})
    print(f"wrote {out}/eval_matrix.csv ({len(mat)} rows)")
    for name, s in summarize(mat).items():
        print(f"  {name:40s} reach99 {s['cells_reaching_99']}/{s['cells']}  T99/DFSA {s['geo_mean_t99_vs_dfsa']}")


if __name__ == "__main__":
    main()
