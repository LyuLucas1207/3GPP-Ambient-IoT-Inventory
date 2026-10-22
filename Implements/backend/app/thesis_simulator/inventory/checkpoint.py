"""Pause / resume: serialize the mutable part of an :class:`EpisodeState`.

Static data (positions, coverage masks, harvested power) is rebuilt from the
run's scene snapshot; only what the engine mutates is stored, as a
``numpy.savez_compressed`` archive. The RNG is captured through numpy's own
``bit_generator.state`` so a resumed run continues the exact same random
stream as an uninterrupted one.
"""

from __future__ import annotations

import io
import json
from typing import Any

import numpy as np

from app.thesis_simulator.inventory.episode import EpisodeState, build_episode
from app.thesis_simulator.inventory.state import DeviceWorld, EpisodeConfig

_WORLD_PREFIX = "world__"


def dump_state(state: EpisodeState) -> bytes:
    meta = {
        "sim_time": state.sim_time,
        "frame_seq": state.frame_seq,
        "next_snapshot_t": state.next_snapshot_t,
        "depletions_total": state.depletions_total,
        "last_progress_t": state.last_progress_t,
        "rng": state.rng.bit_generator.state,
        "readers": [
            {
                "reader_id": r.reader_id,
                "clock_s": r.clock_s,
                "round_index": r.round_index,
                "mnot_next": r.estimator.mnot_next,
                "exhausted": r.exhausted,
            }
            for r in state.readers
        ],
    }
    arrays = {f"{_WORLD_PREFIX}{name}": getattr(state.world, name) for name in DeviceWorld.MUTABLE_FIELDS}
    buf = io.BytesIO()
    np.savez_compressed(buf, meta=np.array(json.dumps(meta)), **arrays)
    return buf.getvalue()


def load_state(blob: bytes, snapshot: dict[str, Any], config: EpisodeConfig) -> EpisodeState:
    with np.load(io.BytesIO(blob), allow_pickle=False) as data:
        meta = json.loads(str(data["meta"]))
        arrays = {name: data[f"{_WORLD_PREFIX}{name}"].copy() for name in DeviceWorld.MUTABLE_FIELDS}

    rng = np.random.default_rng()
    rng.bit_generator.state = meta["rng"]
    state = build_episode(snapshot, config, rng, warm_start=False)
    for name, arr in arrays.items():
        target = getattr(state.world, name)
        if target.shape != arr.shape:
            raise ValueError(f"checkpoint/scene mismatch for {name}: {arr.shape} vs {target.shape}")
        target[...] = arr

    by_id = {r.reader_id: r for r in state.readers}
    for saved in meta["readers"]:
        reader = by_id.get(int(saved["reader_id"]))
        if reader is None:
            raise ValueError(f"checkpoint references unknown reader {saved['reader_id']}")
        reader.clock_s = float(saved["clock_s"])
        reader.round_index = int(saved["round_index"])
        reader.estimator.mnot_next = list(saved["mnot_next"])
        reader.exhausted = bool(saved["exhausted"])

    state.sim_time = float(meta["sim_time"])
    state.frame_seq = int(meta["frame_seq"])
    state.next_snapshot_t = float(meta["next_snapshot_t"])
    state.depletions_total = int(meta["depletions_total"])
    state.last_progress_t = float(meta.get("last_progress_t", state.sim_time))
    return state
