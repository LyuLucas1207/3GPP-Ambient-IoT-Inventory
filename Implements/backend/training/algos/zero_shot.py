"""No training: use the original Sources ``A_IoT_PPO_LSTM.zip`` on every reader.

Each reader keeps its own LSTM state. The observation is that script's raw
counts (S2b, S2a, S1, empty, collisions, K, p), and the action is the
multiplier pair already in [0.25, 10] x [0.1, 10].
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from training.common import BACKEND_ROOT, CsvLog


SOURCE_ZIP = "app/simulator_thesis/rl/policies/A_IoT_PPO_LSTM.zip"


def train(job: dict[str, Any], out_dir: Path, log: CsvLog) -> dict[str, Any]:
    """Point at the original Sources weights. This job does not train."""
    path = BACKEND_ROOT / SOURCE_ZIP
    return {
        "algo": "zero_shot_aperiodic",
        "artifact": path,
        "source": SOURCE_ZIP,
        "training_steps": 1_001_472,
        "architecture": "Sources A_IoT_PPO_LSTM.zip: LSTM(1x128) -> MLP(128,128) -> action Box([0.25, 0.1], [10, 10])",
        "hyperparameters": {"source_alpha": float(job["alpha"]), "source_file": "Sources/Standard_3GPP/3GPP Ambient IoT Aperiodic Codes/Controller-Level/Code/A_IoT_PPO_LSTM.zip"},
    }
