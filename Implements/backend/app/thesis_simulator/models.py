from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String
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
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

    placements: Mapped[list[ThesisPlacement]] = relationship(
        back_populates="section",
        cascade="all, delete-orphan",
        order_by="ThesisPlacement.id",
        lazy="selectin",
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
