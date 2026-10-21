"""PostgreSQL engine for the thesis scene.

Local development uses the Compose service in
``Implements/infrastructure/docker-compose.postgresql.yml``. Override the URL with
``THESIS_DATABASE_URL``. Tests point that variable at the ``thesis_test``
database and call ``reset_engine`` so they never write the dev database.
"""

from __future__ import annotations

import os

from sqlalchemy import create_engine, text

from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

DEFAULT_DATABASE_URL = "postgresql+psycopg://thesis:thesis@127.0.0.1:5432/thesis"

_engine: Engine | None = None
_session_factory: sessionmaker[Session] | None = None


class Base(DeclarativeBase):
    pass


def database_url() -> str:
    return os.environ.get("THESIS_DATABASE_URL", DEFAULT_DATABASE_URL)


def reset_engine() -> None:
    global _engine, _session_factory
    if _engine is not None:
        _engine.dispose()
    _engine = None
    _session_factory = None


def get_engine() -> Engine:
    global _engine
    if _engine is None:
        _engine = create_engine(database_url(), pool_pre_ping=True)
    return _engine


def session_factory() -> sessionmaker[Session]:
    global _session_factory
    if _session_factory is None:
        _session_factory = sessionmaker(bind=get_engine(), expire_on_commit=False)
    return _session_factory


def init_db() -> None:
    from app.thesis_simulator import models  # noqa: F401

    Base.metadata.create_all(get_engine())
    with get_engine().begin() as conn:
        conn.execute(
            text(
                "ALTER TABLE thesis_sections "
                "ADD COLUMN IF NOT EXISTS status VARCHAR(32) NOT NULL DEFAULT 'initializing'"
            )
        )
        conn.execute(
            text(
                "ALTER TABLE thesis_sections "
                "ADD COLUMN IF NOT EXISTS marker_scale DOUBLE PRECISION NOT NULL DEFAULT 0.7"
            )
        )
        conn.execute(
            text(
                "ALTER TABLE thesis_sections "
                "ADD COLUMN IF NOT EXISTS device_marker_scale DOUBLE PRECISION NOT NULL DEFAULT 0.3"
            )
        )
        conn.execute(
            text(
                "ALTER TABLE thesis_sections "
                "ADD COLUMN IF NOT EXISTS locked_at TIMESTAMP WITH TIME ZONE"
            )
        )
        conn.execute(
            text(
                "CREATE UNIQUE INDEX IF NOT EXISTS thesis_run_rounds_run_reader_idx "
                "ON thesis_run_rounds (run_id, reader_id, round_index)"
            )
        )
        conn.execute(
            text(
                "CREATE INDEX IF NOT EXISTS thesis_run_rounds_run_t_idx "
                "ON thesis_run_rounds (run_id, t_start_s)"
            )
        )
        conn.execute(
            text(
                "CREATE INDEX IF NOT EXISTS thesis_device_events_run_device_t_idx "
                "ON thesis_device_events (run_id, device_id, t_s)"
            )
        )
        conn.execute(
            text(
                "CREATE INDEX IF NOT EXISTS thesis_device_events_run_type_t_idx "
                "ON thesis_device_events (run_id, event_type, t_s)"
            )
        )
        conn.execute(
            text(
                "CREATE INDEX IF NOT EXISTS thesis_device_events_run_reader_t_idx "
                "ON thesis_device_events (run_id, reader_id, t_s)"
            )
        )
        conn.execute(
            text(
                "CREATE INDEX IF NOT EXISTS thesis_reader_events_run_reader_t_idx "
                "ON thesis_reader_events (run_id, reader_id, t_s)"
            )
        )
        conn.execute(
            text(
                "ALTER TABLE thesis_inventory_runs "
                "ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMP WITH TIME ZONE"
            )
        )
        conn.execute(
            text(
                "CREATE INDEX IF NOT EXISTS thesis_inventory_runs_section_alive_idx "
                "ON thesis_inventory_runs (section_id, created_at DESC) WHERE deleted_at IS NULL"
            )
        )
        conn.execute(
            text(
                """
                DO $$
                BEGIN
                  IF EXISTS (
                    SELECT 1 FROM information_schema.columns
                    WHERE table_name = 'thesis_sections'
                      AND column_name = 'marker_scale'
                      AND data_type = 'integer'
                  ) THEN
                    ALTER TABLE thesis_sections
                      ALTER COLUMN marker_scale TYPE DOUBLE PRECISION
                      USING marker_scale::double precision;
                  END IF;
                END $$;
                """
            )
        )


def get_db():
    init_db()
    db = session_factory()()
    try:
        yield db
    finally:
        db.close()
