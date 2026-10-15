"""Create and edit one thesis section at a time.

The first save inserts the section and every placement in one transaction.
Later edits update a single row. There is no bulk-replace operation.
"""

from __future__ import annotations

import json
import math
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.schemas.thesis_simulator import (
    PlacementBatchIn,
    PlacementConvertIn,
    PlacementDeleteIn,
    PlacementIn,
    PlacementKindPatch,
    PlacementPatch,
    SectionCreate,
    SectionPatch,
)
from app.thesis_simulator.catalog import spec_for
from app.thesis_simulator.models import ThesisPlacement, ThesisSection, utcnow

INITIALIZING = "initializing"
INITIALIZED = "initialized"
MAX_PLACEMENTS = 20_000
_MAX_PARAMS_CHARS = 16_000
_EDGE = 1e-6


class SceneError(Exception):
    def __init__(self, code: str, status: int = 400) -> None:
        super().__init__(code)
        self.code = code
        self.status = status


def iso(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def placement_out(row: ThesisPlacement) -> dict[str, Any]:
    return {
        "id": row.id,
        "kind": row.kind,
        "subtype": row.subtype,
        "x_m": row.x_m,
        "y_m": row.y_m,
        "params": row.params_json,
    }


def section_out(row: ThesisSection) -> dict[str, Any]:
    return {
        "id": row.id,
        "name": row.name,
        "width_m": row.width_m,
        "height_m": row.height_m,
        "status": row.status,
        "marker_scale": row.marker_scale,
        "created_at": iso(row.created_at),
        "updated_at": iso(row.updated_at),
        "placements": [placement_out(item) for item in row.placements],
    }


def list_sections(db: Session) -> list[dict[str, Any]]:
    rows = db.scalars(select(ThesisSection).order_by(ThesisSection.updated_at.desc(), ThesisSection.id.desc())).all()
    counts = dict(
        db.execute(
            select(ThesisPlacement.section_id, func.count()).group_by(ThesisPlacement.section_id)
        ).all()
    )
    return [
        {
            "id": row.id,
            "name": row.name,
            "width_m": row.width_m,
            "height_m": row.height_m,
            "status": row.status,
            "placement_count": int(counts.get(row.id, 0)),
            "updated_at": iso(row.updated_at),
        }
        for row in rows
    ]


def get_section(db: Session, section_id: int) -> ThesisSection:
    row = db.get(ThesisSection, section_id)
    if row is None:
        raise SceneError("not_found", 404)
    return row


def create_section(db: Session, body: SectionCreate) -> ThesisSection:
    name = _clean_name(body.name)
    if len(body.placements) > MAX_PLACEMENTS:
        raise SceneError("too_many")
    section = ThesisSection(name=name, width_m=body.width_m, height_m=body.height_m, status=INITIALIZING)
    db.add(section)
    db.flush()
    for item in body.placements:
        section.placements.append(_new_placement(section, item))
    db.commit()
    db.refresh(section)
    return section


def update_section(db: Session, section_id: int, body: SectionPatch) -> ThesisSection:
    section = get_section(db, section_id)
    width = section.width_m if body.width_m is None else body.width_m
    height = section.height_m if body.height_m is None else body.height_m
    if width != section.width_m or height != section.height_m:
        for item in section.placements:
            _ensure_inside(item.x_m, item.y_m, width, height)
        section.width_m = width
        section.height_m = height
    if body.name is not None:
        section.name = _clean_name(body.name)
    if body.status is not None:
        if body.status != INITIALIZED:
            raise SceneError("bad_status")
        section.status = INITIALIZED
    if body.marker_scale is not None:
        section.marker_scale = float(body.marker_scale)
    section.updated_at = utcnow()
    db.commit()
    db.refresh(section)
    return section


def add_placement(db: Session, section_id: int, body: PlacementIn) -> ThesisPlacement:
    rows = add_placements(db, section_id, PlacementBatchIn(placements=[body]), allow_initialized=True)
    return rows[0]


def add_placements(
    db: Session,
    section_id: int,
    body: PlacementBatchIn,
    *,
    allow_initialized: bool = False,
) -> list[ThesisPlacement]:
    section = get_section(db, section_id)
    if section.status == INITIALIZED and not allow_initialized:
        raise SceneError("bulk_locked")
    count = db.scalar(
        select(func.count()).select_from(ThesisPlacement).where(ThesisPlacement.section_id == section.id)
    )
    if int(count or 0) + len(body.placements) > MAX_PLACEMENTS:
        raise SceneError("too_many")
    rows = [_new_placement(section, item) for item in body.placements]
    db.add_all(rows)
    section.updated_at = utcnow()
    db.commit()
    for row in rows:
        db.refresh(row)
    return rows


def update_kind_params(db: Session, section_id: int, body: PlacementKindPatch) -> list[ThesisPlacement]:
    section = get_section(db, section_id)
    if body.kind == "device":
        if body.subtype not in {"1", "2a", "2b"}:
            raise SceneError("bad_subtype")
    elif body.subtype not in (None,):
        raise SceneError("subtype_not_used")
    matched = [
        row
        for row in section.placements
        if row.kind == body.kind and row.subtype == (body.subtype if body.kind == "device" else None)
    ]
    for row in matched:
        raw = dict(row.params_json)
        raw.update(body.params)
        row.params_json = _finalize_params(row.kind, row.subtype, raw)
        row.updated_at = utcnow()
    section.updated_at = utcnow()
    db.commit()
    for row in matched:
        db.refresh(row)
    return matched


def convert_placements(db: Session, section_id: int, body: PlacementConvertIn) -> list[ThesisPlacement]:
    section = get_section(db, section_id)
    wanted = set(body.ids)
    matched = [row for row in section.placements if row.id in wanted]
    if len(matched) != len(wanted):
        raise SceneError("not_found", 404)
    for row in matched:
        if row.kind == "device" or body.kind == "device":
            raise SceneError("device_kind_locked")
        if row.kind == body.kind:
            continue
        raw = dict(row.params_json)
        if body.kind == "radar":
            radar_defaults = spec_for("radar", None).defaults()
            raw.setdefault("radius_m", radar_defaults["radius_m"])
            raw.setdefault("show_range", False)
        row.kind = body.kind
        row.subtype = None
        row.params_json = _finalize_params(body.kind, None, raw)
        row.updated_at = utcnow()
    section.updated_at = utcnow()
    db.commit()
    for row in matched:
        db.refresh(row)
    return matched


def update_placement(db: Session, section_id: int, placement_id: int, body: PlacementPatch) -> ThesisPlacement:
    section = get_section(db, section_id)
    row = _find_placement(section, placement_id)
    new_kind = body.kind if body.kind is not None else row.kind
    if (row.kind == "device") != (new_kind == "device"):
        raise SceneError("device_kind_locked")
    if new_kind == "device":
        new_subtype = body.subtype if body.subtype is not None else row.subtype
        if new_subtype not in {"1", "2a", "2b"}:
            raise SceneError("bad_subtype")
    else:
        if body.subtype not in (None,):
            raise SceneError("subtype_not_used")
        new_subtype = None

    new_x = row.x_m if body.x_m is None else body.x_m
    new_y = row.y_m if body.y_m is None else body.y_m
    _ensure_inside(new_x, new_y, section.width_m, section.height_m)

    if new_kind == "device" and new_subtype != row.subtype:
        raw: dict[str, Any] = dict(body.params or {})
    else:
        raw = dict(row.params_json)
        if row.kind == "station" and new_kind == "radar":
            radar_defaults = spec_for("radar", None).defaults()
            raw.setdefault("radius_m", radar_defaults["radius_m"])
            raw.setdefault("show_range", radar_defaults["show_range"])
        if body.params:
            raw.update(body.params)

    row.kind = new_kind
    row.subtype = new_subtype
    row.x_m = float(new_x)
    row.y_m = float(new_y)
    row.params_json = _finalize_params(new_kind, new_subtype, raw)
    row.updated_at = utcnow()
    section.updated_at = utcnow()
    db.commit()
    db.refresh(row)
    return row


def delete_placement(db: Session, section_id: int, placement_id: int) -> None:
    delete_placements(db, section_id, PlacementDeleteIn(ids=[placement_id]), allow_initialized=True)


def delete_placements(
    db: Session,
    section_id: int,
    body: PlacementDeleteIn,
    *,
    allow_initialized: bool = False,
) -> None:
    section = get_section(db, section_id)
    if section.status == INITIALIZED and not allow_initialized:
        raise SceneError("bulk_locked")
    wanted = set(body.ids)
    matched = [row for row in section.placements if row.id in wanted]
    if len(matched) != len(wanted):
        raise SceneError("not_found", 404)
    for row in matched:
        db.delete(row)
    section.updated_at = utcnow()
    db.commit()


def delete_section(db: Session, section_id: int) -> None:
    section = get_section(db, section_id)
    db.delete(section)
    db.commit()


def _find_placement(section: ThesisSection, placement_id: int) -> ThesisPlacement:
    for item in section.placements:
        if item.id == placement_id:
            return item
    raise SceneError("not_found", 404)


def _new_placement(section: ThesisSection, body: PlacementIn) -> ThesisPlacement:
    kind, subtype = _normalize_identity(body.kind, body.subtype)
    _ensure_inside(body.x_m, body.y_m, section.width_m, section.height_m)
    return ThesisPlacement(
        section_id=section.id,
        kind=kind,
        subtype=subtype,
        x_m=float(body.x_m),
        y_m=float(body.y_m),
        params_json=_finalize_params(kind, subtype, dict(body.params)),
    )


def _normalize_identity(kind: str, subtype: str | None) -> tuple[str, str | None]:
    if kind == "device":
        if subtype not in {"1", "2a", "2b"}:
            raise SceneError("bad_subtype")
        return kind, subtype
    if kind in {"station", "radar"}:
        if subtype not in (None,):
            raise SceneError("subtype_not_used")
        return kind, None
    raise SceneError("bad_subtype")


def _clean_name(name: str) -> str:
    cleaned = name.strip()
    if not cleaned:
        raise SceneError("empty_name")
    return cleaned


def _ensure_inside(x: float, y: float, width: float, height: float) -> None:
    values = (x, y, width, height)
    if not all(isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(float(value)) for value in values):
        raise SceneError("outside_bounds")
    if x < -_EDGE or y < -_EDGE or x > width + _EDGE or y > height + _EDGE:
        raise SceneError("outside_bounds")


def _finalize_params(kind: str, subtype: str | None, raw: dict[str, Any]) -> dict[str, Any]:
    try:
        defaults = spec_for(kind, subtype).defaults()
    except KeyError as exc:
        raise SceneError("bad_subtype") from exc
    cleaned: dict[str, Any] = {}
    for key, value in raw.items():
        if not isinstance(key, str) or not key:
            raise SceneError("bad_param")
        if key in defaults:
            cleaned[key] = _coerce_like(defaults[key], value, key)
        else:
            cleaned[key] = _json_value(value, key)
    for key, value in defaults.items():
        cleaned.setdefault(key, value)
    if "radius_m" in cleaned:
        radius = cleaned["radius_m"]
        if isinstance(radius, bool) or not isinstance(radius, (int, float)):
            raise SceneError("bad_radius")
        if not math.isfinite(float(radius)) or float(radius) <= 0 or float(radius) > 10_000:
            raise SceneError("bad_radius")
        cleaned["radius_m"] = float(radius)
    encoded = json.dumps(cleaned, allow_nan=False)
    if len(encoded) > _MAX_PARAMS_CHARS:
        raise SceneError("bad_param")
    return cleaned


def _coerce_like(sample: Any, value: Any, key: str) -> Any:
    if isinstance(sample, bool):
        if not isinstance(value, bool):
            raise SceneError("bad_param")
        return value
    if isinstance(sample, (int, float)):
        return _finite_number(value, key)
    if isinstance(sample, str):
        if not isinstance(value, str):
            raise SceneError("bad_param")
        return value
    if sample is None:
        if value is None:
            return None
        return _finite_number(value, key)
    raise SceneError("bad_param")


def _finite_number(value: Any, key: str) -> float:
    del key
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise SceneError("bad_param")
    number = float(value)
    if not math.isfinite(number):
        raise SceneError("bad_param")
    return number


def _json_value(value: Any, key: str) -> Any:
    if value is None or isinstance(value, (str, bool)):
        return value
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return _finite_number(value, key)
    if isinstance(value, dict):
        return {str(item_key): _json_value(item_value, key) for item_key, item_value in value.items()}
    if isinstance(value, list):
        return [_json_value(item, key) for item in value]
    raise SceneError("bad_param")
