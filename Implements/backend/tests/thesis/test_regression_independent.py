"""The ideal engine must stay bit-identical while new hooks are added.

The fingerprints in ``data/golden_independent.json`` were recorded with the
engine before the controller / termination / resource hooks existed. Every
case uses the defaults of those hooks (fixed or DFSA controller, oracle
termination, independent resources), so any change in a fingerprint means the
refactor altered the physics. Re-record only for an intended physics change:

    THESIS_RECORD_GOLDEN=1 pytest tests/thesis/test_regression_independent.py
"""

import json
import os
from pathlib import Path

import pytest

from app.thesis_simulator.inventory.headless import fingerprint, reader_ids, run_headless, synthetic_scene
from app.thesis_simulator.inventory.state import EpisodeConfig

GOLDEN = Path(__file__).parent / "data" / "golden_independent.json"


def _cases() -> dict[str, tuple[dict, EpisodeConfig, int]]:
    one = synthetic_scene(300, reader_xy=[(50.0, 30.0)], seed=1)
    full = synthetic_scene(1500, seed=2)
    two = synthetic_scene(800, reader_xy=[(30.0, 30.0), (90.0, 30.0)], seed=3)
    ids = reader_ids(full)
    offsets = {str(r): (0.5 if i % 2 else 0.0) for i, r in enumerate(ids)}
    return {
        "single_periodic_fixed": (one, EpisodeConfig.from_json("periodic", {"k_initial": 32, "adaptive_k": False}), 11),
        "grid18_periodic_grouped": (
            full,
            EpisodeConfig.from_json("periodic", {"k_initial": 64, "use_grouping": True, "g": 2, "reader_start_offsets": offsets}),
            12,
        ),
        "grid18_aperiodic_dfsa": (full, EpisodeConfig.from_json("aperiodic", {"k_initial": 32, "adaptive_k": True}), 13),
        "two_aperiodic_capped": (two, EpisodeConfig.from_json("aperiodic", {"k_initial": 64, "max_time_s": 20}), 14),
    }


def _current() -> dict[str, str]:
    return {name: fingerprint(run_headless(scene, cfg, seed)) for name, (scene, cfg, seed) in _cases().items()}


def test_independent_engine_is_bit_identical():
    got = _current()
    if os.environ.get("THESIS_RECORD_GOLDEN"):
        GOLDEN.parent.mkdir(parents=True, exist_ok=True)
        GOLDEN.write_text(json.dumps(got, indent=2, sort_keys=True) + "\n")
        pytest.skip("golden fingerprints recorded")
    want = json.loads(GOLDEN.read_text())
    assert got == want
