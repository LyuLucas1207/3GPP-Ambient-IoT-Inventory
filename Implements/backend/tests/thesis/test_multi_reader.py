"""Per-device metrics, termination rules and reader coordination (database-free)."""

import math

import numpy as np
import pytest

from app.simulator_thesis.inventory.checkpoint import dump_state, load_state
from app.simulator_thesis.inventory.episode import DROP_CAUSE_LABEL, build_episode
from app.simulator_thesis.inventory.events import EventEmitter
from app.simulator_thesis.inventory.episode import mark_unreachable
from app.simulator_thesis.inventory.headless import drive, fingerprint, run_headless, synthetic_scene
from app.simulator_thesis.inventory.metrics import aggregate, device_metrics_blob, device_metrics_rows, load_device_metrics
from app.simulator_thesis.inventory.state import DROP_TERMINATED, EpisodeConfig
from app.simulator_thesis.inventory.termination import TerminationSpec, replay

GRID = synthetic_scene(300, seed=2)
ONE = synthetic_scene(200, reader_xy=[(60.0, 30.0)], seed=5)
# TR 38.769 D1T1-A2: two active readers at least 60 m apart.
PAIR = synthetic_scene(400, reader_xy=[(30.0, 30.0), (90.0, 30.0)], seed=7)


def _cfg(scheme: str = "aperiodic", **extra) -> EpisodeConfig:
    return EpisodeConfig.from_json(scheme, {"k_initial": 32, "adaptive_k": True, **extra})


def test_full_energy_starts_every_device_on_and_full():
    ordinary = build_episode(GRID, _cfg(), np.random.default_rng(0))
    full = build_episode(GRID, _cfg(full_energy=True), np.random.default_rng(0))
    assert ordinary.world.on.min() == 0.0
    assert np.array_equal(full.world.E, full.world.Ecap)
    assert np.all(full.world.on == full.world.T_on_default)
    assert np.all(full.world.on > 0)


# ------------------------------------------------------------------ device metrics


def test_device_metric_invariants():
    res = run_headless(GRID, _cfg(), 3)
    w = res.state.world
    cover = np.sum([r.cover_mask for r in res.state.readers], axis=0)
    assert np.array_equal(w.readers_in_range, cover)
    # every joined attempt either identified the device or counts as a CBRA failure
    assert np.array_equal(w.attempts, w.cbra_failures + w.identified.astype(int))
    assert (w.fail_to_page_count <= w.cbra_failures).all()
    assert (w.fail_to_page_max >= 0).all()
    waited = w.fail_to_page_count > 0
    assert (w.fail_to_page_sum[waited] / w.fail_to_page_count[waited] <= w.fail_to_page_max[waited] + 1e-12).all()
    # a single reader can never be "changed"
    single = run_headless(ONE, _cfg(), 3).state.world
    assert single.reader_changes.sum() == 0


def test_device_metrics_blob_round_trip():
    res = run_headless(GRID, _cfg(), 4)
    rows = device_metrics_rows(load_device_metrics(device_metrics_blob(res.state.world)))
    assert len(rows) == res.state.world.N
    agg = aggregate(res.state.world)
    assert agg["all"]["devices"] == res.state.world.N
    assert set(agg["by_subtype"]) <= {"1", "2a", "2b"}
    assert sum(r["cbra_failures"] for r in rows) == int(res.state.world.cbra_failures.sum())


# ------------------------------------------------------------------ termination


@pytest.mark.parametrize("rule", [
    {"kind": "quiet_rounds", "quiet_rounds": 8},
    {"kind": "id_rate", "window_mode": "rounds", "window": 10, "r_rel": 0.05},
    {"kind": "id_rate", "window_mode": "ewma", "ewma_alpha": 0.2, "r_rel": 0.05},
    {"kind": "combined", "combine": "any", "rules": [{"kind": "quiet_rounds", "quiet_rounds": 20}, {"kind": "energy_bound"}]},
])
def test_online_stop_matches_offline_replay_single_reader(rule):
    """Rules read only past observations and consume no randomness, so on one
    reader the live stop and the replay on the oracle run must coincide."""
    oracle = run_headless(ONE, _cfg(), 9)
    live = run_headless(ONE, _cfg(termination=rule), 9)
    reader = live.state.readers[0]
    spec = TerminationSpec.from_json(rule)
    out = replay(spec, oracle.rounds, t_wc_by_reader={reader.reader_id: reader.t_wc_s})
    # a non-oracle reader always stops: before the last ID, or after paging the empty tail
    assert reader.stopped
    assert out.reader_stop[reader.reader_id] == pytest.approx(reader.term.stopped_t)
    assert out.identified_before_stop == live.identified
    assert live.rounds == oracle.rounds[: len(live.rounds)]
    assert out.extra_time_s is not None and (out.missed > 0 or out.extra_time_s > 0)


def test_terminated_devices_get_their_own_drop_cause():
    res = run_headless(GRID, _cfg(termination={"kind": "quiet_rounds", "quiet_rounds": 2}), 5)
    w = res.state.world
    assert all(r.stopped or r.exhausted for r in res.state.readers)
    pending = w.dropped & (w.drop_cause == DROP_TERMINATED)
    assert DROP_CAUSE_LABEL[DROP_TERMINATED] == "terminated_early"
    assert pending.sum() + w.identified.sum() + (w.dropped & (w.drop_cause == 1)).sum() == w.N
    assert res.state.counters()["terminated_early"] == int(pending.sum())


def test_energy_bound_recharge_time_is_finite_and_conservative():
    edge = build_episode(GRID, _cfg(termination={"kind": "energy_bound"}), np.random.default_rng(0))
    actual = build_episode(GRID, _cfg(termination={"kind": "energy_bound", "energy_source": "actual"}), np.random.default_rng(0))
    for a, b in zip(edge.readers, actual.readers):
        assert math.isfinite(a.t_wc_s) and a.t_wc_s > 0
        # one reader's CW at the coverage edge charges no faster than every reader's CW at the true position
        assert a.t_wc_s >= b.t_wc_s - 1e-9


def test_energy_bound_edge_cap_and_max_wait():
    """Active 2b devices are covered far beyond the harvesting range (xi = 0 below
    -41 dBm), so the uncapped edge bound is infinite; the cap and max_wait bound it."""
    from app.simulator_thesis.catalog import spec_for
    from app.simulator_thesis.inventory.termination import TermState, evaluate

    scene = synthetic_scene(200, reader_xy=[(60.0, 30.0)], seed=5)
    for p in scene["placements"]:
        if p["kind"] == "device" and p["subtype"] == "2b":
            p["params"] = spec_for("device", "2b").defaults()

    def t_wc(**term):
        st = build_episode(scene, _cfg(termination={"kind": "energy_bound", **term}), np.random.default_rng(0))
        return st.readers[0].t_wc_s

    assert t_wc() == math.inf
    capped = t_wc(edge_cap_m=41.4)
    assert 1500 < capped < 2000  # Device 2a at its 41.4 m edge

    st = TermState(t_first=0.0, last_id_t=10.0)
    spec = TerminationSpec.from_json({"kind": "energy_bound", "max_wait_s": 300})
    assert evaluate(spec, st, 309.0, math.inf) is None
    assert evaluate(spec, st, 310.0, math.inf) == "energy_bound"
    assert evaluate(spec, st, 30.0, 15.0) == "energy_bound"  # T_wc below the cap still rules
    assert evaluate(TerminationSpec.from_json({"kind": "energy_bound"}), st, 1e9, math.inf) is None


def test_stations_add_cw_without_becoming_readers():
    """Paper multi-source: a station radiates CW for harvest and does not page."""
    scene = synthetic_scene(40, reader_xy=[(60.0, 30.0)], seed=1)
    bare = build_episode(scene, _cfg(), np.random.default_rng(0))
    scene["placements"].append(
        {"id": 200_000, "kind": "station", "subtype": None, "x_m": 20.0, "y_m": 30.0, "params": {}}
    )
    with_station = build_episode(scene, _cfg(), np.random.default_rng(0))
    readers_only = build_episode(scene, _cfg(station_cw=False), np.random.default_rng(0))
    assert len(with_station.readers) == len(bare.readers) == 1
    assert (with_station.world.Ph_total > bare.world.Ph_total).all()
    np.testing.assert_allclose(readers_only.world.Ph_total, bare.world.Ph_total)


def test_harvested_power_applies_conversion_efficiency_to_total_cw():
    st = build_episode(GRID, _cfg(), np.random.default_rng(0))
    pin_w = sum(r.Ph_contrib for r in st.readers)
    pin_dbm = 10.0 * np.log10(pin_w) + 30.0
    xi = np.clip(np.where(pin_dbm <= -10.0, (pin_dbm + 41.0) / 100.0, (-2.0 * pin_dbm + 11.0) / 100.0), 0.0, 1.0)
    np.testing.assert_allclose(st.world.Ph_total, xi * pin_w, rtol=1e-12)
    assert (st.world.Ph_total < pin_w).all()


# ------------------------------------------------------------------ coordination


def test_independent_mode_has_no_interference():
    res = run_headless(GRID, _cfg(resource={"mode": "independent"}), 6)
    for r in res.state.readers:
        assert r.subbands == tuple(range(8))
        assert r.interference["frames_hit"] == 0


def test_fdma_grants_disjoint_subbands_to_neighbours():
    st = build_episode(GRID, _cfg(resource={"mode": "fdma", "conflict_distance_m": 30}), np.random.default_rng(0))
    coord = st.coord
    assert coord.n_colors <= 8
    for i, a in enumerate(st.readers):
        assert a.f_r >= 1
        for j in np.nonzero(coord.adj[i])[0]:
            assert not set(a.subbands) & set(st.readers[j].subbands)


def test_fdma_keeps_msg1_length_when_f_r_shrinks():
    res = run_headless(GRID, _cfg("aperiodic", adaptive_k=False, resource={"mode": "fdma", "conflict_distance_m": 30}), 7, max_frames=40)
    for r in res.rounds:
        f_r = r["metadata"]["f_r"]
        assert r["k_estimate"] == math.ceil(32 / 8) * f_r


def test_tdma_frames_start_inside_their_colour_window():
    cfg = _cfg(max_time_s=6, resource={"mode": "tdma", "tdma_window_s": 0.5})
    res = run_headless(GRID, cfg, 8)
    coord = res.state.coord
    by_id = {r.reader_id: i for i, r in enumerate(res.state.readers)}
    for r in res.rounds:
        slot, slots = coord.time_slot(by_id[r["reader_id"]])
        phase = r["t_start_s"] % (slots * 0.5)
        assert slot * 0.5 - 1e-9 <= phase < (slot + 1) * 0.5 + 1e-9


def test_lbt_neighbours_never_start_during_each_other():
    cfg = _cfg(max_time_s=6, resource={"mode": "lbt"})
    res = run_headless(GRID, cfg, 9)
    coord = res.state.coord
    by_id = {r.reader_id: i for i, r in enumerate(res.state.readers)}
    frames = [(by_id[r["reader_id"]], r["t_start_s"], r["t_end_s"]) for r in res.rounds]
    for a, s_a, e_a in frames:
        for b, s_b, e_b in frames:
            if a != b and coord.adj[a, b] and s_a < s_b:
                assert s_b >= e_a - 1e-9, (a, b, s_a, e_a, s_b)


def test_tr_a2_pair_needs_coordination():
    """Two readers 60 m apart (D1T1-A2): the other reader's CW after 61 dB
    suppression still swamps the D2R floor, so sharing collapses and the
    link-budget conflict graph separates them (TR 38.769 7.2.2 multiplexes them too)."""
    ideal = run_headless(PAIR, _cfg(max_time_s=60), 10)
    shared = run_headless(PAIR, _cfg(max_time_s=60, resource={"mode": "shared"}), 10)
    assert shared.identified < 0.5 * ideal.identified
    for mode, keep in (("fdma", 0.95), ("lbt", 0.95), ("tdma", 0.9)):
        res = run_headless(PAIR, _cfg(max_time_s=60, resource={"mode": mode}), 10)
        assert res.state.coord.n_colors == 2
        assert res.identified >= keep * ideal.identified, mode


# ------------------------------------------------------------------ checkpoint


@pytest.mark.parametrize("extra", [
    {"resource": {"mode": "tdma"}},
    {"resource": {"mode": "lbt"}},
    {"resource": {"mode": "fdma"}, "termination": {"kind": "quiet_rounds", "quiet_rounds": 6}},
])
def test_checkpoint_resume_is_exact_with_coordination(extra):
    cfg = _cfg(max_time_s=8, **extra)
    whole = run_headless(GRID, cfg, 11)

    rng = np.random.default_rng(11)
    state = build_episode(GRID, cfg, rng)
    emit = EventEmitter(run_id=0)
    mark_unreachable(state, emit)
    first = drive(state, max_frames=150, finish=False)
    restored = load_state(dump_state(first.state), GRID, cfg)
    rest = drive(restored)
    rest.rounds = first.rounds + rest.rounds
    assert fingerprint(rest) == fingerprint(whole)
