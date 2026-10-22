from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import BigInteger, DateTime, Float, ForeignKey, Integer, LargeBinary, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.thesis_simulator.db import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class ThesisSection(Base):
    __tablename__ = "thesis_sections"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    width_m: Mapped[float] = mapped_column(Float, nullable=False)
    height_m: Mapped[float] = mapped_column(Float, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="initializing", server_default="initializing")
    marker_scale: Mapped[float] = mapped_column(Float, nullable=False, default=0.7, server_default="0.7")
    device_marker_scale: Mapped[float] = mapped_column(Float, nullable=False, default=0.3, server_default="0.3")
    locked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

    placements: Mapped[list[ThesisPlacement]] = relationship(
        back_populates="section",
        cascade="all, delete-orphan",
        order_by="ThesisPlacement.id",
        lazy="selectin",
    )
    runs: Mapped[list[ThesisInventoryRun]] = relationship(
        back_populates="section",
        cascade="all, delete-orphan",
        order_by="ThesisInventoryRun.created_at.desc()",
    )


class ThesisPlacement(Base):
    __tablename__ = "thesis_placements"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    section_id: Mapped[int] = mapped_column(
        ForeignKey("thesis_sections.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    kind: Mapped[str] = mapped_column(String(16), nullable=False)
    subtype: Mapped[str | None] = mapped_column(String(8), nullable=True)
    x_m: Mapped[float] = mapped_column(Float, nullable=False)
    y_m: Mapped[float] = mapped_column(Float, nullable=False)
    params_json: Mapped[dict] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

    section: Mapped[ThesisSection] = relationship(back_populates="placements")


class ThesisInventoryRun(Base):
    __tablename__ = "thesis_inventory_runs"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    section_id: Mapped[int] = mapped_column(
        ForeignKey("thesis_sections.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    scheme: Mapped[str] = mapped_column(String(16), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="pending", server_default="pending")
    config_json: Mapped[dict] = mapped_column(JSONB, nullable=False)
    scene_snapshot_json: Mapped[dict] = mapped_column(JSONB, nullable=False)
    requested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    duration_s: Mapped[float | None] = mapped_column(Float, nullable=True)
    error_detail: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

    section: Mapped[ThesisSection] = relationship(back_populates="runs")
    summary: Mapped[ThesisRunSummary | None] = relationship(
        back_populates="run", cascade="all, delete-orphan", uselist=False
    )


class ThesisRunRound(Base):
    __tablename__ = "thesis_run_rounds"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    run_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("thesis_inventory_runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    reader_id: Mapped[int] = mapped_column(Integer, nullable=False)
    round_index: Mapped[int] = mapped_column(Integer, nullable=False)
    t_start_s: Mapped[float] = mapped_column(Float, nullable=False)
    t_end_s: Mapped[float] = mapped_column(Float, nullable=False)
    k_estimate: Mapped[float | None] = mapped_column(Float, nullable=True)
    g: Mapped[float | None] = mapped_column(Float, nullable=True)
    pstar: Mapped[float | None] = mapped_column(Float, nullable=True)
    slot_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    success_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    collision_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    empty_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    metadata_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    # Live-run bookkeeping + per-round analytics (see inventory/frame.py).
    frame_seq: Mapped[int | None] = mapped_column(Integer, nullable=True)
    candidates: Mapped[int | None] = mapped_column(Integer, nullable=True)
    joiners: Mapped[int | None] = mapped_column(Integer, nullable=True)
    on_at_page: Mapped[int | None] = mapped_column(Integer, nullable=True)
    backlog_true: Mapped[int | None] = mapped_column(Integer, nullable=True)
    served: Mapped[int | None] = mapped_column(Integer, nullable=True)
    s_budget: Mapped[int | None] = mapped_column(Integer, nullable=True)
    budget_dropped: Mapped[int | None] = mapped_column(Integer, nullable=True)
    n_hat: Mapped[float | None] = mapped_column(Float, nullable=True)
    mnot_prev: Mapped[int | None] = mapped_column(Integer, nullable=True)
    mnot_next: Mapped[int | None] = mapped_column(Integer, nullable=True)
    n_done_total: Mapped[int | None] = mapped_column(Integer, nullable=True)
    identified_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    timing_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    energy_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    deaths_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    slots_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)


class ThesisDeviceEvent(Base):
    __tablename__ = "thesis_device_events"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    # No foreign keys on the event tables: per-row FK checks halved COPY
    # throughput. Deleting a run removes its events through the
    # thesis_runs_delete_events trigger (see db.init_db).
    run_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    device_id: Mapped[int] = mapped_column(Integer, nullable=False)
    reader_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    round_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    t_s: Mapped[float] = mapped_column(Float, nullable=False)
    event_type: Mapped[str] = mapped_column(String(32), nullable=False)
    cause: Mapped[str | None] = mapped_column(String(32), nullable=True)
    energy_j: Mapped[float | None] = mapped_column(Float, nullable=True)
    payload_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    frame_seq: Mapped[int | None] = mapped_column(Integer, nullable=True)


class ThesisReaderEvent(Base):
    __tablename__ = "thesis_reader_events"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    # No foreign keys on the event tables: per-row FK checks halved COPY
    # throughput. Deleting a run removes its events through the
    # thesis_runs_delete_events trigger (see db.init_db).
    run_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    reader_id: Mapped[int] = mapped_column(Integer, nullable=False)
    round_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    t_s: Mapped[float] = mapped_column(Float, nullable=False)
    event_type: Mapped[str] = mapped_column(String(32), nullable=False)
    slot_index: Mapped[int | None] = mapped_column(Integer, nullable=True)
    payload_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    frame_seq: Mapped[int | None] = mapped_column(Integer, nullable=True)


class ThesisRunSummary(Base):
    __tablename__ = "thesis_run_summary"

    run_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("thesis_inventory_runs.id", ondelete="CASCADE"),
        primary_key=True,
    )
    total_devices: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    identified_total: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    identified_by_subtype_json: Mapped[dict] = mapped_column(JSONB, nullable=False)
    died_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    dropped_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    rounds_total: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    wall_duration_s: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    metrics_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    run: Mapped[ThesisInventoryRun] = relationship(back_populates="summary")


class ThesisRunSnapshot(Base):
    """Every-device state at one simulated instant (for scrubbing / energy charts).

    ``state_codes`` is one uint8 per device (inventory.state.STATE_*),
    ``energy_j`` one float32 per device, both in scene-snapshot device order.
    """

    __tablename__ = "thesis_run_snapshots"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    run_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("thesis_inventory_runs.id", ondelete="CASCADE"),
        nullable=False,
    )
    frame_seq: Mapped[int] = mapped_column(Integer, nullable=False)
    sim_time_s: Mapped[float] = mapped_column(Float, nullable=False)
    state_codes: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    energy_j: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)


class ThesisRunCheckpoint(Base):
    """Latest resumable engine state of a run (one row per run)."""

    __tablename__ = "thesis_run_checkpoints"

    run_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("thesis_inventory_runs.id", ondelete="CASCADE"),
        primary_key=True,
    )
    frame_seq: Mapped[int] = mapped_column(Integer, nullable=False)
    sim_time_s: Mapped[float] = mapped_column(Float, nullable=False)
    state_blob: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
