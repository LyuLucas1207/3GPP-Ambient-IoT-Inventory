from typing import Any, Literal

from pydantic import BaseModel, Field

SectionStatus = Literal["initializing", "initialized"]
Kind = Literal["device", "station", "radar"]
Shape = Literal["circle", "square", "triangle", "diamond", "hexagon"]


class PlacementIn(BaseModel):
    kind: Kind
    subtype: str | None = None
    x_m: float
    y_m: float
    params: dict[str, Any] = Field(default_factory=dict)


class PlacementBatchIn(BaseModel):
    placements: list[PlacementIn] = Field(min_length=1, max_length=5_000)


class PlacementDeleteIn(BaseModel):
    ids: list[int] = Field(min_length=1, max_length=20_000)


class PlacementConvertIn(BaseModel):
    ids: list[int] = Field(min_length=1, max_length=5_000)
    kind: Literal["station", "radar"]


class PlacementKindPatch(BaseModel):
    kind: Kind
    subtype: str | None = None
    params: dict[str, Any] = Field(default_factory=dict)


class PlacementPatch(BaseModel):
    kind: Kind | None = None
    subtype: str | None = None
    x_m: float | None = None
    y_m: float | None = None
    params: dict[str, Any] | None = None


class SectionCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    width_m: float = Field(gt=0, le=10_000)
    height_m: float = Field(gt=0, le=10_000)
    placements: list[PlacementIn] = Field(default_factory=list, max_length=20_000)


class SectionPatch(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    width_m: float | None = Field(default=None, gt=0, le=10_000)
    height_m: float | None = Field(default=None, gt=0, le=10_000)
    status: Literal["initialized"] | None = None
    marker_scale: float | None = Field(default=None, ge=0, le=5)
    device_marker_scale: float | None = Field(default=None, ge=0, le=5)


class PlacementOut(BaseModel):
    id: int
    kind: Kind
    subtype: str | None
    x_m: float
    y_m: float
    params: dict[str, Any]
    derived: dict[str, Any] | None = None


class SectionOut(BaseModel):
    id: int
    name: str
    width_m: float
    height_m: float
    status: SectionStatus
    marker_scale: float
    device_marker_scale: float
    created_at: str
    updated_at: str
    placements: list[PlacementOut]


class SectionSummary(BaseModel):
    id: int
    name: str
    width_m: float
    height_m: float
    status: SectionStatus
    placement_count: int
    updated_at: str


class CatalogEntryOut(BaseModel):
    kind: Kind
    subtype: str | None
    shape: Shape
    defaults: dict[str, Any]
    derived_ranges: dict[str, float] | None = None


class ScenarioDefaultsOut(BaseModel):
    width_m: float
    height_m: float
    bs_lattice_spacing_m: float
    bs_positions: list[list[float]]
    active_bs_xy: list[float]
    default_n_devices: int
    max_placements: int


class DerivedRangesIn(BaseModel):
    tx_power_dbm: float = 33.0
    antenna_gain_dbi: float = 6.0
    extra_attenuation_db: float = 0.0
    carrier_ghz: float = 0.9
    device_sensitivities: dict[str, float] | None = None


class DerivedRangesOut(BaseModel):
    effective_range_m: dict[str, float]
