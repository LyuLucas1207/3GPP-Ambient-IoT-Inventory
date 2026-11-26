from fastapi.testclient import TestClient

from tests.thesis.test_fsa_engine import _init_section, client  # noqa: F401  (fixture)


def _run(client: TestClient, sid: int, **body) -> dict:
    res = client.post(f"/api/thesis-simulator/sections/{sid}/runs", json={"sync": True, "seed": 3, "scheme": "aperiodic", **body})
    assert res.status_code == 201, res.text
    return res.json()


def test_run_with_coordination_and_termination_blocks(client: TestClient):
    sid = _init_section(client, device_count=30, readers=[(10.0, 10.0), (40.0, 10.0)])
    run = _run(
        client, sid, max_time_s=30, k_initial=16, adaptive_k=True,
        resource={"mode": "tdma", "tdma_window_s": 0.25},
        termination={"kind": "quiet_rounds", "quiet_rounds": 6},
        controller={"kind": "dfsa"},
    )
    s = run["summary"]
    assert run["status"] == "completed"
    assert s["resource_mode"] == "tdma"
    assert s["controller_kind"] == "dfsa"
    assert s["termination_label"] == "quiet_rounds(n=6)"
    assert run["config"]["resource"]["mode"] == "tdma"

    ix = client.get(f"/api/thesis-simulator/runs/{run['id']}/interference").json()
    assert ix["mode"] == "tdma"
    assert set(ix["readers"]) == {str(r) for r in ix["readers"]}
    for info in ix["readers"].values():
        assert info["time_slot"] is not None
        assert "stop_reason" in info

    dm = client.get(f"/api/thesis-simulator/runs/{run['id']}/device-metrics").json()
    assert len(dm["devices"]) == 30
    assert dm["aggregate"]["all"]["devices"] == 30
    row = dm["devices"][0]
    for key in ("readers_in_range", "cbra_failures", "reader_changes", "fail_to_page_mean_s"):
        assert key in row


def test_termination_replay_endpoint(client: TestClient):
    sid = _init_section(client, device_count=20)
    run = _run(client, sid, max_time_s=20, k_initial=16)
    res = client.post(
        f"/api/thesis-simulator/runs/{run['id']}/termination-replay",
        json={"rules": [{"kind": "quiet_rounds", "quiet_rounds": 3}, {"kind": "energy_bound", "margin": 0.1}, {"kind": "oracle"}]},
    )
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["oracle"] is True
    assert [o["rule"] for o in body["outcomes"]] == ["quiet_rounds(n=3)", "energy_bound(edge, margin=0.1)", "oracle"]
    assert body["outcomes"][-1]["missed"] == 0


def test_bad_resource_mode_is_rejected(client: TestClient):
    sid = _init_section(client, device_count=5)
    res = client.post(f"/api/thesis-simulator/sections/{sid}/runs", json={"sync": True, "resource": {"mode": "nope"}})
    assert res.status_code == 422


def test_run_with_registry_policy(client: TestClient):
    sid = _init_section(client, device_count=20, readers=[(10.0, 10.0), (40.0, 10.0)])
    policies = client.get("/api/thesis-simulator/policies").json()
    zs = next(p for p in policies if p["policy_id"] == "A_IoT_PPO_LSTM")
    assert zs["available"] and zs["algo"] == "zero_shot_aperiodic"
    assert zs["training_steps"] == 1001472
    run = _run(client, sid, max_time_s=20, k_initial=16, controller={"kind": "policy", "policy_id": "A_IoT_PPO_LSTM"})
    assert run["status"] == "completed"
    assert run["summary"]["controller_kind"] == "policy"
    assert run["summary"]["policy_id"] == "A_IoT_PPO_LSTM"
    assert run["summary"]["identified_total"] > 0


def test_unknown_policy_is_rejected(client: TestClient):
    sid = _init_section(client, device_count=5)
    res = client.post(f"/api/thesis-simulator/sections/{sid}/runs",
                      json={"sync": True, "controller": {"kind": "policy", "policy_id": "does_not_exist"}})
    assert res.status_code == 422
    assert "policy_unavailable" in res.text


def test_training_endpoints(client: TestClient, tmp_path, monkeypatch):
    monkeypatch.setenv("THESIS_TRAINING_OUTPUTS", str(tmp_path))
    run = tmp_path / "ps_ppo_fixed2" / "20260101T000000__a0p5__b0p5__s0"
    (run / "plots").mkdir(parents=True)
    (run / "meta.json").write_text('{"policy_id": "x", "status": "done", "alpha": 0.5, "scale": {"name": "smoke"}}')
    (run / "train_metrics.csv").write_text("timesteps,return\n1,0.5\n2,0.7\n")
    exps = client.get("/api/thesis-simulator/training/experiments").json()
    names = {e["experiment"] for e in exps}
    assert {"ps_ppo_fixed2", "ps_ppo_randomized", "mappo", "ippo", "zero_shot_single"} <= names
    fixed = next(e for e in exps if e["experiment"] == "ps_ppo_fixed2")
    assert fixed["runs"] == 1 and fixed["done"] == 1 and fixed["latest"]["scale"] == "smoke"
    detail = client.get("/api/thesis-simulator/training/experiments/ps_ppo_fixed2").json()
    assert detail["runs"][0]["curve"] == [{"timesteps": 1.0, "return": 0.5}, {"timesteps": 2.0, "return": 0.7}]
    assert client.get("/api/thesis-simulator/training/experiments/..%2Fetc").status_code == 404
    assert client.get("/api/thesis-simulator/training/experiments/nope").status_code == 404


def test_analysis_reachable_completion_times(client: TestClient):
    sid = _init_section(client, device_count=20, readers=[(10.0, 10.0), (40.0, 10.0)])
    run = _run(client, sid, resource={"mode": "tdma"})
    body = client.get(f"/api/thesis-simulator/runs/{run['id']}/analysis").json()
    reach = body["reachable_completion_times"]
    assert set(reach) == set(body["population_completion_times"])
    pop99, reach99 = body["population_completion_times"]["99"], reach["99"]
    assert reach99 is not None
    assert pop99 is None or reach99 <= pop99


def test_dead_training_process_reported_interrupted(tmp_path, monkeypatch):
    import json
    import socket

    from app.thesis_simulator import training_registry as reg

    monkeypatch.setenv("THESIS_TRAINING_OUTPUTS", str(tmp_path))
    run = tmp_path / "exp" / "20260101T000000__a0p5__b0p5__s0"
    run.mkdir(parents=True)
    meta = {"status": "running", "pid": 2**22 + 12345, "host": socket.gethostname()}
    (run / "meta.json").write_text(json.dumps(meta))
    assert reg._run_brief(run)["status"] == "interrupted"
    meta["host"] = "another-host"
    (run / "meta.json").write_text(json.dumps(meta))
    assert reg._run_brief(run)["status"] == "running"
