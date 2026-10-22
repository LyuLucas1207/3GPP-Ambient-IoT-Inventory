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


def _init_section(client: TestClient, *, device_count: int = 10, readers: list[tuple[float, float]] | None = None) -> int:
    readers = readers or [(10.0, 10.0)]
    placements = []
    for i in range(device_count):
        x = 2.0 + (i * 2.0) % 18
        y = 2.0 + ((i * 3.0) % 15)
        placements.append({"kind": "device", "subtype": "1" if i % 3 == 0 else ("2a" if i % 3 == 1 else "2b"),
                           "x_m": x, "y_m": y, "params": {}})
    for (rx, ry) in readers:
        placements.append({"kind": "radar", "subtype": None, "x_m": rx, "y_m": ry, "params": {}})
    created = client.post(
        "/api/thesis-simulator/sections",
        json={"name": "fsa", "width_m": 60, "height_m": 40, "placements": placements},
    )
    sid = created.json()["id"]
    client.patch(f"/api/thesis-simulator/sections/{sid}", json={"status": "initialized"})
    return sid


def test_small_single_reader(client: TestClient):
    sid = _init_section(client, device_count=10)
    res = client.post(
        f"/api/thesis-simulator/sections/{sid}/runs",
        json={"sync": True, "scheme": "periodic", "max_time_s": 5, "seed": 42, "use_grouping": False, "k_initial": 16},
    )
    assert res.status_code == 201, res.text
    body = res.json()
    assert body["status"] == "completed"
    s = body["summary"]
    assert s["total_devices"] == 10
    assert s["identified_total"] + s["dropped_count"] == 10
    assert s["rounds_total"] >= 1


def test_two_readers_fdma_dcm_exclusivity(client: TestClient):
    sid = _init_section(client, device_count=20, readers=[(15.0, 15.0), (16.0, 16.0)])
    run_id = client.post(
        f"/api/thesis-simulator/sections/{sid}/runs",
        json={"sync": True, "scheme": "periodic", "max_time_s": 4, "seed": 7, "use_grouping": True, "g": 2, "k_initial": 16},
    ).json()["id"]
    # Walk every device's timeline; for identified devices, confirm reader_id of
    # the identified event is one of the two readers (not null).
    scene = client.get(f"/api/thesis-simulator/sections/{sid}").json()
    device_ids = [p["id"] for p in scene["placements"] if p["kind"] == "device"]
    reader_ids = {p["id"] for p in scene["placements"] if p["kind"] == "radar"}
    assert len(reader_ids) == 2
    saw_any_identified = False
    for did in device_ids:
        tl = client.get(f"/api/thesis-simulator/runs/{run_id}/device/{did}/timeline").json()
        if tl["final_state"] == "identified":
            saw_any_identified = True
            ident_evt = next(e for e in tl["events"] if e["event_type"] == "identified")
            assert ident_evt["reader_id"] in reader_ids
    assert saw_any_identified


def test_deterministic_with_seed(client: TestClient):
    sid = _init_section(client, device_count=12)
    a = client.post(
        f"/api/thesis-simulator/sections/{sid}/runs",
        json={"sync": True, "scheme": "periodic", "max_time_s": 3, "seed": 123, "use_grouping": False, "k_initial": 16},
    ).json()
    b = client.post(
        f"/api/thesis-simulator/sections/{sid}/runs",
        json={"sync": True, "scheme": "periodic", "max_time_s": 3, "seed": 123, "use_grouping": False, "k_initial": 16},
    ).json()
    assert a["summary"]["identified_total"] == b["summary"]["identified_total"]
    assert a["summary"]["rounds_total"] == b["summary"]["rounds_total"]
    assert a["summary"]["died_count"] == b["summary"]["died_count"]


def test_periodic_vs_aperiodic(client: TestClient):
    sid = _init_section(client, device_count=15)
    p = client.post(
        f"/api/thesis-simulator/sections/{sid}/runs",
        json={"sync": True, "scheme": "periodic", "max_time_s": 4, "seed": 11, "use_grouping": False, "k_initial": 16},
    ).json()
    a = client.post(
        f"/api/thesis-simulator/sections/{sid}/runs",
        json={"sync": True, "scheme": "aperiodic", "max_time_s": 4, "seed": 11, "use_grouping": False, "k_initial": 16},
    ).json()
    assert p["status"] == "completed"
    assert a["status"] == "completed"


def test_energy_series_in_range(client: TestClient):
    sid = _init_section(client, device_count=6)
    run_id = client.post(
        f"/api/thesis-simulator/sections/{sid}/runs",
        json={"sync": True, "scheme": "periodic", "max_time_s": 3, "seed": 5, "use_grouping": False, "k_initial": 8},
    ).json()["id"]
    scene = client.get(f"/api/thesis-simulator/sections/{sid}").json()
    device_ids = [p["id"] for p in scene["placements"] if p["kind"] == "device"]
    for did in device_ids[:3]:
        tl = client.get(f"/api/thesis-simulator/runs/{run_id}/device/{did}/timeline").json()
        for t_s, e_j in tl["energy_series"]:
            # ECAP_2 is the biggest cap (25µJ for Device2a/2b); loose upper bound.
            assert -1e-9 <= e_j <= 30e-6
