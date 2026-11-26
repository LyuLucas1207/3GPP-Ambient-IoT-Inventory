"""Read-only view of ``training/outputs`` for the API (experiments, runs, curves, matrices)."""

from __future__ import annotations

import csv
import json
import os
import re
import socket
from pathlib import Path
from typing import Any

BACKEND_ROOT = Path(__file__).resolve().parents[2]
_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.\-]*$")
PLOTS = ("learning_curve.png", "eval_heatmap.png")
MAX_CURVE_POINTS = 400


class TrainingNotFound(LookupError):
    pass


def outputs_dir() -> Path:
    return Path(os.environ.get("THESIS_TRAINING_OUTPUTS", BACKEND_ROOT / "training" / "outputs"))


def configs_dir() -> Path:
    return BACKEND_ROOT / "training" / "configs"


def _safe(name: str) -> str:
    if not _NAME.match(name or ""):
        raise TrainingNotFound(name)
    return name


def _read_json(p: Path) -> dict[str, Any] | None:
    try:
        return json.loads(p.read_text())
    except (OSError, json.JSONDecodeError):
        return None


def _num(v: str) -> Any:
    if v in ("", None):
        return None
    try:
        return float(v)
    except ValueError:
        return v


def _read_csv(p: Path) -> list[dict[str, Any]]:
    if not p.exists():
        return []
    with p.open() as fh:
        return [{k: _num(v) for k, v in row.items()} for row in csv.DictReader(fh)]


def _status(meta: dict[str, Any]) -> str:
    """``running`` whose training process is gone (killed, host rebooted) is reported as ``interrupted``."""
    status = meta.get("status", "unknown")
    pid, host = meta.get("pid"), meta.get("host")
    if status != "running" or not isinstance(pid, int) or host != socket.gethostname():
        return status
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return "interrupted"
    except PermissionError:
        pass
    return status


def _run_brief(d: Path) -> dict[str, Any]:
    meta = _read_json(d / "meta.json") or {}
    return {
        "run": d.name,
        "experiment": d.parent.name,
        "policy_id": meta.get("policy_id"),
        "status": _status(meta),
        "algo": meta.get("algo") or meta.get("algo_config"),
        "alpha": meta.get("alpha"),
        "beta": meta.get("beta"),
        "seed": meta.get("seed"),
        "scale": meta.get("scale") if isinstance(meta.get("scale"), str) else (meta.get("scale") or {}).get("name"),
        "training_steps": meta.get("training_steps"),
        "training_episodes": meta.get("training_episodes"),
        "mean_return_last20": meta.get("mean_return_last20"),
        "wall_time_s": meta.get("wall_time_total_s"),
        "started_at": meta.get("started_at"),
        "promoted": meta.get("promoted"),
        "error": meta.get("error"),
        "eval_summary": meta.get("eval_summary"),
        "plots": [p for p in PLOTS if (d / "plots" / p).exists()],
    }


def list_experiments() -> list[dict[str, Any]]:
    root = outputs_dir()
    configs = {p.stem: _read_json(p) or {} for p in sorted(configs_dir().glob("*.json"))}
    names = set(configs)
    if root.exists():
        names |= {d.name for d in root.iterdir() if d.is_dir() and not d.name.startswith((".", "_"))}
    out = []
    for name in sorted(names):
        runs = sorted((d for d in (root / name).iterdir() if d.is_dir()), key=lambda d: d.name) if (root / name).exists() else []
        briefs = [_run_brief(d) for d in runs]
        cfg = configs.get(name, {})
        out.append({
            "experiment": name,
            "algo": cfg.get("algo"),
            "description": cfg.get("description"),
            "config": cfg or None,
            "runs": len(briefs),
            "done": sum(b["status"] == "done" for b in briefs),
            "failed": sum(b["status"] == "failed" for b in briefs),
            "latest": briefs[-1] if briefs else None,
        })
    return out


def _downsample(rows: list[dict[str, Any]], n: int = MAX_CURVE_POINTS) -> list[dict[str, Any]]:
    if len(rows) <= n:
        return rows
    step = len(rows) / n
    return [rows[int(i * step)] for i in range(n)] + [rows[-1]]


def experiment_detail(name: str) -> dict[str, Any]:
    name = _safe(name)
    root = outputs_dir() / name
    cfg = _read_json(configs_dir() / f"{name}.json")
    if not root.exists() and cfg is None:
        raise TrainingNotFound(name)
    runs = []
    for d in sorted((d for d in root.iterdir() if d.is_dir()), key=lambda d: d.name) if root.exists() else []:
        brief = _run_brief(d)
        brief["curve"] = _downsample(_read_csv(d / "train_metrics.csv"))
        brief["eval_matrix"] = _read_csv(d / "eval_matrix.csv")
        brief["meta"] = _read_json(d / "meta.json")
        runs.append(brief)
    return {"experiment": name, "config": cfg, "runs": runs}


def plot_path(name: str, run: str, plot: str) -> Path:
    if plot not in PLOTS:
        raise TrainingNotFound(plot)
    p = outputs_dir() / _safe(name) / _safe(run) / "plots" / plot
    if not p.exists():
        raise TrainingNotFound(str(p))
    return p


def run_path(name: str, run: str) -> Path:
    p = outputs_dir() / _safe(name) / _safe(run)
    if not (p / "meta.json").exists():
        raise TrainingNotFound(str(p))
    return p
