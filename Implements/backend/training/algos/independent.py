"""IPPO baseline: one actor and one local critic per reader slot (no sharing, no global state)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from training.algos import mappo
from training.common import CsvLog


def train(job: dict[str, Any], out_dir: Path, log: CsvLog) -> dict[str, Any]:
    return mappo.train(job, out_dir, log, shared=False, central=False)
