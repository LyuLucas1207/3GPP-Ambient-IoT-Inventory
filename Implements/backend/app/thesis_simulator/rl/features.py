"""Observation and action transforms of the multi-reader (K, p*) policy.

Shared by the training environment (``rl.env``), the live ``PolicyController``
and the training folder, so a policy sees exactly the same numbers in training
and in a run.

Observation (``OBS_DIM`` floats in [0, 1])
------------------------------------------
For each of the reader's last ``HISTORY`` frames, newest first (zeros when
the reader has run fewer frames):

    S / K, C / K, E / K           success / collision / empty Msg1 resources
    new_ids / K, joiners / K
    log2(K) / log2(K_max)         size of the frame
    p                             paging probability used
    t_frame / T_REF               duration (clipped)

then the reader's context, all of it knowable by a real reader:

    readers / R_MAX, neighbours / (R_MAX - 1), colour / colours, F_r / F,
    start offset / OFFSET_REF, x / width, y / height,
    time since the last new ID / T_QUIET_REF, frames run / FRAMES_REF

The number of devices left, their energies and availability are never
observed (the reader cannot know them).

Action
------
``a`` in [-1, 1]^2 -> multipliers (m, q) with the single-reader mapping of
``app.aperiodic_simulator.rl.transforms`` (m in [0.25, 10], q in [0.1, 10],
log-uniform). With ``L_prev = ceil(K_prev / F_r)``:

    L = clip(ceil(m * L_prev), 1, ceil(K_max / F_r));   K = L * F_r
    p = clip(q * p_prev, P_FLOOR, 1)

so the policy scales the Msg1 length and the resources follow the grant.
"""

from __future__ import annotations

import math
from typing import TYPE_CHECKING

import numpy as np

from app.aperiodic_simulator.rl.transforms import ACTION_TRANSFORM as SINGLE_READER_ACTION
from app.aperiodic_simulator.rl.transforms import action_to_multipliers

if TYPE_CHECKING:
    from app.thesis_simulator.inventory.state import EpisodeConfig, ReaderState

HISTORY = 4
FRAME_FEATURES = 8
CONTEXT_FEATURES = 9
OBS_DIM = HISTORY * FRAME_FEATURES + CONTEXT_FEATURES
ACTION_DIM = 2

R_MAX = 18
T_REF = 0.5
OFFSET_REF = 10.0
T_QUIET_REF = 120.0
FRAMES_REF = 2000.0
P_FLOOR = 1e-4

OBSERVATION_SPEC = {
    "history": HISTORY,
    "frame_features": ["S/K", "C/K", "E/K", "new_ids/K", "joiners/K", "log2(K)/log2(K_max)", "p", f"t_frame/{T_REF}"],
    "context_features": [
        f"readers/{R_MAX}", f"neighbors/{R_MAX - 1}", "color/n_colors", "F_r/F", f"start_offset/{OFFSET_REF}",
        "x/width", "y/height", f"time_since_last_id/{T_QUIET_REF}", f"frames/{FRAMES_REF}",
    ],
    "dim": OBS_DIM,
    "excluded": ["devices left", "energies", "availability", "C2"],
}
ACTION_SPEC = {
    **SINGLE_READER_ACTION,
    "L": "clip(ceil(m * ceil(K_prev / F_r)), 1, ceil(K_max / F_r))",
    "K": "L * F_r",
    "p": f"clip(q * p_prev, {P_FLOOR}, 1)",
}


def _clip01(x: float) -> float:
    return 0.0 if not math.isfinite(x) else min(1.0, max(0.0, x))


def observation(reader: "ReaderState", config: "EpisodeConfig") -> np.ndarray:
    k_max = max(2, int(config.consts.k_max))
    out = np.zeros(OBS_DIM, dtype=np.float32)
    hist = list(reader.history)[-HISTORY:][::-1]
    for i, h in enumerate(hist):
        k = max(1, h.k)
        base = i * FRAME_FEATURES
        out[base: base + FRAME_FEATURES] = (
            _clip01(h.success / k), _clip01(h.collision / k), _clip01(h.empty / k),
            _clip01(h.new_ids / k), _clip01(h.joiners / k),
            _clip01(math.log2(k) / math.log2(k_max)), _clip01(h.pstar), _clip01((h.t_end - h.t_start) / T_REF),
        )
    ctx = reader.context
    F = max(1, int(config.consts.f_freq))
    n_colors = max(1.0, ctx.get("n_colors", 1.0))
    now = reader.history[-1].t_end if reader.history else reader.clock_s
    last_id = reader.term.last_id_t
    quiet = now - (last_id if last_id is not None else (reader.term.t_first if reader.term.t_first is not None else now))
    base = HISTORY * FRAME_FEATURES
    out[base:] = (
        _clip01(ctx.get("n_readers", 1.0) / R_MAX),
        _clip01(ctx.get("neighbors", 0.0) / (R_MAX - 1)),
        _clip01(ctx.get("color", 0.0) / n_colors),
        _clip01(reader.f_r / F),
        _clip01(ctx.get("start_offset_s", 0.0) / OFFSET_REF),
        _clip01(ctx.get("x_norm", 0.0)),
        _clip01(ctx.get("y_norm", 0.0)),
        _clip01(quiet / T_QUIET_REF),
        _clip01(reader.term.frames / FRAMES_REF),
    )
    return out


def apply_action(action, k_prev: int, p_prev: float, f_r: int, k_max: int) -> tuple[int, float, float, float]:
    """(K, p, m, q) for ``action`` given the previous frame's K and p."""
    m, q = action_to_multipliers(action)
    f_r = max(1, int(f_r))
    l_prev = max(1, math.ceil(k_prev / f_r))
    l_max = max(1, math.ceil(k_max / f_r))
    L = max(1, min(math.ceil(m * l_prev), l_max))
    p = min(max(q * p_prev, P_FLOOR), 1.0)
    return int(L * f_r), float(p), float(m), float(q)
