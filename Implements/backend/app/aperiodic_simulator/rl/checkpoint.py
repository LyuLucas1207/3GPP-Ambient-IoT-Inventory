"""Recurrent-PPO checkpoint paths, metadata and integrity checks.

Each checkpoint ``recurrent_ppo_alpha_<a>.zip`` has a sibling
``recurrent_ppo_alpha_<a>.json`` with the training metadata (steps, seed,
config hash, package versions, git commit, action/observation transforms)
and the zip's SHA-256.
"""

import hashlib
import json
from pathlib import Path

CHECKPOINT_DIR = Path(__file__).resolve().parent / "checkpoints"
TRAIN_COMMAND = "python backend/scripts/aperiodic/train_ppo/train_ppo.py --steps 1000000 --seed 42"


class CheckpointMissing(RuntimeError):
    pass


def alpha_tag(alpha: float) -> str:
    return f"{alpha:.2f}".rstrip("0").rstrip(".").replace(".", "p") if alpha != int(alpha) else f"{int(alpha)}p0"


def checkpoint_path(alpha: float = 0.5) -> Path:
    return CHECKPOINT_DIR / f"recurrent_ppo_alpha_{alpha_tag(alpha)}.zip"


def meta_path(alpha: float = 0.5) -> Path:
    return checkpoint_path(alpha).with_suffix(".json")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load_meta(alpha: float = 0.5, verify: bool = True) -> dict:
    zp, mp = checkpoint_path(alpha), meta_path(alpha)
    if not zp.exists() or not mp.exists():
        raise CheckpointMissing(
            f"PPO checkpoint not available for alpha={alpha} ({zp.name}). Train it with: {TRAIN_COMMAND}"
            + (f" --alpha {alpha}" if alpha != 0.5 else "")
        )
    meta = json.loads(mp.read_text())
    if verify:
        digest = sha256_file(zp)
        if digest != meta.get("sha256"):
            raise CheckpointMissing(f"PPO checkpoint {zp.name} fails SHA-256 verification (metadata {meta.get('sha256')}, file {digest})")
    meta["path"] = str(zp)
    return meta


def available_alphas() -> list[float]:
    out = []
    for mp in sorted(CHECKPOINT_DIR.glob("recurrent_ppo_alpha_*.json")):
        try:
            out.append(float(json.loads(mp.read_text())["alpha"]))
        except (KeyError, ValueError, json.JSONDecodeError):
            continue
    return out


def ppo_status_payload() -> dict:
    try:
        meta = load_meta(0.5)
    except CheckpointMissing as exc:
        return {"available": False, "reason": str(exc), "train_command": TRAIN_COMMAND, "alphas": available_alphas()}
    return {
        "available": True,
        "checkpoint": meta["path"],
        "training_steps": meta["training_steps"],
        "paper_training_steps": 1_000_000,
        "fully_trained": meta["training_steps"] >= 1_000_000,
        "architecture": meta["architecture"],
        "trained_scenario": meta["trained_scenario"],
        "alpha": meta["alpha"],
        "sha256": meta["sha256"],
        "seed": meta["seed"],
        "created_at": meta.get("created_at"),
        "git_commit": meta.get("git_commit"),
        "package_versions": meta.get("package_versions"),
        "action_transform": meta.get("action_transform"),
        "observation_normalization": meta.get("observation_normalization"),
        "alphas": available_alphas(),
        "train_command": TRAIN_COMMAND,
    }
