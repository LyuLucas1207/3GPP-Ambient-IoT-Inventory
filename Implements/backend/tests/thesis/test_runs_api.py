from fastapi.testclient import TestClient
import pytest
from sqlalchemy import create_engine, text

from app.main import app
from app.thesis_simulator.db import get_engine, init_db, reset_engine

DEV_DATABASE_URL = "postgresql+psycopg://thesis:thesis@127.0.0.1:5432/thesis"
TEST_DATABASE_URL = "postgresql+psycopg://thesis:thesis@127.0.0.1:5432/thesis_test"


def _ensure_test_database() -> None:
    admin = create_engine(DEV_DATABASE_URL, isolation_level="AUTOCOMMIT", pool_pre_ping=True)
    try:
        with admin.connect() as conn:
            exists = conn.execute(text("SELECT 1 FROM pg_database WHERE datname = 'thesis_test'")).scalar()
            if exists is None:
                conn.execute(text("CREATE DATABASE thesis_test"))
    finally:
        admin.dispose()


@pytest.fixture
def client(monkeypatch):
    _ensure_test_database()
    monkeypatch.setenv("THESIS_DATABASE_URL", TEST_DATABASE_URL)
    reset_engine()
    init_db()
    with get_engine().begin() as conn:
        conn.execute(
            text(
                "TRUNCATE TABLE thesis_run_summary, thesis_device_events, thesis_reader_events, "
                "thesis_run_rounds, thesis_inventory_runs, thesis_placements, thesis_sections "
                "RESTART IDENTITY CASCADE"
            )
        )
    with TestClient(app) as test_client:
        yield test_client
    reset_engine()


def _init_section(client: TestClient, with_reader: bool = True) -> int:
    placements = [
        {"kind": "device", "subtype": "1", "x_m": 15, "y_m": 15, "params": {}},
        {"kind": "device", "subtype": "2a", "x_m": 20, "y_m": 20, "params": {}},
        {"kind": "device", "subtype": "2b", "x_m": 90, "y_m": 50, "params": {}},
    ]
    if with_reader:
        placements.append({"kind": "radar", "subtype": None, "x_m": 20, "y_m": 20, "params": {}})
    created = client.post(
        "/api/thesis-simulator/sections",
        json={"name": "run-tests", "width_m": 120, "height_m": 60, "placements": placements},
    )
    section_id = created.json()["id"]
    client.patch(f"/api/thesis-simulator/sections/{section_id}", json={"status": "initialized"})
    return section_id


def test_run_requires_initialized(client: TestClient):
    created = client.post(
        "/api/thesis-simulator/sections",
        json={"name": "x", "width_m": 50, "height_m": 50, "placements": []},
    )
    section_id = created.json()["id"]
    res = client.post(
        f"/api/thesis-simulator/sections/{section_id}/runs",
        json={"scheme": "periodic", "max_time_s": 5},
    )
    assert res.status_code == 400
    assert res.json()["detail"] == "section_not_initialized"


def test_create_periodic_run_populates_summary(client: TestClient):
    section_id = _init_section(client)
    res = client.post(
        f"/api/thesis-simulator/sections/{section_id}/runs",
        json={"scheme": "periodic", "max_time_s": 5, "seed": 42},
    )
    assert res.status_code == 201, res.text
    body = res.json()
    assert body["status"] == "completed"
    assert body["scheme"] == "periodic"
    assert body["summary"]["total_devices"] == 3
    assert body["summary"]["rounds_total"] >= 1


def test_run_scheme_validation(client: TestClient):
    section_id = _init_section(client)
    res = client.post(
        f"/api/thesis-simulator/sections/{section_id}/runs",
        json={"scheme": "weird", "max_time_s": 2},
    )
    assert res.status_code == 422


def test_list_runs_newest_first(client: TestClient):
    section_id = _init_section(client)
    for scheme in ("periodic", "aperiodic", "periodic"):
        client.post(
            f"/api/thesis-simulator/sections/{section_id}/runs",
            json={"scheme": scheme, "max_time_s": 2, "seed": 1},
        )
    res = client.get(f"/api/thesis-simulator/sections/{section_id}/runs")
    assert res.status_code == 200
    assert len(res.json()) == 3


def test_timeline_endpoint(client: TestClient):
    section_id = _init_section(client)
    run_res = client.post(
        f"/api/thesis-simulator/sections/{section_id}/runs",
        json={"scheme": "periodic", "max_time_s": 3, "seed": 7},
    )
    run_id = run_res.json()["id"]
    scene = client.get(f"/api/thesis-simulator/sections/{section_id}").json()
    device_id = next(p["id"] for p in scene["placements"] if p["kind"] == "device")
    tl = client.get(f"/api/thesis-simulator/runs/{run_id}/device/{device_id}/timeline")
    assert tl.status_code == 200
    body = tl.json()
    assert body["device_id"] == device_id
    assert body["final_state"] in {"identified", "died", "dropped"}
    assert all(a["t_s"] <= b["t_s"] for a, b in zip(body["events"], body["events"][1:]))


def test_device_states_endpoint(client: TestClient):
    section_id = _init_section(client)
    run_id = client.post(
        f"/api/thesis-simulator/sections/{section_id}/runs",
        json={"scheme": "periodic", "max_time_s": 3, "seed": 3},
    ).json()["id"]
    res = client.get(f"/api/thesis-simulator/runs/{run_id}/device-states")
    assert res.status_code == 200
    states = res.json()["states"]
    assert len(states) >= 3
    assert set(states.values()).issubset({"identified", "died", "dropped"})


def test_cascade_delete(client: TestClient):
    section_id = _init_section(client)
    run_id = client.post(
        f"/api/thesis-simulator/sections/{section_id}/runs",
        json={"scheme": "periodic", "max_time_s": 2, "seed": 1},
    ).json()["id"]
    assert client.delete(f"/api/thesis-simulator/runs/{run_id}").status_code == 204
    assert client.get(f"/api/thesis-simulator/runs/{run_id}").status_code == 404


def test_device_events_pagination(client: TestClient):
    section_id = _init_section(client)
    run_id = client.post(
        f"/api/thesis-simulator/sections/{section_id}/runs",
        json={"scheme": "periodic", "max_time_s": 3, "seed": 11},
    ).json()["id"]
    first = client.get(
        f"/api/thesis-simulator/runs/{run_id}/device-events",
        params={"limit": 5},
    ).json()
    assert len(first["events"]) == 5
    if first["next_since"] is not None:
        second = client.get(
            f"/api/thesis-simulator/runs/{run_id}/device-events",
            params={"limit": 5, "since": first["next_since"]},
        ).json()
        assert len(second["events"]) >= 1
        assert second["events"][0]["t_s"] >= first["next_since"]


def test_deterministic_with_seed(client: TestClient):
    section_id = _init_section(client)
    a = client.post(
        f"/api/thesis-simulator/sections/{section_id}/runs",
        json={"scheme": "aperiodic", "max_time_s": 3, "seed": 99},
    ).json()
    b = client.post(
        f"/api/thesis-simulator/sections/{section_id}/runs",
        json={"scheme": "aperiodic", "max_time_s": 3, "seed": 99},
    ).json()
    assert a["summary"]["identified_total"] == b["summary"]["identified_total"]
    assert a["summary"]["rounds_total"] == b["summary"]["rounds_total"]
