"""Actual AO occupancy is decided at Msg1 time, not at plan creation."""

import numpy as np

from simulator.cbra import (
    AO_COLLISION,
    AO_IDLE,
    AO_SINGLETON,
    drop_if_energy_fail,
    finish_cbra,
    plan_cbra,
    resolve_msg1_time_ao,
)
from simulator.config import ON, paper_device1_config


def _forced_same_ao(cfg, n_attempt=2):
    rng = np.random.default_rng(0)
    eligible = np.arange(n_attempt)
    plan = plan_cbra(cfg, rng, 0, 0, 0.0, eligible, p_access=1.0)
    n_freq = cfg.device.n_freq_ao
    plan.time_ao[:] = 0
    plan.freq_ao[:] = 0
    for ao in plan.aos:
        ao.planned_ids = []
    plan.aos[0].planned_ids = list(range(n_attempt))
    return plan


def test_drop_before_msg1_turns_collision_into_singleton():
    cfg = paper_device1_config(num_devices=2)
    plan = _forced_same_ao(cfg, 2)
    n = 2
    energy = np.array([500e-9, 0.0])
    state = np.full(n, ON, dtype=np.int8)
    inventoried = np.zeros(n, dtype=bool)
    msg1_j = cfg.device.p_tx_w * cfg.device.msg1_s
    resolve_msg1_time_ao(plan, 0, energy, state, inventoried, cfg.device.e_low_j, msg1_j)
    ao = plan.aos[0]
    assert ao.status == AO_SINGLETON
    assert ao.transmitted_ids == [0]
    assert 1 in ao.dropped_before_msg1
    assert 1 not in ao.transmitted_ids
    assert int(plan.pending_success[0]) == 0


def test_msg3_energy_fail_keeps_msg1_singleton_not_done():
    cfg = paper_device1_config(num_devices=1)
    rng = np.random.default_rng(1)
    plan = plan_cbra(cfg, rng, 0, 0, 0.0, np.array([0]), p_access=1.0)
    energy = np.array([500e-9])
    state = np.array([ON], dtype=np.int8)
    inventoried = np.zeros(1, dtype=bool)
    msg1_j = cfg.device.p_tx_w * cfg.device.msg1_s
    t_ao = int(plan.time_ao[0])
    resolve_msg1_time_ao(plan, t_ao, energy, state, inventoried, cfg.device.e_low_j, msg1_j)
    ao = next(a for a in plan.aos if a.status == AO_SINGLETON)
    energy[0] = 0.0
    drop_if_energy_fail(plan, energy, cfg.device.e_low_j, "msg3")
    assert ao.status == AO_SINGLETON
    assert ao.final_result == "energy_failed_msg3"
    assert plan.pending_success.size == 0
    res = finish_cbra(plan, cfg)
    assert res.msg1_singleton_ids == [0]
    assert res.completed_ids == []


def test_collision_devices_are_actual_transmitters():
    cfg = paper_device1_config(num_devices=2)
    plan = _forced_same_ao(cfg, 2)
    energy = np.array([500e-9, 500e-9])
    state = np.full(2, ON, dtype=np.int8)
    inventoried = np.zeros(2, dtype=bool)
    msg1_j = cfg.device.p_tx_w * cfg.device.msg1_s
    resolve_msg1_time_ao(plan, 0, energy, state, inventoried, cfg.device.e_low_j, msg1_j)
    ao = plan.aos[0]
    assert ao.status == AO_COLLISION
    assert set(ao.transmitted_ids) == {0, 1}
    assert set(plan.collision_ids.tolist()) == {0, 1}
    assert plan.pending_success.size == 0


def test_non_attempting_device_not_in_occupancy():
    cfg = paper_device1_config(num_devices=3)
    rng = np.random.default_rng(2)
    # Force only device 0 to attempt by p=0 then patch.
    plan = plan_cbra(cfg, rng, 0, 0, 0.0, np.array([0, 1, 2]), p_access=0.0)
    assert plan.attempting_ids.size == 0
    energy = np.ones(3) * 500e-9
    state = np.full(3, ON, dtype=np.int8)
    inventoried = np.zeros(3, dtype=bool)
    resolve_msg1_time_ao(plan, 0, energy, state, inventoried, cfg.device.e_low_j, 0.0)
    for ao in plan.aos:
        assert 2 not in ao.transmitted_ids
        assert 2 not in ao.planned_ids
    assert all(ao.status != AO_COLLISION for ao in plan.aos)
