"""No training: reference the aperiodic engine's single-reader RecurrentPPO checkpoint.

Every reader runs that policy with its own LSTM state on the single-reader
observation (S1, S2a, S2b, I, C per resource, L, p). This measures how far a
policy trained for one reader transfers to many without retraining.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from training.common import BACKEND_ROOT, CsvLog


def train(job: dict[str, Any], out_dir: Path, log: CsvLog) -> dict[str, Any]:
    from app.aperiodic_simulator.rl.checkpoint import load_meta

    src = load_meta(float(job["alpha"]))
    path = Path(src["path"])
    try:
        rel = str(path.relative_to(BACKEND_ROOT))
    except ValueError:
        rel = str(path)
    return {
        "algo": "zero_shot_aperiodic",
        "artifact": path,
        "source": rel,
        "training_steps": int(src.get("training_steps") or 0),
        "architecture": src.get("architecture"),
        "hyperparameters": {"source_alpha": src.get("alpha"), "source_seed": src.get("seed")},
    }
