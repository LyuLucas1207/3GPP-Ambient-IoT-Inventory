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
        conn.execute(text("TRUNCATE TABLE thesis_placements, thesis_sections RESTART IDENTITY CASCADE"))
    with TestClient(app) as test_client:
        yield test_client
    reset_engine()


def _device(x=10, y=10, subtype="1"):
    return {"kind": "device", "subtype": subtype, "x_m": x, "y_m": y, "params": {}}


def _station(x=25, y=25):
    return {"kind": "station", "subtype": None, "x_m": x, "y_m": y, "params": {}}


def test_catalog_lists_five_shapes(client: TestClient):
    res = client.get("/api/thesis-simulator/catalog")
    assert res.status_code == 200
    rows = res.json()
    assert [(row["kind"], row["subtype"], row["shape"]) for row in rows] == [
        ("device", "1", "circle"),
        ("device", "2a", "circle"),
        ("device", "2b", "circle"),
        ("station", None, "diamond"),
        ("radar", None, "hexagon"),
    ]
    radar = rows[-1]
    assert "radius_m" not in radar["defaults"]
    assert radar["defaults"]["show_range"] is False
    assert set(radar["derived_ranges"]) == {"1", "2a", "2b"}
    assert radar["derived_ranges"]["1"] > 30
    assert radar["derived_ranges"]["2a"] > radar["derived_ranges"]["1"]
    station = next(row for row in rows if row["kind"] == "station")
    assert "radius_m" not in station["defaults"]
    assert station["defaults"]["show_range"] is False
    assert station["derived_ranges"]["1"] > 0
    assert rows[0]["defaults"]["rx_sensitivity_dbm"] == -36
    assert rows[2]["defaults"]["uplink"] == "active"


def test_save_then_patch_one_row(client: TestClient):
    created = client.post(
        "/api/thesis-simulator/sections",
        json={
            "name": " Floor A ",
            "width_m": 100,
            "height_m": 50,
            "placements": [_device(10, 12), _device(20, 15, "2a"), _station()],
        },
    )
    assert created.status_code == 200
    body = created.json()
    assert body["name"] == "Floor A"
    assert len(body["placements"]) == 3
    station = next(item for item in body["placements"] if item["kind"] == "station")
    other_id = next(item["id"] for item in body["placements"] if item["kind"] == "device")

    converted = client.patch(
        f"/api/thesis-simulator/sections/{body['id']}/placements/{station['id']}",
        json={"kind": "radar"},
    )
    assert converted.status_code == 200
    radar = converted.json()
    assert radar["id"] == station["id"]
    assert radar["kind"] == "radar"
    assert "radius_m" not in radar["params"]
    assert radar["params"]["show_range"] is False
    assert radar["params"]["tx_power_dbm"] == 33
    assert set(radar["derived"]["effective_range_m"]) == {"1", "2a", "2b"}

    tuned = client.patch(
        f"/api/thesis-simulator/sections/{body['id']}/placements/{radar['id']}",
        json={"params": {"extra_attenuation_db": 4.5, "radius_m": 28, "show_range": True}},
    )
    assert tuned.status_code == 200
    assert tuned.json()["params"]["extra_attenuation_db"] == 4.5
    assert "radius_m" not in tuned.json()["params"]
    assert tuned.json()["params"]["show_range"] is True

    listed = client.get("/api/thesis-simulator/sections")
    assert listed.status_code == 200
    assert listed.json()[0]["placement_count"] == 3

    loaded = client.get(f"/api/thesis-simulator/sections/{body['id']}")
    untouched = next(item for item in loaded.json()["placements"] if item["id"] == other_id)
    assert untouched["params"]["rx_sensitivity_dbm"] == -36
    kept = next(item for item in loaded.json()["placements"] if item["id"] == radar["id"])
    assert kept["params"]["extra_attenuation_db"] == 4.5

    back = client.patch(
        f"/api/thesis-simulator/sections/{body['id']}/placements/{radar['id']}",
        json={"kind": "station"},
    )
    assert back.status_code == 200
    assert back.json()["kind"] == "station"
    assert back.json()["id"] == station["id"]
    assert back.json()["params"]["extra_attenuation_db"] == 4.5
    assert "radius_m" not in back.json()["params"]


def test_device_subtype_change_uses_new_defaults(client: TestClient):
    created = client.post(
        "/api/thesis-simulator/sections",
        json={"name": "Types", "width_m": 100, "height_m": 50, "placements": [_device()]},
    )
    section_id = created.json()["id"]
    device_id = created.json()["placements"][0]["id"]
    changed = client.patch(
        f"/api/thesis-simulator/sections/{section_id}/placements/{device_id}",
        json={"subtype": "2b"},
    )
    assert changed.status_code == 200
    params = changed.json()["params"]
    assert changed.json()["subtype"] == "2b"
    assert params["rx_sensitivity_dbm"] == -70
    assert params["uplink"] == "active"
    assert params["active_tx_power_dbm"] == -20
    assert params["uses_wurx"] is True


def test_new_section_starts_initializing_and_save_marks_initialized(client: TestClient):
    created = client.post(
        "/api/thesis-simulator/sections",
        json={"name": "Fresh", "width_m": 100, "height_m": 50, "placements": []},
    )
    assert created.status_code == 200
    assert created.json()["status"] == "initializing"
    section_id = created.json()["id"]
    saved = client.patch(f"/api/thesis-simulator/sections/{section_id}", json={"status": "initialized"})
    assert saved.status_code == 200
    assert saved.json()["status"] == "initialized"
    scaled = client.patch(f"/api/thesis-simulator/sections/{section_id}", json={"marker_scale": 2.5})
    assert scaled.status_code == 200
    assert scaled.json()["marker_scale"] == 2.5
    assert client.patch(f"/api/thesis-simulator/sections/{section_id}", json={"marker_scale": 0}).status_code == 200
    assert client.patch(f"/api/thesis-simulator/sections/{section_id}", json={"marker_scale": 6}).status_code == 422
    listed = client.get("/api/thesis-simulator/sections").json()
    assert listed[0]["status"] == "initialized"


def test_resize_rejects_points_outside_and_keeps_size(client: TestClient):
    created = client.post(
        "/api/thesis-simulator/sections",
        json={"name": "Tight", "width_m": 100, "height_m": 50, "placements": [_device(90, 40)]},
    )
    section_id = created.json()["id"]
    rejected = client.patch(
        f"/api/thesis-simulator/sections/{section_id}",
        json={"width_m": 80},
    )
    assert rejected.status_code == 400
    assert rejected.json()["detail"] == "outside_bounds"
    loaded = client.get(f"/api/thesis-simulator/sections/{section_id}")
    assert loaded.json()["width_m"] == 100
    assert loaded.json()["height_m"] == 50


def test_single_add_and_delete_do_not_replace_the_scene(client: TestClient):
    created = client.post(
        "/api/thesis-simulator/sections",
        json={"name": "Grow", "width_m": 100, "height_m": 50, "placements": [_device(1, 1), _device(2, 2)]},
    )
    section_id = created.json()["id"]
    added = client.post(
        f"/api/thesis-simulator/sections/{section_id}/placements",
        json={"kind": "radar", "x_m": 25, "y_m": 25, "params": {}},
    )
    assert added.status_code == 200
    assert added.json()["kind"] == "radar"
    assert "radius_m" not in added.json()["params"]
    assert set(added.json()["derived"]["effective_range_m"]) == {"1", "2a", "2b"}
    removed = client.delete(
        f"/api/thesis-simulator/sections/{section_id}/placements/{created.json()['placements'][0]['id']}"
    )
    assert removed.status_code == 204
    loaded = client.get(f"/api/thesis-simulator/sections/{section_id}")
    assert len(loaded.json()["placements"]) == 2
    assert {item["kind"] for item in loaded.json()["placements"]} == {"device", "radar"}


def test_rejects_cross_kind_and_outside_create(client: TestClient):
    created = client.post(
        "/api/thesis-simulator/sections",
        json={"name": "Guard", "width_m": 100, "height_m": 50, "placements": [_device()]},
    )
    section_id = created.json()["id"]
    device_id = created.json()["placements"][0]["id"]
    crossed = client.patch(
        f"/api/thesis-simulator/sections/{section_id}/placements/{device_id}",
        json={"kind": "station"},
    )
    assert crossed.status_code == 400
    assert crossed.json()["detail"] == "device_kind_locked"

    outside = client.post(
        "/api/thesis-simulator/sections",
        json={"name": "Out", "width_m": 10, "height_m": 10, "placements": [_device(11, 1)]},
    )
    assert outside.status_code == 400
    assert outside.json()["detail"] == "outside_bounds"
    assert client.get("/api/thesis-simulator/sections").json() == [
        {
            "id": section_id,
            "name": "Guard",
            "width_m": 100,
            "height_m": 50,
            "placement_count": 1,
            "status": "initializing",
            "updated_at": client.get("/api/thesis-simulator/sections").json()[0]["updated_at"],
        }
    ]


def test_delete_section_removes_its_placements(client: TestClient):
    created = client.post(
        "/api/thesis-simulator/sections",
        json={"name": "Gone", "width_m": 100, "height_m": 50, "placements": [_device(), _station()]},
    )
    section_id = created.json()["id"]
    removed = client.delete(f"/api/thesis-simulator/sections/{section_id}")
    assert removed.status_code == 204
    assert client.get(f"/api/thesis-simulator/sections/{section_id}").status_code == 404
    assert client.get("/api/thesis-simulator/sections").json() == []


def test_batch_creates_devices_in_one_request(client: TestClient):
    created = client.post(
        "/api/thesis-simulator/sections",
        json={"name": "Batch", "width_m": 100, "height_m": 50, "placements": []},
    )
    section_id = created.json()["id"]
    batch = client.post(
        f"/api/thesis-simulator/sections/{section_id}/placements/batch",
        json={"placements": [_device(index, 1) for index in range(1, 6)]},
    )
    assert batch.status_code == 200
    assert len(batch.json()) == 5
    loaded = client.get(f"/api/thesis-simulator/sections/{section_id}")
    assert len(loaded.json()["placements"]) == 5
    locked = client.patch(f"/api/thesis-simulator/sections/{section_id}", json={"status": "initialized"})
    assert locked.status_code == 200
    rejected = client.post(
        f"/api/thesis-simulator/sections/{section_id}/placements/batch",
        json={"placements": [_device(8, 8)]},
    )
    assert rejected.status_code == 400
    assert rejected.json()["detail"] == "bulk_locked"


def test_kind_patch_updates_one_class(client: TestClient):
    created = client.post(
        "/api/thesis-simulator/sections",
        json={
            "name": "Ranges",
            "width_m": 100,
            "height_m": 50,
            "placements": [_station(10, 10), _station(20, 20), _device(5, 5)],
        },
    )
    section_id = created.json()["id"]
    patched = client.patch(
        f"/api/thesis-simulator/sections/{section_id}/placements/batch",
        json={"kind": "station", "subtype": None, "params": {"tx_power_dbm": 35.0}},
    )
    assert patched.status_code == 200
    assert len(patched.json()) == 2
    assert {item["params"]["tx_power_dbm"] for item in patched.json()} == {35.0}
    assert all("radius_m" not in item["params"] for item in patched.json())
    loaded = client.get(f"/api/thesis-simulator/sections/{section_id}").json()
    device = next(item for item in loaded["placements"] if item["kind"] == "device")
    assert "radius_m" not in device["params"]


def test_convert_selected_stations_to_radar(client: TestClient):
    created = client.post(
        "/api/thesis-simulator/sections",
        json={
            "name": "Pick",
            "width_m": 100,
            "height_m": 50,
            "placements": [_station(10, 10), _station(30, 10), _station(50, 10), _device(5, 5)],
        },
    )
    body = created.json()
    stations = [item for item in body["placements"] if item["kind"] == "station"]
    chosen = [stations[0]["id"], stations[2]["id"]]
    converted = client.post(
        f"/api/thesis-simulator/sections/{body['id']}/placements/convert",
        json={"ids": chosen, "kind": "radar"},
    )
    assert converted.status_code == 200
    assert {item["id"]: item["kind"] for item in converted.json()} == {chosen[0]: "radar", chosen[1]: "radar"}
    loaded = client.get(f"/api/thesis-simulator/sections/{body['id']}").json()["placements"]
    kinds = {item["id"]: item["kind"] for item in loaded}
    assert kinds[stations[1]["id"]] == "station"
    assert next(item["kind"] for item in loaded if item["kind"] == "device") == "device"


def test_batch_delete_removes_listed_ids(client: TestClient):
    created = client.post(
        "/api/thesis-simulator/sections",
        json={
            "name": "Clear",
            "width_m": 100,
            "height_m": 50,
            "placements": [_device(1, 1), _device(2, 2), _station(10, 10)],
        },
    )
    body = created.json()
    device_ids = [item["id"] for item in body["placements"] if item["kind"] == "device"]
    removed = client.request(
        "DELETE",
        f"/api/thesis-simulator/sections/{body['id']}/placements/batch",
        json={"ids": device_ids},
    )
    assert removed.status_code == 204
    left = client.get(f"/api/thesis-simulator/sections/{body['id']}").json()["placements"]
    assert [item["kind"] for item in left] == ["station"]


def test_no_bulk_replace_route(client: TestClient):
    paths = [path for path in client.get("/openapi.json").json()["paths"] if path.startswith("/api/thesis-simulator")]
    assert "/api/thesis-simulator/sections" in paths
    assert "/api/thesis-simulator/sections/{section_id}/placements" in paths
    assert not any("regenerate" in path or "replace" in path or "bulk" in path for path in paths)


def test_scenario_defaults_match_inf_dh(client: TestClient):
    res = client.get("/api/thesis-simulator/scenario-defaults")
    assert res.status_code == 200
    body = res.json()
    assert body["width_m"] == 120.0
    assert body["height_m"] == 60.0
    assert body["bs_lattice_spacing_m"] == 20.0
    assert len(body["bs_positions"]) == 18
    assert body["default_n_devices"] == 10_000
    assert body["max_placements"] == 20_000
    assert body["active_bs_xy"] == [50.0, 30.0]


def test_derived_ranges_endpoint_matches_catalog(client: TestClient):
    res = client.post(
        "/api/thesis-simulator/derived-ranges",
        json={"tx_power_dbm": 33.0, "antenna_gain_dbi": 6.0, "extra_attenuation_db": 0.0, "carrier_ghz": 0.9},
    )
    assert res.status_code == 200
    out = res.json()["effective_range_m"]
    assert set(out) == {"1", "2a", "2b"}
    assert out["2a"] > out["1"]
    assert out["2b"] > out["2a"]
    override = client.post(
        "/api/thesis-simulator/derived-ranges",
        json={
            "tx_power_dbm": 33.0,
            "antenna_gain_dbi": 6.0,
            "extra_attenuation_db": 10.0,
            "carrier_ghz": 0.9,
        },
    ).json()["effective_range_m"]
    assert override["1"] < out["1"]
