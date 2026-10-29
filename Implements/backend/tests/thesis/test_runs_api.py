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
        json={"sync": True, "scheme": "periodic", "max_time_s": 5},
    )
    assert res.status_code == 400
    assert res.json()["detail"] == "section_not_initialized"


def test_create_periodic_run_populates_summary(client: TestClient):
    section_id = _init_section(client)
    res = client.post(
        f"/api/thesis-simulator/sections/{section_id}/runs",
        json={"sync": True, "scheme": "periodic", "max_time_s": 5, "seed": 42},
    )
    assert res.status_code == 201, res.text
    body = res.json()
    assert body["status"] == "completed"
    assert body["scheme"] == "periodic"
    assert body["summary"]["total_devices"] == 3
    assert body["summary"]["rounds_total"] >= 1


def test_run_name_create_and_rename(client: TestClient):
    section_id = _init_section(client)
    res = client.post(
        f"/api/thesis-simulator/sections/{section_id}/runs",
        json={
            "sync": True,
            "scheme": "periodic",
            "max_time_s": 2,
            "seed": 1,
            "name": "  baseline-A  ",
        },
    )
    assert res.status_code == 201, res.text
    body = res.json()
    assert body["name"] == "baseline-A"
    assert body["summary"]["name"] == "baseline-A"
    run_id = body["id"]

    renamed = client.post(f"/api/thesis-simulator/runs/{run_id}/name", json={"name": "nightly"})
    assert renamed.status_code == 200, renamed.text
    assert renamed.json()["name"] == "nightly"

    cleared = client.post(f"/api/thesis-simulator/runs/{run_id}/name", json={"name": "   "})
    assert cleared.status_code == 200, cleared.text
    assert cleared.json()["name"] is None

    listed = client.get(f"/api/thesis-simulator/sections/{section_id}/runs")
    assert listed.status_code == 200
    assert listed.json()[0]["run_id"] == run_id
    assert listed.json()[0]["name"] is None


def test_run_scheme_validation(client: TestClient):
    section_id = _init_section(client)
    res = client.post(
        f"/api/thesis-simulator/sections/{section_id}/runs",
        json={"sync": True, "scheme": "weird", "max_time_s": 2},
    )
    assert res.status_code == 422


def test_list_runs_newest_first(client: TestClient):
    section_id = _init_section(client)
    for scheme in ("periodic", "aperiodic", "periodic"):
        client.post(
            f"/api/thesis-simulator/sections/{section_id}/runs",
            json={"sync": True, "scheme": scheme, "max_time_s": 2, "seed": 1},
        )
    res = client.get(f"/api/thesis-simulator/sections/{section_id}/runs")
    assert res.status_code == 200
    assert len(res.json()) == 3


def test_timeline_endpoint(client: TestClient):
    section_id = _init_section(client)
    run_res = client.post(
        f"/api/thesis-simulator/sections/{section_id}/runs",
        json={"sync": True, "scheme": "periodic", "max_time_s": 3, "seed": 7},
    )
    run_id = run_res.json()["id"]
    scene = client.get(f"/api/thesis-simulator/sections/{section_id}").json()
    device_id = next(p["id"] for p in scene["placements"] if p["kind"] == "device")
    tl = client.get(f"/api/thesis-simulator/runs/{run_id}/device/{device_id}/timeline")
    assert tl.status_code == 200
    body = tl.json()
    assert body["device_id"] == device_id
    assert body["final_state"] in {"identified", "dropped", "unreachable"}
    assert all(a["t_s"] <= b["t_s"] for a, b in zip(body["events"], body["events"][1:]))


def test_device_states_endpoint(client: TestClient):
    section_id = _init_section(client)
    run_id = client.post(
        f"/api/thesis-simulator/sections/{section_id}/runs",
        json={"sync": True, "scheme": "periodic", "max_time_s": 3, "seed": 3},
    ).json()["id"]
    res = client.get(f"/api/thesis-simulator/runs/{run_id}/device-states")
    assert res.status_code == 200
    states = res.json()["states"]
    assert len(states) >= 3
    assert set(states.values()).issubset({"identified", "dropped", "unreachable"})


def test_cascade_delete(client: TestClient):
    section_id = _init_section(client)
    run_id = client.post(
        f"/api/thesis-simulator/sections/{section_id}/runs",
        json={"sync": True, "scheme": "periodic", "max_time_s": 2, "seed": 1},
    ).json()["id"]
    assert client.delete(f"/api/thesis-simulator/runs/{run_id}").status_code == 204
    assert client.get(f"/api/thesis-simulator/runs/{run_id}").status_code == 404


def test_device_events_pagination(client: TestClient):
    section_id = _init_section(client)
    run_id = client.post(
        f"/api/thesis-simulator/sections/{section_id}/runs",
        json={"sync": True, "scheme": "periodic", "max_time_s": 3, "seed": 11},
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
        json={"sync": True, "scheme": "aperiodic", "max_time_s": 3, "seed": 99},
    ).json()
    b = client.post(
        f"/api/thesis-simulator/sections/{section_id}/runs",
        json={"sync": True, "scheme": "aperiodic", "max_time_s": 3, "seed": 99},
    ).json()
    assert a["summary"]["identified_total"] == b["summary"]["identified_total"]
    assert a["summary"]["rounds_total"] == b["summary"]["rounds_total"]


# ------------------------------------------------------------------ live runs

import json
import time


def _wait_status(client: TestClient, run_id: int, wanted: set[str], timeout_s: float = 60.0) -> dict:
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        body = client.get(f"/api/thesis-simulator/runs/{run_id}").json()
        if body["status"] in wanted:
            return body
        time.sleep(0.05)
    raise AssertionError(f"run {run_id} never reached {wanted}")


def _live_section(client: TestClient) -> int:
    placements = [
        {"kind": "device", "subtype": ("1", "2a", "2b")[i % 3], "x_m": 15 + (i % 5), "y_m": 15 + (i // 5), "params": {}}
        for i in range(15)
    ]
    placements.append({"kind": "device", "subtype": "2b", "x_m": 1990, "y_m": 55, "params": {}})  # beyond any coverage
    placements.append({"kind": "radar", "subtype": None, "x_m": 18, "y_m": 17, "params": {}})
    created = client.post(
        "/api/thesis-simulator/sections",
        json={"name": "live", "width_m": 2000, "height_m": 60, "placements": placements},
    )
    sid = created.json()["id"]
    client.patch(f"/api/thesis-simulator/sections/{sid}", json={"status": "initialized"})
    return sid


def test_pause_resume_matches_uninterrupted_run(client: TestClient):
    sid = _live_section(client)
    base = {"scheme": "periodic", "max_time_s": 30, "seed": 21, "k_initial": 16}
    reference = client.post(f"/api/thesis-simulator/sections/{sid}/runs", json={**base, "sync": True}).json()
    assert reference["status"] == "completed"

    run = client.post(f"/api/thesis-simulator/sections/{sid}/runs", json={**base, "speed": 2.0}).json()
    time.sleep(0.3)
    paused = client.post(f"/api/thesis-simulator/runs/{run['id']}/pause")
    assert paused.status_code == 200, paused.text
    assert paused.json()["status"] == "paused"

    client.post(f"/api/thesis-simulator/runs/{run['id']}/speed", json={"speed": None})
    resumed = client.post(f"/api/thesis-simulator/runs/{run['id']}/resume")
    assert resumed.status_code == 200, resumed.text
    done = _wait_status(client, run["id"], {"completed", "failed"})
    assert done["status"] == "completed", done.get("error_detail")
    for key in ("identified_total", "dropped_count", "rounds_total", "died_count"):
        assert done["summary"][key] == reference["summary"][key], key


def test_open_ended_run_ends_with_far_device_unreachable(client: TestClient):
    sid = _live_section(client)
    body = client.post(
        f"/api/thesis-simulator/sections/{sid}/runs",
        json={"sync": True, "scheme": "aperiodic", "seed": 4, "k_initial": 16, "stall_timeout_s": 60},
    ).json()
    assert body["status"] == "completed"
    s = body["summary"]
    assert s["unreachable_count"] == 1
    assert s["identified_total"] + s["dropped_count"] == s["total_devices"]


def test_stop_really_stops(client: TestClient):
    sid = _live_section(client)
    run = client.post(
        f"/api/thesis-simulator/sections/{sid}/runs",
        json={"scheme": "periodic", "max_time_s": 600, "seed": 2, "k_initial": 16, "speed": 1.0},
    ).json()
    time.sleep(0.2)
    stopped = client.post(f"/api/thesis-simulator/runs/{run['id']}/stop")
    assert stopped.status_code == 200, stopped.text
    assert stopped.json()["status"] == "stopped"
    seq_a = client.get(f"/api/thesis-simulator/runs/{run['id']}/rounds").json()
    time.sleep(0.3)
    seq_b = client.get(f"/api/thesis-simulator/runs/{run['id']}/rounds").json()
    assert len(seq_a) == len(seq_b)
    assert client.post(f"/api/thesis-simulator/runs/{run['id']}/resume").status_code == 409


def test_stream_sends_snapshot_ticks_and_done(client: TestClient):
    sid = _live_section(client)
    run = client.post(
        f"/api/thesis-simulator/sections/{sid}/runs",
        json={"scheme": "periodic", "max_time_s": 8, "seed": 5, "k_initial": 16, "speed": 20.0},
    ).json()
    events: list[tuple[str, dict]] = []
    with client.stream("GET", f"/api/thesis-simulator/runs/{run['id']}/stream") as res:
        assert res.headers["content-type"].startswith("text/event-stream")
        name = None
        for line in res.iter_lines():
            if line.startswith("event:"):
                name = line.split(":", 1)[1].strip()
            elif line.startswith("data:") and name:
                events.append((name, json.loads(line.split(":", 1)[1])))
                if name == "done":
                    break
    names = [n for n, _ in events]
    assert names[0] == "snapshot"
    assert names[-1] == "done"
    snap = events[0][1]
    assert len(snap["device_ids"]) == 16
    assert "tick" in names
    ticks = [d for n, d in events if n == "tick"]
    assert any(t["rounds"] for t in ticks)
    assert events[-1][1]["status"] == "completed"


def test_stream_of_finished_run_is_snapshot_then_done(client: TestClient):
    sid = _live_section(client)
    run = client.post(
        f"/api/thesis-simulator/sections/{sid}/runs",
        json={"sync": True, "scheme": "periodic", "max_time_s": 3, "seed": 5, "k_initial": 16},
    ).json()
    with client.stream("GET", f"/api/thesis-simulator/runs/{run['id']}/stream") as res:
        text_body = "".join(res.iter_text())
    assert text_body.index("event: snapshot") < text_body.index("event: done")
    snap = client.get(f"/api/thesis-simulator/runs/{run['id']}/snapshot").json()
    assert len(snap["device_ids"]) == 16


def _event_rows(run_id: int) -> int:
    from app.thesis_simulator.db import get_engine

    with get_engine().connect() as conn:
        dev = conn.execute(text("SELECT count(*) FROM thesis_device_events WHERE run_id = :r"), {"r": run_id}).scalar()
        rdr = conn.execute(text("SELECT count(*) FROM thesis_reader_events WHERE run_id = :r"), {"r": run_id}).scalar()
    return int(dev) + int(rdr)


def test_deleting_run_or_section_removes_its_events(client: TestClient):
    sid = _live_section(client)
    body = {"sync": True, "scheme": "periodic", "max_time_s": 3, "seed": 1, "k_initial": 16}
    run_a = client.post(f"/api/thesis-simulator/sections/{sid}/runs", json=body).json()["id"]
    run_b = client.post(f"/api/thesis-simulator/sections/{sid}/runs", json=body).json()["id"]
    assert _event_rows(run_a) > 0 and _event_rows(run_b) > 0

    assert client.delete(f"/api/thesis-simulator/runs/{run_a}").status_code == 204
    deadline = time.monotonic() + 10
    while _event_rows(run_a) and time.monotonic() < deadline:  # hard delete runs as a background task
        time.sleep(0.05)
    assert _event_rows(run_a) == 0

    assert client.delete(f"/api/thesis-simulator/sections/{sid}").status_code in (200, 204)
    assert _event_rows(run_b) == 0


def test_device_map_and_identifications(client: TestClient):
    sid = _live_section(client)
    run = client.post(
        f"/api/thesis-simulator/sections/{sid}/runs",
        json={"sync": True, "scheme": "periodic", "max_time_s": 10, "seed": 3, "k_initial": 16},
    ).json()
    dm = client.get(f"/api/thesis-simulator/runs/{run['id']}/device-map").json()
    assert len(dm["device_ids"]) == len(dm["subtypes"]) == 16
    (cover,) = dm["coverage"].values()
    assert 15 not in cover  # the far device (last index) is outside the only reader's disk
    ids = client.get(f"/api/thesis-simulator/runs/{run['id']}/identifications").json()
    assert len(ids["t"]) == run["summary"]["identified_total"]
    assert ids["t"] == sorted(ids["t"])
    assert set(ids["device"]) <= set(cover)
