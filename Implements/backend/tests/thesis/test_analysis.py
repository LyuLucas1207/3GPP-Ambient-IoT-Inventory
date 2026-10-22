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
                "TRUNCATE TABLE thesis_run_checkpoints, thesis_run_snapshots, thesis_run_summary, thesis_device_events, thesis_reader_events, "
                "thesis_run_rounds, thesis_inventory_runs, thesis_placements, thesis_sections "
                "RESTART IDENTITY CASCADE"
            )
        )
    with TestClient(app) as test_client:
        yield test_client
    reset_engine()


def _two_reader_section(client: TestClient, device_count: int = 20) -> tuple[int, list[int]]:
    placements = []
    for i in range(device_count):
        placements.append({
            "kind": "device",
            "subtype": "1" if i % 3 == 0 else ("2a" if i % 3 == 1 else "2b"),
            "x_m": 10.0 + (i % 5) * 4.0,
            "y_m": 10.0 + ((i // 5) % 5) * 4.0,
            "params": {},
        })
    placements.append({"kind": "radar", "subtype": None, "x_m": 12.0, "y_m": 12.0, "params": {}})
    placements.append({"kind": "radar", "subtype": None, "x_m": 24.0, "y_m": 24.0, "params": {}})
    created = client.post(
        "/api/thesis-simulator/sections",
        json={"name": "ana", "width_m": 60, "height_m": 40, "placements": placements},
    )
    sid = created.json()["id"]
    client.patch(f"/api/thesis-simulator/sections/{sid}", json={"status": "initialized"})
    scene = client.get(f"/api/thesis-simulator/sections/{sid}").json()
    reader_ids = [p["id"] for p in scene["placements"] if p["kind"] == "radar"]
    return sid, reader_ids


def test_identification_curve_monotonic(client: TestClient):
    sid, _ = _two_reader_section(client)
    run_id = client.post(
        f"/api/thesis-simulator/sections/{sid}/runs",
        json={"sync": True, "scheme": "periodic", "max_time_s": 5, "seed": 1, "use_grouping": False, "k_initial": 16},
    ).json()["id"]
    analysis = client.get(f"/api/thesis-simulator/runs/{run_id}/analysis").json()
    curve = analysis["identification_curve"]
    for i in range(1, len(curve)):
        assert curve[i][0] >= curve[i - 1][0]
        assert curve[i][1] == curve[i - 1][1] + 1


def test_completion_times_ordered(client: TestClient):
    sid, _ = _two_reader_section(client)
    run_id = client.post(
        f"/api/thesis-simulator/sections/{sid}/runs",
        json={"sync": True, "scheme": "periodic", "max_time_s": 5, "seed": 2, "use_grouping": False, "k_initial": 16},
    ).json()["id"]
    ct = client.get(f"/api/thesis-simulator/runs/{run_id}/analysis").json()["completion_times"]
    nonnull = [v for v in (ct["50"], ct["90"], ct["100"]) if v is not None]
    assert nonnull == sorted(nonnull)


def test_reader_contribution_sum_matches_total(client: TestClient):
    sid, _ = _two_reader_section(client)
    run_id = client.post(
        f"/api/thesis-simulator/sections/{sid}/runs",
        json={"sync": True, "scheme": "periodic", "max_time_s": 5, "seed": 3, "use_grouping": False, "k_initial": 16},
    ).json()["id"]
    analysis = client.get(f"/api/thesis-simulator/runs/{run_id}/analysis").json()
    total = analysis["summary"]["identified_total"]
    assert sum(int(v) for v in analysis["reader_contribution"].values()) == total


def test_disabled_reader_ids_zero_contribution(client: TestClient):
    sid, reader_ids = _two_reader_section(client, device_count=15)
    disabled_rid = reader_ids[1]
    run_id = client.post(
        f"/api/thesis-simulator/sections/{sid}/runs",
        json={
            "scheme": "periodic",
            "max_time_s": 5,
            "sync": True,
            "seed": 4,
            "use_grouping": False,
            "k_initial": 16,
            "disabled_reader_ids": [disabled_rid],
        },
    ).json()["id"]
    analysis = client.get(f"/api/thesis-simulator/runs/{run_id}/analysis").json()
    contrib = analysis["reader_contribution"]
    assert str(disabled_rid) not in contrib or int(contrib[str(disabled_rid)]) == 0


def test_compare_endpoint_rejects_cross_section(client: TestClient):
    sid_a, _ = _two_reader_section(client, device_count=8)
    sid_b, _ = _two_reader_section(client, device_count=8)
    run_a = client.post(
        f"/api/thesis-simulator/sections/{sid_a}/runs",
        json={"sync": True, "scheme": "periodic", "max_time_s": 2, "seed": 5, "use_grouping": False, "k_initial": 16},
    ).json()["id"]
    run_b = client.post(
        f"/api/thesis-simulator/sections/{sid_b}/runs",
        json={"sync": True, "scheme": "periodic", "max_time_s": 2, "seed": 6, "use_grouping": False, "k_initial": 16},
    ).json()["id"]
    res = client.post(
        f"/api/thesis-simulator/sections/{sid_a}/runs/compare",
        json={"run_ids": [run_a, run_b]},
    )
    assert res.status_code == 400
    assert res.json()["detail"] == "run_section_mismatch"


def test_compare_endpoint_same_section(client: TestClient):
    sid, _ = _two_reader_section(client, device_count=12)
    run_ids = []
    for seed in (10, 11):
        run_ids.append(client.post(
            f"/api/thesis-simulator/sections/{sid}/runs",
            json={"sync": True, "scheme": "periodic", "max_time_s": 3, "seed": seed, "use_grouping": False, "k_initial": 16},
        ).json()["id"])
    res = client.post(
        f"/api/thesis-simulator/sections/{sid}/runs/compare",
        json={"run_ids": run_ids},
    )
    assert res.status_code == 200
    body = res.json()
    assert len(body["runs"]) == 2
    assert body["runs"][0]["run_id"] == run_ids[0]
    assert body["runs"][1]["run_id"] == run_ids[1]
