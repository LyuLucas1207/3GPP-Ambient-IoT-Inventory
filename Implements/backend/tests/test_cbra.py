import numpy as np

from simulator.cbra import run_cbra
from simulator.config import paper_device1_config


def test_idle_success_collision():
    """run_cbra() does not execute time-AOs; unresolved PENDING AOs become IDLE.

    Occupancy (singleton vs collision) is tested in test_cbra_occupancy.py.
    """
    cfg = paper_device1_config(num_devices=8)
    rng = np.random.default_rng(1)
    eligible = np.array([0, 1, 2], dtype=int)
    result = run_cbra(cfg, rng, 0, 0.0, eligible, p_access=1.0)
    counts = {ao.status: 0 for ao in result.aos}
    for ao in result.aos:
        counts[ao.status] += 1
        if ao.status == "IDLE":
            assert ao.device_ids == []
        elif ao.status == "MSG1_SINGLETON":
            assert len(ao.device_ids) == 1
        elif ao.status == "COLLISION":
            assert len(ao.device_ids) > 1
    assert result.idle_count + result.success_ao_count + result.collision_ao_count == cfg.device.n_ao
    assert cfg.device.n_ao == 8


def test_no_eligible_all_idle():
    cfg = paper_device1_config()
    rng = np.random.default_rng(0)
    result = run_cbra(cfg, rng, 0, 0.0, np.array([], dtype=int), p_access=1.0)
    assert result.idle_count == 8
    assert result.success_ids == []
    assert result.attempting_ids == []
