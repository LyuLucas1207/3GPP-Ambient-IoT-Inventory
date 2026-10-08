import numpy as np
import pytest

from app.aperiodic_simulator.protocol.cbra import NO_STAGE, Fate, ParticipantInputs, run_cbra
from app.aperiodic_simulator.core.config import SystemParams
from app.aperiodic_simulator.physics.impairments import resolve_aos
from app.aperiodic_simulator.core.states import AOObserved, AOPhysical, PagingMode
from app.aperiodic_simulator.core.timing import periodic_round_interval_s, t_ei_s, t_page_s

S = SystemParams()


def resolve(ao, pw, n_ao=4, seed=0, enabled=True, md=0.0, fa=0.0, t2=None):
    ao = np.asarray(ao)
    return resolve_aos(
        ao,
        np.asarray(pw, dtype=float),
        np.ones(ao.size, dtype=bool) if t2 is None else np.asarray(t2),
        n_ao,
        np.random.default_rng(seed),
        capture_ratio_db=6.0,
        missed_detection_rate=md,
        false_alarm_rate=fa,
        enabled=enabled,
    )


def test_capture_threshold_6db():
    r = resolve([0, 0], [4.1, 1.0])  # 6.13 dB
    assert r.physical[0] == AOPhysical.CAPTURED and r.winner[0] == 0
    assert r.observed[0] == AOObserved.SUCCESS
    r = resolve([0, 0], [3.9, 1.0])  # 5.9 dB
    assert r.physical[0] == AOPhysical.COLLISION and r.winner[0] == -1
    assert r.observed[0] == AOObserved.COLLISION
    # strongest vs the *sum* of the interferers
    r = resolve([0, 0, 0], [5.0, 1.0, 1.0])
    assert r.physical[0] == AOPhysical.COLLISION
    r = resolve([0, 0], [100.0, 1.0], enabled=False)
    assert r.physical[0] == AOPhysical.COLLISION


def test_c2_counts_type2_multi_occupancy_only():
    r = resolve([0, 0, 1, 1, 2], [9, 1, 1, 1, 1], t2=[False, False, True, False, True])
    assert r.c2 == 1  # AO0 has no type-2 device; AO1 does; AO2 is single


def test_false_alarm_separated_from_occupancy():
    r = resolve([0], [1.0], n_ao=200, fa=1.0)
    idle = r.occupancy == 0
    assert (r.physical[idle] == AOPhysical.IDLE).all()
    assert (r.observed[idle] == AOObserved.COLLISION).all()
    assert r.false_alarm[idle].all()
    assert r.observed[0] == AOObserved.SUCCESS


def test_missed_detection_separated_from_physical_success():
    r = resolve([0, 1], [1.0, 1.0], md=1.0)
    assert (r.physical[:2] == AOPhysical.SINGLE).all()
    assert (r.observed[:2] == AOObserved.IDLE).all()
    assert (r.winner[:2] == -1).all()
    assert r.missed[:2].all()


def test_impairment_draws_seeded():
    ao = np.random.default_rng(1).integers(0, 64, 100)
    a = resolve(ao, np.ones(100), n_ao=64, seed=5, md=0.3, fa=0.3)
    b = resolve(ao, np.ones(100), n_ao=64, seed=5, md=0.3, fa=0.3)
    np.testing.assert_array_equal(a.observed, b.observed)
    np.testing.assert_array_equal(a.missed, b.missed)


def parts(n, e=None, type2=True):
    p_tx = 200e-6 if type2 else 1e-6
    p_rx = 50e-6 if type2 else 1e-6
    e_up = 25e-6 if type2 else 5e-6
    return ParticipantInputs(
        energy_j=np.full(n, e_up if e is None else e),
        p_tx_w=np.full(n, p_tx),
        p_rx_w=np.full(n, p_rx),
        p_sl_w=np.full(n, 0.1e-6),
        p_harv_w=np.zeros(n),
        e_low_j=np.full(n, e_up / 2),
        e_up_j=np.full(n, e_up),
        p_ul_w=np.random.default_rng(3).uniform(1e-13, 1e-11, n),
        is_type2=np.full(n, type2),
    )


def cbra(mode, n, L, e=None, enforce=True, seed=0, imp=False):
    rng = np.random.default_rng(seed)
    return run_cbra(0.0, L, mode, parts(n, e), rng, np.random.default_rng(seed + 1), S, enforce, imp)


def test_periodic_fixed_reservation_and_waste():
    out = cbra(PagingMode.PERIODIC, 5, 16)
    assert out.k_alloc == pytest.approx(0.5 * 16 * 8)
    assert out.t_round_end == pytest.approx(periodic_round_interval_s(16))
    assert out.k_served == out.k_decoded <= 5
    assert out.k_alloc - out.k_served > 0  # unused reserved resources


def test_periodic_under_allocation_leaves_decoded_unserved():
    out = cbra(PagingMode.PERIODIC, 200, 1, seed=2)  # 8 AOs, K_fixed = 4
    assert out.k_alloc == 4.0
    if out.k_decoded > 4:
        assert out.k_served == 4
        assert (out.fate == Fate.UNSERVED).sum() == out.k_decoded - 4


def test_aperiodic_dynamic_reservation():
    out = cbra(PagingMode.APERIODIC, 20, 4)
    assert out.k_alloc == out.k_decoded == out.k_served
    assert out.identified.sum() == (out.fate == Fate.SUCCESS).sum()


def test_ei_stage_energy_and_timing():
    L = 8
    out = cbra(PagingMode.APERIODIC, 10, L)
    assert out.t_msg2_start - out.t_ei_start == pytest.approx(t_ei_s(L))
    assert out.t_msg1_start == pytest.approx(t_page_s())
    np.testing.assert_allclose(out.stage_energy_j["EI"], 50e-6 * t_ei_s(L))


def test_success_exits_after_msg3_and_fail_after_ei():
    out = cbra(PagingMode.APERIODIC, 30, 2, seed=4)
    fail = (out.fate == Fate.COLLISION) | (out.fate == Fate.MISSED)
    assert np.allclose(out.exit_time_s[fail], out.t_msg2_start)
    assert (out.exit_time_s[out.identified] > out.t_msg3_start).all()


def test_midround_depletion_enforced_vs_not():
    e = 12.5e-6 + 1e-7  # just above E_low: fails at paging/msg1
    a = cbra(PagingMode.PERIODIC, 10, 16, e=e, enforce=True)
    b = cbra(PagingMode.PERIODIC, 10, 16, e=e, enforce=False)
    assert (a.depleted_stage != NO_STAGE).all()
    assert (a.fate == Fate.DEPLETED).all() and not a.identified.any()
    assert (b.depleted_stage != NO_STAGE).all()  # recorded as would-deplete
    assert (b.fate != Fate.DEPLETED).all()
    assert (b.exit_energy_j >= 0).all()
