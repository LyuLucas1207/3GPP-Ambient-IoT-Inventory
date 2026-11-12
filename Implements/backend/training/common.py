"""Paths, run metadata and checkpoint sidecars for the training folder."""

from __future__ import annotations

import csv
import hashlib
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

TRAINING_DIR = Path(__file__).resolve().parent
BACKEND_ROOT = TRAINING_DIR.parent
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

OUTPUTS_DIR = Path(os.environ.get("THESIS_TRAINING_OUTPUTS", TRAINING_DIR / "outputs"))
CONFIGS_DIR = TRAINING_DIR / "configs"


def utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")


def tag(x: float) -> str:
    return f"{x:g}".replace(".", "p").replace("-", "m")


def policy_id(experiment: str, alpha: float, beta: float, seed: int, stamp: str) -> str:
    return f"{experiment}__a{tag(alpha)}__b{tag(beta)}__s{seed}__{stamp}"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def config_hash(obj: Any) -> str:
    return hashlib.sha256(json.dumps(obj, sort_keys=True, default=str).encode()).hexdigest()


def git_commit() -> str | None:
    try:
        return subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], cwd=BACKEND_ROOT, text=True, stderr=subprocess.DEVNULL).strip()
    except (OSError, subprocess.CalledProcessError):
        return None


def package_versions() -> dict[str, str]:
    out = {"python": sys.version.split()[0]}
    for name in ("numpy", "torch", "stable_baselines3", "sb3_contrib", "gymnasium"):
        try:
            out[name] = __import__(name).__version__
        except ImportError:
            pass
    return out


def load_config(path_or_name: str) -> dict[str, Any]:
    p = Path(path_or_name)
    if not p.exists():
        p = CONFIGS_DIR / (path_or_name if path_or_name.endswith(".json") else f"{path_or_name}.json")
    cfg = json.loads(p.read_text())
    cfg.setdefault("name", p.stem)
    cfg["_path"] = str(p)
    return cfg


def run_dir(experiment: str, stamp: str, alpha: float, beta: float, seed: int) -> Path:
    d = OUTPUTS_DIR / experiment / f"{stamp}__a{tag(alpha)}__b{tag(beta)}__s{seed}"
    for sub in ("checkpoints", "plots"):
        (d / sub).mkdir(parents=True, exist_ok=True)
    return d


def write_json(path: Path, obj: Any) -> Path:
    path.write_text(json.dumps(obj, indent=2, sort_keys=False, default=str) + "\n")
    return path


class CsvLog:
    """Append-only CSV with a header from the first row's keys."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self._keys: list[str] | None = None

    def write(self, row: dict[str, Any]) -> None:
        new = self._keys is None
        if new:
            self._keys = list(row)
        with self.path.open("a", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=self._keys, extrasaction="ignore")
            if new:
                w.writeheader()
            w.writerow(row)


def read_csv(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    with path.open() as fh:
        rows = list(csv.DictReader(fh))
    for r in rows:
        for k, v in r.items():
            try:
                r[k] = float(v) if v not in ("", None) else None
            except (TypeError, ValueError):
                pass
    return rows
