import math

import pytest

from app.aperiodic_simulator.core.config import SystemParams
from app.aperiodic_simulator.physics.device_types import device_types, type_param_arrays
from app.aperiodic_simulator.physics.energy import (
    compute_global_lmax,
    e_base_j,
    e_scale_j,
    e_worst_case_direct_j,
    e_worst_case_j,
    lmax_report,
    lmax_type,
)
from app.aperiodic_simulator.core.timing import (
    aperiodic_msg3_slots,
    aperiodic_round_duration_s,
    periodic_k_fixed,
    periodic_round_interval_s,
    t_ei_s,
    t_msg1_s,
    t_msg2_s,
    t_msg3_s,
    t_page_s,
)

import numpy as np

S = SystemParams()


def test_durations_from_bits_and_rate():
    assert t_page_s() == pytest.approx(80 / 7000)
    assert t_msg1_s() == pytest.approx(38 / 7000)
    assert t_msg2_s() == pytest.approx(88 / 7000)
    assert t_msg3_s() == pytest.approx(144 / 7000)


@pytest.mark.parametrize("L", [1, 2, 16, 83])
def test_t_ei(L):
    assert t_ei_s(L) == pytest.approx((L * 8 + 24) / 7000)


def test_periodic_interval_oracles():
    assert periodic_round_interval_s(1) * 1e3 == pytest.approx(82.0, abs=0.05)
    assert periodic_round_interval_s(16) * 1e3 == pytest.approx(1089.14, abs=0.05)
    assert periodic_k_fixed(16) == pytest.approx(0.5 * 16 * 8)


def test_aperiodic_round_uses_decoded_msg1():
    L, K = 4, 13
    expected = t_page_s() + L * t_msg1_s() + t_ei_s(L) + K * t_msg2_s() + math.ceil(K / 8) * t_msg3_s()
    assert aperiodic_round_duration_s(L, K) == pytest.approx(expected)
    assert aperiodic_msg3_slots(0) == 0
    assert aperiodic_msg3_slots(8) == 1
    assert aperiodic_msg3_slots(9) == 2
    # With nothing decoded the aperiodic round is shorter than the periodic one.
    assert aperiodic_round_duration_s(16, 0) < periodic_round_interval_s(16)


def test_lmax_values():
    rep = lmax_report()
    t1, t2a, t2b = device_types()
    assert lmax_type(t1) == 170
    assert lmax_type(t2a) == 83
    assert lmax_type(t2b) == 83
    assert compute_global_lmax() == 83
    assert rep["Lmax"] == 83
    assert rep["per_type"]["1"]["Lmax"] == 170


@pytest.mark.parametrize("L", [1, 16, 83])
def test_energy_bound_affine_in_L(L):
    for t in device_types():
        assert e_worst_case_j(t, L) == pytest.approx(e_base_j(t) + e_scale_j(t) * L)
        assert e_worst_case_direct_j(t, L) == pytest.approx(e_worst_case_j(t, L), rel=1e-9)
        assert e_base_j(t) > 0 and e_scale_j(t) > 0
    for t in device_types():
        assert e_worst_case_j(t, lmax_type(t)) <= t.e_up_j - t.e_low_j + 1e-15
        assert e_worst_case_j(t, lmax_type(t) + 1) > t.e_up_j - t.e_low_j


def test_monitor_power_per_type():
    t1, t2a, t2b = device_types()
    assert t1.p_wurx_w == t1.p_rx_w == 1e-6
    assert t2a.uses_wurx and t2b.uses_wurx
    assert t2a.p_wurx_w == S.p_wurx_w and t2a.p_wurx_w < t2a.p_rx_w
    par = type_param_arrays(np.array([0, 1, 2]))
    assert par["p_wurx_w"].tolist() == [1e-6, 1e-6, 1e-6]
    assert par["p_rx_w"].tolist() == [1e-6, 50e-6, 50e-6]
