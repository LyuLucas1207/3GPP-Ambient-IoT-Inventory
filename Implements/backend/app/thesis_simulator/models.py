from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import BigInteger, DateTime, Float, ForeignKey, Integer, String
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


class ThesisDeviceEvent(Base):
    __tablename__ = "thesis_device_events"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    run_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("thesis_inventory_runs.id", ondelete="CASCADE"),
        nullable=False,
    )
    device_id: Mapped[int] = mapped_column(Integer, nullable=False)
    reader_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    round_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("thesis_run_rounds.id", ondelete="SET NULL"),
        nullable=True,
    )
    t_s: Mapped[float] = mapped_column(Float, nullable=False)
    event_type: Mapped[str] = mapped_column(String(32), nullable=False)
    cause: Mapped[str | None] = mapped_column(String(32), nullable=True)
    energy_j: Mapped[float | None] = mapped_column(Float, nullable=True)
    payload_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)


class ThesisReaderEvent(Base):
    __tablename__ = "thesis_reader_events"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    run_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("thesis_inventory_runs.id", ondelete="CASCADE"),
        nullable=False,
    )
    reader_id: Mapped[int] = mapped_column(Integer, nullable=False)
    round_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("thesis_run_rounds.id", ondelete="SET NULL"),
        nullable=True,
    )
    t_s: Mapped[float] = mapped_column(Float, nullable=False)
    event_type: Mapped[str] = mapped_column(String(32), nullable=False)
    slot_index: Mapped[int | None] = mapped_column(Integer, nullable=True)
    payload_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)


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
