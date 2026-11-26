"""Train multi-reader inventory policies.

    cd Implements/backend
    .venv/bin/python -m training.train --config ps_ppo_randomized --scale small
    .venv/bin/python -m training.train --config mappo --scale 0.25 --seeds 0 1 2 --jobs 3
    .venv/bin/python -m training.train --config ps_ppo_fixed2 --scale smoke --alphas 0.25 0.5 --promote

Every (alpha, beta, seed) of the config is one job, written to
``training/outputs/<experiment>/<UTC stamp>__a<alpha>__b<beta>__s<seed>/``:

    meta.json              status, timings, the sidecar below, evaluation summary
    checkpoints/final.zip  the policy (absent for zero_shot_single, which references the aperiodic zip)
    checkpoints/final.json registry sidecar: algo, alpha, beta, seed, scale, configs, specs, versions, SHA-256
    train_metrics.csv      one row per training episode (return, identified fraction, T99, resource efficiency)
    eval_matrix.csv        mean per test cell, policy vs DFSA (training.evaluate)
    eval_episodes.csv      every evaluation episode
    plots/                 learning_curve.png, eval_heatmap.png
    tb/                    TensorBoard logs (only when tensorboard is installed)

``--promote`` copies the checkpoint into the policy registry
(``app/thesis_simulator/rl/policies``) under its ``policy_id`` so runs can
select it (``controller = {"kind": "policy", "policy_id": ...}``).
"""

from __future__ import annotations

import argparse
import importlib
import os
import socket
import sys
import time
import traceback
from concurrent.futures import ProcessPoolExecutor
from datetime import datetime
from pathlib import Path
from typing import Any

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from training.common import (
    CsvLog,
    config_hash,
    git_commit,
    load_config,
    package_versions,
    policy_id,
    read_csv,
    run_dir,
    sha256_file,
    utc_stamp,
    write_json,
)
from training.scales import resolve_scale, with_overrides

ALGOS = {"ps_ppo": "training.algos.ps_ppo", "mappo": "training.algos.mappo", "ippo": "training.algos.independent",
         "zero_shot": "training.algos.zero_shot"}


def expand_jobs(cfg: dict[str, Any], scale: dict[str, Any], args: argparse.Namespace, stamp: str) -> list[dict[str, Any]]:
    alphas = args.alphas or cfg.get("alphas", [0.5])
    betas = args.betas or cfg.get("betas", [0.5])
    seeds = args.seeds if args.seeds is not None else cfg.get("seeds", [0])
    if cfg["algo"] not in ALGOS:
        raise SystemExit(f"unknown algo {cfg['algo']!r}; choose from {sorted(ALGOS)}")
    jobs = []
    for alpha in alphas:
        for beta in betas:
            for seed in seeds:
                env = {**cfg.get("env", {}), "alpha": float(alpha), "beta": float(beta), "n_devices": list(scale["n_devices"]),
                       "t_max_s": scale["t_max_s"], "stall_timeout_s": scale["t_max_s"], "max_frames": scale["max_frames"]}
                jobs.append({
                    "experiment": cfg["name"], "algo": cfg["algo"], "description": cfg.get("description"),
                    "alpha": float(alpha), "beta": float(beta), "seed": int(seed), "stamp": stamp, "scale": scale, "env": env,
                    "hyperparameters": cfg.get("hyperparameters", {}), "vec": args.vec,
                    "eval": None if args.no_eval else {"grid": scale["eval_grid"], "episodes": scale["eval_episodes"], "jobs": args.eval_jobs},
                    "promote": args.promote, "train_config": {k: v for k, v in cfg.items() if not k.startswith("_")},
                })
    return jobs


def plot_learning_curve(rows: list[dict[str, Any]], path: Path, title: str) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np

    if not rows:
        return
    x = np.array([r["timesteps"] for r in rows], dtype=float)
    fig, axes = plt.subplots(1, 3, figsize=(13, 3.6))
    for ax, key, label in zip(axes, ("return", "identified_fraction", "t99"), ("episode return", "identified fraction", "T99 [s]")):
        y = np.array([np.nan if r.get(key) is None else r[key] for r in rows], dtype=float)
        ax.plot(x, y, ".", alpha=0.3, ms=3)
        w = max(1, len(y) // 20)
        if len(y) >= w:
            ok = np.where(np.isfinite(y), y, 0.0)
            cnt = np.convolve(np.isfinite(y).astype(float), np.ones(w), "valid")
            ax.plot(x[w - 1:], np.convolve(ok, np.ones(w), "valid") / np.maximum(cnt, 1), lw=2)
        ax.set_xlabel("training steps (frames)")
        ax.set_title(label)
        ax.grid(alpha=0.3)
    fig.suptitle(title, fontsize=10)
    fig.tight_layout()
    fig.savefig(path, dpi=120)
    plt.close(fig)


def run_job(job: dict[str, Any]) -> dict[str, Any]:
    from app.thesis_simulator.rl.features import ACTION_SPEC, OBSERVATION_SPEC

    out = run_dir(job["experiment"], job["stamp"], job["alpha"], job["beta"], job["seed"])
    pid = policy_id(job["experiment"], job["alpha"], job["beta"], job["seed"], job["stamp"])
    base = {"policy_id": pid, "experiment": job["experiment"], "algo_config": job["algo"], "alpha": job["alpha"], "beta": job["beta"],
            "seed": job["seed"], "scale": job["scale"], "run_dir": str(out), "started_at": datetime.now().astimezone().isoformat(timespec="seconds")}
    write_json(out / "meta.json", {**base, "status": "running", "pid": os.getpid(), "host": socket.gethostname()})
    t0 = time.time()
    try:
        (out / "train_metrics.csv").unlink(missing_ok=True)
        log = CsvLog(out / "train_metrics.csv")
        art = importlib.import_module(ALGOS[job["algo"]]).train(job, out, log)
        sidecar = {
            "policy_id": pid,
            "algo": art["algo"],
            "experiment": job["experiment"],
            "description": job.get("description"),
            "alpha": job["alpha"],
            "beta": job["beta"],
            "seed": job["seed"],
            "scale": job["scale"]["name"],
            "scale_detail": job["scale"],
            "training_steps": art["training_steps"],
            "architecture": art.get("architecture"),
            "hyperparameters": art.get("hyperparameters"),
            "train_config": job["train_config"],
            "env": job["env"],
            "observation_spec": OBSERVATION_SPEC if art["algo"] != "zero_shot_aperiodic" else "Sources RL.py raw counts (S2b, S2a, S1, empty, collisions, K_prev, p_prev)",
            "action_spec": ACTION_SPEC if art["algo"] != "zero_shot_aperiodic" else {
                "policy_action_space": "Box([0.25, 0.1], [10, 10])",
                "K": "clip(round(m * K_prev), 2, 668)",
                "p": "clip(q * p_prev, 0.001, 1)",
            },
            "package_versions": package_versions(),
            "git_commit": git_commit(),
            "config_hash": config_hash({"train_config": job["train_config"], "env": job["env"], "scale": job["scale"]}),
            "created_at": datetime.now().astimezone().isoformat(timespec="seconds"),
            "wall_time_s": round(time.time() - t0, 1),
            "sha256": sha256_file(Path(art["artifact"])),
        }
        if art.get("source"):
            sidecar["source"] = art["source"]
        write_json(out / "checkpoints" / "final.json", sidecar)
        rows = read_csv(out / "train_metrics.csv")
        sidecar["training_episodes"] = len(rows)
        tail = [r["return"] for r in rows[-20:] if r.get("return") is not None]
        sidecar["mean_return_last20"] = sum(tail) / len(tail) if tail else None
        plot_learning_curve(rows, out / "plots" / "learning_curve.png", pid)
        if job["eval"]:
            from training.evaluate import evaluate_run

            sidecar["eval_summary"] = evaluate_run(out, job["env"], job["eval"]["grid"], job["eval"]["episodes"], job["eval"].get("jobs", 1))
        write_json(out / "checkpoints" / "final.json", sidecar)
        promoted = None
        if job["promote"]:
            from training.promote import promote

            promoted = promote(out)
        meta = {**base, **sidecar, "status": "done", "wall_time_total_s": round(time.time() - t0, 1), "promoted": promoted}
        write_json(out / "meta.json", meta)
        print(f"[done] {pid}  {meta['wall_time_total_s']} s  -> {out}", flush=True)
        return meta
    except Exception as exc:  # recorded so other jobs of the sweep continue
        meta = {**base, "status": "failed", "error": repr(exc), "traceback": traceback.format_exc(), "wall_time_total_s": round(time.time() - t0, 1)}
        write_json(out / "meta.json", meta)
        print(f"[failed] {pid}: {exc!r}", file=sys.stderr, flush=True)
        return meta


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--config", required=True, help="name in training/configs or a path to a json config")
    ap.add_argument("--scale", default="small", help="smoke | small | medium | full | <preset>:<factor> | <factor of full>")
    ap.add_argument("--alphas", type=float, nargs="*")
    ap.add_argument("--betas", type=float, nargs="*")
    ap.add_argument("--seeds", type=int, nargs="*")
    ap.add_argument("--steps", type=int, help="override total training steps")
    ap.add_argument("--n-envs", type=int)
    ap.add_argument("--n-devices", type=int, nargs=2, metavar=("LO", "HI"))
    ap.add_argument("--eval-episodes", type=int)
    ap.add_argument("--eval-grid", choices=["mini", "standard", "full"])
    ap.add_argument("--eval-jobs", type=int, default=1, help="processes per job for evaluation")
    ap.add_argument("--no-eval", action="store_true")
    ap.add_argument("--jobs", type=int, default=1, help="(alpha, beta, seed) jobs trained in parallel")
    ap.add_argument("--vec", choices=["dummy", "subproc"], default="dummy", help="vector env for ps_ppo")
    ap.add_argument("--promote", action="store_true", help="copy each finished checkpoint into the policy registry")
    a = ap.parse_args(argv)
    cfg = load_config(a.config)
    scale = with_overrides(resolve_scale(a.scale), steps=a.steps, n_envs=a.n_envs, eval_episodes=a.eval_episodes,
                           n_devices=tuple(a.n_devices) if a.n_devices else None, eval_grid=a.eval_grid).to_json()
    jobs = expand_jobs(cfg, scale, a, utc_stamp())
    print(f"{cfg['name']}: {len(jobs)} job(s), scale {scale['name']} ({scale['total_steps']} steps, {scale['n_envs']} env(s))", flush=True)
    if a.jobs > 1 and len(jobs) > 1:
        with ProcessPoolExecutor(min(a.jobs, len(jobs))) as ex:
            metas = list(ex.map(run_job, jobs))
    else:
        metas = [run_job(j) for j in jobs]
    failed = [m for m in metas if m["status"] != "done"]
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
