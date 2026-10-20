from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session

from app.schemas.thesis_simulator import (
    CatalogEntryOut,
    DerivedRangesIn,
    DerivedRangesOut,
    PlacementBatchIn,
    PlacementConvertIn,
    PlacementDeleteIn,
    PlacementIn,
    PlacementKindPatch,
    PlacementOut,
    PlacementPatch,
    ScenarioDefaultsOut,
    SectionCreate,
    SectionOut,
    SectionPatch,
    SectionSummary,
)
from app.thesis_simulator.catalog import catalog_payload, derive_reader_ranges
from app.thesis_simulator.db import get_db
from app.thesis_simulator.scenario import scenario_defaults_payload
from app.thesis_simulator.service import (
    SceneError,
    add_placement,
    add_placements,
    create_section,
    convert_placements,
    delete_placement,
    delete_placements,
    delete_section,
    get_section,
    list_sections,
    placement_out,
    section_out,
    update_placement,
    update_kind_params,
    update_section,
)

router = APIRouter(tags=["thesis-simulator"])


def _guard(exc: SceneError) -> HTTPException:
    return HTTPException(status_code=exc.status, detail=exc.code)


@router.get("/catalog", response_model=list[CatalogEntryOut])
def read_catalog() -> list[dict]:
    return catalog_payload()


@router.get("/scenario-defaults", response_model=ScenarioDefaultsOut)
def read_scenario_defaults() -> dict:
    return scenario_defaults_payload()


@router.post("/derived-ranges", response_model=DerivedRangesOut)
def compute_derived_ranges(body: DerivedRangesIn) -> dict:
    rf = {
        "tx_power_dbm": body.tx_power_dbm,
        "antenna_gain_dbi": body.antenna_gain_dbi,
        "extra_attenuation_db": body.extra_attenuation_db,
        "carrier_ghz": body.carrier_ghz,
        "include_d2r": body.include_d2r,
    }
    return {"effective_range_m": derive_reader_ranges(rf, body.device_sensitivities)}


@router.get("/sections", response_model=list[SectionSummary])
def read_sections(db: Session = Depends(get_db)) -> list[dict]:
    return list_sections(db)


@router.post("/sections", response_model=SectionOut)
def post_section(body: SectionCreate, db: Session = Depends(get_db)) -> dict:
    try:
        return section_out(create_section(db, body))
    except SceneError as exc:
        raise _guard(exc) from exc


@router.get("/sections/{section_id}", response_model=SectionOut)
def read_section(section_id: int, db: Session = Depends(get_db)) -> dict:
    try:
        return section_out(get_section(db, section_id))
    except SceneError as exc:
        raise _guard(exc) from exc


@router.patch("/sections/{section_id}", response_model=SectionOut)
def patch_section(section_id: int, body: SectionPatch, db: Session = Depends(get_db)) -> dict:
    try:
        return section_out(update_section(db, section_id, body))
    except SceneError as exc:
        raise _guard(exc) from exc


@router.delete("/sections/{section_id}", status_code=204)
def remove_section(section_id: int, db: Session = Depends(get_db)) -> Response:
    try:
        delete_section(db, section_id)
    except SceneError as exc:
        raise _guard(exc) from exc
    return Response(status_code=204)


@router.post("/sections/{section_id}/placements", response_model=PlacementOut)
def post_placement(section_id: int, body: PlacementIn, db: Session = Depends(get_db)) -> dict:
    try:
        return placement_out(add_placement(db, section_id, body))
    except SceneError as exc:
        raise _guard(exc) from exc


@router.post("/sections/{section_id}/placements/batch", response_model=list[PlacementOut])
def post_placement_batch(section_id: int, body: PlacementBatchIn, db: Session = Depends(get_db)) -> list[dict]:
    try:
        return [placement_out(row) for row in add_placements(db, section_id, body)]
    except SceneError as exc:
        raise _guard(exc) from exc


@router.patch("/sections/{section_id}/placements/batch", response_model=list[PlacementOut])
def patch_placement_batch(section_id: int, body: PlacementKindPatch, db: Session = Depends(get_db)) -> list[dict]:
    try:
        return [placement_out(row) for row in update_kind_params(db, section_id, body)]
    except SceneError as exc:
        raise _guard(exc) from exc


@router.post("/sections/{section_id}/placements/convert", response_model=list[PlacementOut])
def post_placement_convert(section_id: int, body: PlacementConvertIn, db: Session = Depends(get_db)) -> list[dict]:
    try:
        return [placement_out(row) for row in convert_placements(db, section_id, body)]
    except SceneError as exc:
        raise _guard(exc) from exc


@router.patch("/sections/{section_id}/placements/{placement_id}", response_model=PlacementOut)
def patch_placement(
    section_id: int,
    placement_id: int,
    body: PlacementPatch,
    db: Session = Depends(get_db),
) -> dict:
    try:
        return placement_out(update_placement(db, section_id, placement_id, body))
    except SceneError as exc:
        raise _guard(exc) from exc


@router.delete("/sections/{section_id}/placements/batch", status_code=204)
def remove_placement_batch(section_id: int, body: PlacementDeleteIn, db: Session = Depends(get_db)) -> Response:
    try:
        delete_placements(db, section_id, body)
    except SceneError as exc:
        raise _guard(exc) from exc
    return Response(status_code=204)


@router.delete("/sections/{section_id}/placements/{placement_id}", status_code=204)
def remove_placement(section_id: int, placement_id: int, db: Session = Depends(get_db)) -> Response:
    try:
        delete_placement(db, section_id, placement_id)
    except SceneError as exc:
        raise _guard(exc) from exc
    return Response(status_code=204)
