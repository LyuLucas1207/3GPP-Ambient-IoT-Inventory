from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_is_global():
    assert client.get("/api/health").json() == {"status": "ok"}


def test_legacy_endpoints_live_under_api_simulator():
    assert client.get("/api/simulator/about").status_code == 200
    assert client.get("/api/simulator/config/paper").status_code == 200
    assert client.get("/api/simulator/config/fig5b-reference").status_code == 200


def test_old_unnamespaced_endpoints_are_gone():
    assert client.get("/api/about").status_code == 404
    assert client.get("/api/config/paper").status_code == 404
    assert client.post("/api/simulate", json={}).status_code in {404, 405}


def test_legacy_trace_route_uses_runs_namespace():
    paths = set(client.get("/openapi.json").json()["paths"])
    assert "/api/simulator/runs/{run_id}/strategies/{strategy}/devices/{device_id}/trace" in paths
    assert not any(p.startswith("/api/simulation/") for p in paths)


def test_legacy_simulate_small_run():
    body = {
        "num_devices": 20,
        "strategies": ["em"],
        "max_time_s": 2.0,
        "collect_snapshots": False,
        "collect_paging_events": False,
    }
    res = client.post("/api/simulator/simulate", json=body)
    assert res.status_code == 200
    payload = res.json()
    assert payload["energy_trace"]["path"].startswith("/api/simulator/runs/")
