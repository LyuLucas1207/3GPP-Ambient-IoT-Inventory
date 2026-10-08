from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)
BASE = "/api/aperiodic-simulator"

SMALL = {"num_devices": 300, "seed": 3, "max_time_s": 120.0, "L_fixed": 8}


def test_aperiodic_routes_are_namespaced():
    paths = set(client.get("/openapi.json").json()["paths"])
    ap = {p for p in paths if p.startswith(BASE)}
    assert f"{BASE}/simulate" in ap
    assert f"{BASE}/runs/{{run_id}}/controllers/{{controller}}/devices/{{device_id}}/trace" in ap
    for p in paths:
        assert p == "/api/health" or p.startswith("/api/simulator/") or p.startswith(BASE + "/"), p


def test_paper_config_and_about():
    cfg = client.get(f"{BASE}/config/paper").json()
    assert cfg["lmax"]["Lmax"] == 83
    assert {t["name"] for t in cfg["device_types"]} == {"1", "2a", "2b"}
    assert client.get(f"{BASE}/about").status_code == 200


def test_legacy_strategy_payload_is_rejected():
    res = client.post(f"{BASE}/simulate", json={"strategies": ["em"], "paging_mode": "em"})
    assert res.status_code == 422
    res = client.post(f"{BASE}/simulate", json={**SMALL, "controller": "em"})
    assert res.status_code == 422


def test_invalid_combinations_return_422():
    bad = [
        {"ppo_enabled": True, "paging_mode": "periodic", "controller": "recurrent_ppo", "L_mode": "adaptive"},
        {"controller": "recurrent_ppo"},
        {"paging_mode": "aperiodic", "N_g": 4},
        {"controller": "pfsa_pze", "L_mode": "adaptive"},
        {"L_fixed": 84},
        {"runtime_mode": "interactive", "num_episodes": 2},
        {"num_devices": 15001},
    ]
    for b in bad:
        assert client.post(f"{BASE}/simulate", json={**SMALL, **b}).status_code == 422, b


def test_interactive_run_and_device_trace():
    res = client.post(f"{BASE}/simulate", json=SMALL)
    assert res.status_code == 200
    data = res.json()
    assert data["controller"] == "pfsa_pze"
    assert data["metrics"]["n_eff"] > 0
    assert data["rounds"] and all(r["L"] == 8 for r in data["rounds"])
    assert data["cbra_inspect"]
    dev = next(d for d in data["devices"] if d["traced"])
    tr = client.get(f"{BASE}/runs/{data['run_id']}/controllers/pfsa_pze/devices/{dev['id']}/trace")
    assert tr.status_code == 200
    assert tr.json()["segments"]
    assert client.get(f"{BASE}/runs/nope/controllers/pfsa_pze/devices/0/trace").status_code == 404


def test_periodic_baseline_run():
    body = {**SMALL, "paging_mode": "periodic", "N_g": 2}
    data = client.post(f"{BASE}/simulate", json=body).json()
    assert data["config"]["paging_mode"] == "periodic"
    assert any(r.get("group") is not None for r in data["rounds"])


def test_ppo_status_is_honest():
    st = client.get(f"{BASE}/ppo/status").json()
    assert "train_command" in st
    if not st["available"]:
        body = {**SMALL, "ppo_enabled": True, "controller": "recurrent_ppo", "L_mode": "adaptive"}
        assert client.post(f"{BASE}/simulate", json=body).status_code == 409
    else:
        assert st["training_steps"] > 0 and len(st["sha256"]) == 64


def test_frontend_clients_use_their_own_namespace():
    import re
    from pathlib import Path

    src = Path(__file__).resolve().parents[3] / "frontend" / "src"
    if not src.exists():
        return
    urls = {}
    for f in list(src.rglob("*.ts")) + list(src.rglob("*.tsx")):
        for m in re.finditer(r"['\"`](/api/[A-Za-z0-9_\-/{}$.]*)", f.read_text()):
            urls.setdefault(f.relative_to(src).as_posix(), set()).add(m.group(1))
    assert urls, "no API URLs found in the frontend"
    for path, found in urls.items():
        for u in found:
            assert u == "/api/health" or u.startswith("/api/simulator") or u.startswith(BASE), (path, u)
    ap = urls.get("api/aperiodicSimulator.ts", set())
    assert ap and all(u.startswith(BASE) for u in ap)
    legacy = urls.get("api/simulator.ts", set())
    assert legacy and all(u.startswith("/api/simulator") for u in legacy)


def test_unknown_reproduce_target():
    assert client.post(f"{BASE}/reproduce/figure99", json={}).status_code in {404, 422}
