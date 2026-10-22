"""Engine-level tests for the stepped episode (no database needed)."""

import math

import numpy as np

from app.thesis_simulator.inventory.checkpoint import dump_state, load_state
from app.thesis_simulator.inventory.config import CONSTANTS
from app.thesis_simulator.inventory.episode import (
    build_episode,
    finish_episode,
    mark_unreachable,
    step_episode,
)
from app.thesis_simulator.inventory.events import EventEmitter
from app.thesis_simulator.inventory.state import DROP_UNREACHABLE, EpisodeConfig

MAX_STEPS = 200_000
"""Loop guard: every test must terminate even if the engine never finishes."""


def _scene(n_near: int = 30, far: bool = True) -> dict:
    placements = []
    for i in range(n_near):
        placements.append({
            "id": i + 1, "kind": "device", "subtype": ("1", "2a", "2b")[i % 3],
            "x_m": 8.0 + (i % 6), "y_m": 8.0 + (i // 6), "params": {},
        })
    if far:
        placements.append({"id": 900, "kind": "device", "subtype": "2b", "x_m": 5000.0, "y_m": 5000.0, "params": {}})
    placements.append({"id": 1000, "kind": "radar", "subtype": None, "x_m": 10.0, "y_m": 10.0, "params": {}})
    return {"width_m": 6000, "height_m": 6000, "placements": placements}


def _config(**over) -> EpisodeConfig:
    cfg = {"max_time_s": 120.0, "k_initial": 16, "use_grouping": False, "seed": 3}
    cfg.update(over)
    return EpisodeConfig.from_json(over.pop("scheme", "periodic"), cfg)


def _run_to_end(state, emit, max_steps=MAX_STEPS):
    for _ in range(max_steps):
        if step_episode(state, emit) is None:
            break
        emit.discard()
    else:
        raise AssertionError("episode did not finish within the step guard")
    finish_episode(state, emit)
    emit.discard()


def test_out_of_range_device_is_unreachable_not_stuck():
    state = build_episode(_scene(), _config(), np.random.default_rng(1))
    emit = EventEmitter(run_id=0)
    assert mark_unreachable(state, emit) == 1
    far = int(np.nonzero(state.world.placement_ids == 900)[0][0])
    assert state.world.dropped[far] and state.world.drop_cause[far] == DROP_UNREACHABLE


def test_open_ended_run_finishes_when_all_devices_terminal():
    # No max_time: the episode must end by itself once the reachable devices are identified.
    state = build_episode(_scene(n_near=12), _config(max_time_s=None), np.random.default_rng(2))
    emit = EventEmitter(run_id=0)
    mark_unreachable(state, emit)
    _run_to_end(state, emit)
    assert state.world.all_terminal()
    assert state.world.identified.sum() == 12


def test_frame_duration_matches_reference_formula():
    cfg = _config(scheme="periodic", k_initial=64)
    state = build_episode(_scene(far=False), cfg, np.random.default_rng(4))
    emit = EventEmitter(run_id=0)
    result = step_episode(state, emit)
    k, F = 64, CONSTANTS.f_freq
    s_m2 = math.ceil(k * CONSTANTS.dcm_succ_ratio(True))
    expected = (
        CONSTANTS.t_paging()
        + math.ceil(k / F) * CONSTANTS.t_m1()
        + CONSTANTS.t_ebi(k)
        + s_m2 * CONSTANTS.t_m2()
        + math.ceil(s_m2 / F) * CONSTANTS.t_m3()
    )
    assert math.isclose(result.t_frame, expected, rel_tol=1e-12)


def test_depletion_is_not_terminal():
    state = build_episode(_scene(n_near=18, far=False), _config(), np.random.default_rng(5))
    emit = EventEmitter(run_id=0)
    _run_to_end(state, emit)
    terminal = state.world.identified | state.world.dropped
    assert terminal.all()  # max_time closes the episode; nobody is left in limbo


def test_pause_resume_is_bit_identical():
    scene, cfg = _scene(n_near=24), _config(max_time_s=60.0)

    straight = build_episode(scene, cfg, np.random.default_rng(7))
    emit_a = EventEmitter(run_id=0)
    mark_unreachable(straight, emit_a)
    _run_to_end(straight, emit_a)

    paused = build_episode(scene, cfg, np.random.default_rng(7))
    emit_b = EventEmitter(run_id=0)
    mark_unreachable(paused, emit_b)
    for _ in range(15):
        step_episode(paused, emit_b)
        emit_b.discard()
    resumed = load_state(dump_state(paused), scene, cfg)
    _run_to_end(resumed, emit_b)

    for name in ("identified", "dropped", "depletions", "attempts"):
        assert np.array_equal(getattr(straight.world, name), getattr(resumed.world, name)), name
    assert np.allclose(straight.world.E, resumed.world.E)
    assert np.allclose(straight.world.identified_t, resumed.world.identified_t, equal_nan=True)
    assert straight.frame_seq == resumed.frame_seq
    assert straight.rounds_total == resumed.rounds_total


def test_unservable_device_in_coverage_ends_by_stall_guard():
    # A device inside the coverage disk that can never harvest enough energy must not
    # keep an open-ended run alive forever: the stall guard ends it.
    scene = _scene(n_near=3, far=False)
    state = build_episode(scene, _config(max_time_s=None, stall_timeout_s=5.0), np.random.default_rng(9))
    stuck = 0
    state.world.Ph_total[stuck] = 0.0  # never recharges
    state.world.E[stuck] = 0.0
    state.world.on[stuck] = 0.0
    emit = EventEmitter(run_id=0)
    _run_to_end(state, emit)
    assert state.world.all_terminal()
    assert state.world.dropped[stuck]
    assert state.counters()["no_progress"] >= 1
