import numpy as np

from simulator.config import OFF, ON, SLEEP, paper_device1_config
from simulator.strategies.dcm import apply_dcm_pre_inventory, apply_elow, return_to_sleep


def test_preinventory_timer_returns_to_off():
    cfg = paper_device1_config()
    n = 1
    energy = np.array([cfg.device.e_max_j])
    state = np.array([ON], dtype=np.int8)
    on_remaining = np.array([2], dtype=np.int32)
    synced = np.array([False])
    apply_dcm_pre_inventory(energy, state, on_remaining, synced, cfg)
    assert state[0] == ON
    apply_dcm_pre_inventory(energy, state, on_remaining, synced, cfg)
    assert state[0] == OFF
    assert on_remaining[0] == 0


def test_synced_devices_skip_preinventory_timer():
    cfg = paper_device1_config()
    energy = np.array([cfg.device.e_max_j])
    state = np.array([ON], dtype=np.int8)
    on_remaining = np.array([1], dtype=np.int32)
    synced = np.array([True])
    apply_dcm_pre_inventory(energy, state, on_remaining, synced, cfg)
    assert state[0] == ON


def test_elow_forces_off_from_sleep():
    cfg = paper_device1_config()
    energy = np.array([cfg.device.e_low_j])
    state = np.array([SLEEP], dtype=np.int8)
    hit = apply_elow(energy, state, cfg, np.array([True]))
    assert bool(hit[0])
    assert state[0] == OFF


def test_return_to_sleep_leaves_off_and_done():
    from simulator.config import DONE

    state = np.array([ON, OFF, DONE, ON], dtype=np.int8)
    on_remaining = np.array([6, 0, 0, 3], dtype=np.int32)
    return_to_sleep(state, on_remaining, np.array([True, True, True, False]))
    assert state[0] == SLEEP
    assert on_remaining[0] == 0
    assert state[1] == OFF
    assert state[2] == DONE
    assert state[3] == ON
    assert on_remaining[3] == 3
