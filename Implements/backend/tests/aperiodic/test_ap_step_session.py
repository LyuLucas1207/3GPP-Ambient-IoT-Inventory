import numpy as np
from fastapi.testclient import TestClient

from app.aperiodic_simulator.core.runner import run_episode
from app.aperiodic_simulator.core.simulation import Episode
from app.aperiodic_simulator.runtime import step_session
from app.aperiodic_simulator.runtime.service import build_config
from app.main import app
from app.schemas.aperiodic_simulator import AperiodicSimulateRequest

client = TestClient(app)
BASE = "/api/aperiodic-simulator"


def _cfg(**kw):
    req = AperiodicSimulateRequest(**{"num_devices": 120, "seed": 7, "max_time_s": 60.0, **kw})
    return build_config(req)


def test_step_session_matches_regular_episode():
    for kw in ({"L_fixed": 2}, {"paging_mode": "periodic", "N_g": 4, "L_fixed": 4}):
        cfg = _cfg(**kw)
        ref = run_episode(cfg).episode
        sess = step_session.create(cfg)
        rows = []
        while not sess.ep.finished and len(rows) < 40:
            r = sess.next(skip_empty=False)
            rows.append((r["t_start_s"], r["t_end_s"], r["counts"]["identified"], r["counts"]["participants"]))
        for got, want in zip(rows, ref.history):
            assert got[0] == want[0] and got[1] == want[1]
            assert got[2] == want[4] and got[3] == want[7]
        step_session.delete(sess.id)


def test_round_detail_is_consistent():
    for kw in ({"L_fixed": 1}, {"paging_mode": "periodic", "N_g": 4, "L_fixed": 4}, {"controller": "dfsa_schoute", "L_mode": "adaptive"}):
        sess = step_session.create(_cfg(**kw))
        for _ in range(8):
            r = sess.next(skip_empty=True)
            if "counts" not in r:
                break
            c, devs = r["counts"], r["devices"]
            assert c["paged"] == c["paged_monitor"] + c["paged_sync_wake"] + c["paged_resync"]
            assert c["paged"] == sum(d["paged_via"] is not None for d in devs)
            assert c["participants"] == sum(d["access"] == "transmit" for d in devs)
            assert c["rejected"] == sum(d["access"] == "reject" for d in devs)
            assert sum(c["fates"].values()) == c["participants"]
            assert sum(len(a) for a in r["ao"]["devices"]) == c["participants"]
            assert len(r["msg2"]) == c["k_served"]
            assert c["identified"] == c["to_done"] == sum(m["identified"] for m in r["msg3"])
            for d in devs:
                if d["access"] == "transmit":
                    assert d["page"] is not None and d["ao"] is not None
                    assert d["segments"] and d["segments"][-1]["t1"] <= r["t_end_s"] + 1e-9
                if d["fate"] == "success" and r["counts"]["depletion_by_stage"]["msg3"] == 0:
                    assert d["after"]["state"] == "DONE"
        step_session.delete(sess.id)


def test_step_session_api_lifecycle():
    res = client.post(f"{BASE}/step-sessions", json={"config": {"L_fixed": 4}, "n_devices": 30})
    assert res.status_code == 200
    info = res.json()
    sid = info["session_id"]
    assert info["n_eff"] == len(info["devices"]) == len(info["now"]["states"])
    nxt = client.post(f"{BASE}/step-sessions/{sid}/next", json={"skip_empty": True}).json()
    assert nxt["round"] >= 0 and nxt["counts"]["paged"] > 0
    assert client.delete(f"{BASE}/step-sessions/{sid}").json() == {"deleted": True}
    assert client.post(f"{BASE}/step-sessions/{sid}/next").status_code == 404
    bad = client.post(f"{BASE}/step-sessions", json={"config": {"L_fixed": 4}, "n_devices": 5000})
    assert bad.status_code == 422


def test_session_store_is_bounded():
    cfg = _cfg(num_devices=20)
    ids = [step_session.create(cfg).id for _ in range(step_session.MAX_SESSIONS + 3)]
    assert step_session.session_count() <= step_session.MAX_SESSIONS
    for sid in ids:
        step_session.delete(sid)


def test_batch_episode_seeds_differ():
    """Episode i of a batch uses seed base+i: layouts and DCM phases differ between episodes."""
    cfg = _cfg(num_devices=200)
    a, b = Episode(cfg.with_(seed=10)), Episode(cfg.with_(seed=11))
    assert not np.array_equal(a.population.xy, b.population.xy)
    assert not np.allclose(a.anchor[: min(a.n, b.n)], b.anchor[: min(a.n, b.n)])
    c = Episode(cfg.with_(seed=10))
    assert np.array_equal(a.population.xy, c.population.xy)


def test_paper_reference_endpoint():
    res = client.get(f"{BASE}/paper-reference/fig5a")
    assert res.status_code == 200
    body = res.json()
    assert body["figure"] == "figure5" and body["curves"]
    for curve in body["curves"].values():
        assert len(curve["x"]) == len(curve["y"]) > 1
    assert client.get(f"{BASE}/paper-reference/nope").status_code == 404
