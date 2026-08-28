import numpy as np

from simulator.config import OFF, ON, paper_device1_config
from simulator.strategies.em import apply_em_thresholds


def test_em_off_to_on_at_eup():
    cfg = paper_device1_config()
    energy = np.array([cfg.device.e_up_j, 100e-9])
    state = np.array([OFF, OFF], dtype=np.int8)
    apply_em_thresholds(energy, state, cfg)
    assert state[0] == ON
    assert state[1] == OFF


def test_em_on_to_off_at_elow():
    cfg = paper_device1_config()
    energy = np.array([cfg.device.e_low_j, 400e-9])
    state = np.array([ON, ON], dtype=np.int8)
    apply_em_thresholds(energy, state, cfg)
    assert state[0] == OFF
    assert state[1] == ON
