import numpy as np

from simulator.config import DONE, OFF, ON, SLEEP, TX, paper_device1_config
from simulator.energy import sleep_net_min_w_from_nw, update_energy


def _step(state_code, peh, n=3):
    cfg = paper_device1_config()
    d = cfg.device
    energy = np.full(n, 300e-9)
    state = np.full(n, state_code, dtype=np.int8)
    peh_w = np.full(n, peh)
    update_energy(energy, state, peh_w, cfg.dt_s, d.p_rx_w, d.p_tx_w, d.p_sl_w, d.e_max_j)
    return energy, d


def test_off_harvests_and_clamps():
    energy, d = _step(OFF, peh=1e-6)
    assert np.all(energy > 300e-9)
    energy = np.full(3, d.e_max_j)
    state = np.full(3, OFF, dtype=np.int8)
    peh_w = np.full(3, 1.0)
    update_energy(energy, state, peh_w, 1.0, d.p_rx_w, d.p_tx_w, d.p_sl_w, d.e_max_j)
    assert np.all(energy == d.e_max_j)


def test_on_consumes_prx():
    energy, d = _step(ON, peh=0.0)
    assert np.allclose(energy, 300e-9 - d.p_rx_w * 0.5e-3)


def test_tx_consumes_ptx():
    energy, d = _step(TX, peh=0.0)
    assert np.allclose(energy, 300e-9 - d.p_tx_w * 0.5e-3)


def test_sleep_harvests_minus_psl():
    peh = 2e-6
    energy, d = _step(SLEEP, peh=peh)
    expected = 300e-9 + (peh - d.p_sl_w) * 0.5e-3
    assert np.allclose(energy, expected)


def test_sleep_min_zero_stops_drain_when_peh_below_psl():
    cfg = paper_device1_config()
    d = cfg.device
    peh = 12.56e-9  # < P_sl = 100 nW
    energy = np.array([300e-9])
    state = np.array([SLEEP], dtype=np.int8)
    peh_w = np.array([peh])
    update_energy(
        energy, state, peh_w, 1.0, d.p_rx_w, d.p_tx_w, d.p_sl_w, d.e_max_j,
        sleep_net_min_w=0.0,
    )
    assert energy[0] == 300e-9


def test_sleep_min_neg_inf_still_drains_when_peh_below_psl():
    cfg = paper_device1_config()
    d = cfg.device
    peh = 12.56e-9
    energy = np.array([300e-9])
    state = np.array([SLEEP], dtype=np.int8)
    peh_w = np.array([peh])
    update_energy(
        energy, state, peh_w, 1.0, d.p_rx_w, d.p_tx_w, d.p_sl_w, d.e_max_j,
        sleep_net_min_w=float("-inf"),
    )
    expected = 300e-9 + (peh - d.p_sl_w) * 1.0
    assert np.isclose(energy[0], expected)
    assert energy[0] < 300e-9


def test_sleep_min_custom_floor_clips_drain():
    cfg = paper_device1_config()
    d = cfg.device
    peh = 12.56e-9
    floor = -50e-9
    energy = np.array([300e-9])
    state = np.array([SLEEP], dtype=np.int8)
    peh_w = np.array([peh])
    update_energy(
        energy, state, peh_w, 1.0, d.p_rx_w, d.p_tx_w, d.p_sl_w, d.e_max_j,
        sleep_net_min_w=floor,
    )
    raw = peh - d.p_sl_w
    assert raw < floor
    assert np.isclose(energy[0], 300e-9 + floor * 1.0)


def test_done_energy_frozen():
    energy, _ = _step(DONE, peh=1e-3)
    assert np.allclose(energy, 300e-9)


def test_energy_never_negative():
    cfg = paper_device1_config()
    d = cfg.device
    energy = np.array([1e-15])
    state = np.array([ON], dtype=np.int8)
    peh_w = np.array([0.0])
    update_energy(energy, state, peh_w, 1.0, d.p_rx_w, d.p_tx_w, d.p_sl_w, d.e_max_j)
    assert energy[0] >= 0.0


def test_sleep_net_min_w_from_nw_none_is_neg_inf():
    assert sleep_net_min_w_from_nw(None) == float("-inf")
    assert sleep_net_min_w_from_nw(0.0) == 0.0
    assert np.isclose(sleep_net_min_w_from_nw(-50.0), -50e-9)
