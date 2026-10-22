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
    global _engine, _session_factory, _db_ready_url
    _db_ready_url = None
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


# Columns added after the tables first shipped (create_all never ALTERs).
_ADDED_COLUMNS: tuple[tuple[str, str, str], ...] = (
    ("thesis_run_rounds", "frame_seq", "INTEGER"),
    ("thesis_run_rounds", "candidates", "INTEGER"),
    ("thesis_run_rounds", "joiners", "INTEGER"),
    ("thesis_run_rounds", "on_at_page", "INTEGER"),
    ("thesis_run_rounds", "backlog_true", "INTEGER"),
    ("thesis_run_rounds", "served", "INTEGER"),
    ("thesis_run_rounds", "s_budget", "INTEGER"),
    ("thesis_run_rounds", "budget_dropped", "INTEGER"),
    ("thesis_run_rounds", "n_hat", "DOUBLE PRECISION"),
    ("thesis_run_rounds", "mnot_prev", "INTEGER"),
    ("thesis_run_rounds", "mnot_next", "INTEGER"),
    ("thesis_run_rounds", "n_done_total", "INTEGER"),
    ("thesis_run_rounds", "identified_json", "JSONB"),
    ("thesis_run_rounds", "timing_json", "JSONB"),
    ("thesis_run_rounds", "energy_json", "JSONB"),
    ("thesis_run_rounds", "deaths_json", "JSONB"),
    ("thesis_run_rounds", "slots_json", "JSONB"),
    ("thesis_device_events", "frame_seq", "INTEGER"),
    ("thesis_reader_events", "frame_seq", "INTEGER"),
)

_ADDED_INDEXES: tuple[str, ...] = (
    "CREATE INDEX IF NOT EXISTS thesis_run_rounds_run_seq_idx ON thesis_run_rounds (run_id, frame_seq)",
    "CREATE INDEX IF NOT EXISTS thesis_device_events_run_seq_idx ON thesis_device_events (run_id, frame_seq)",
    "CREATE INDEX IF NOT EXISTS thesis_reader_events_run_seq_idx ON thesis_reader_events (run_id, frame_seq)",
    "CREATE INDEX IF NOT EXISTS thesis_run_snapshots_run_t_idx ON thesis_run_snapshots (run_id, sim_time_s)",
)

# Event tables carry no foreign keys (COPY throughput); this trigger keeps the
# old ON DELETE CASCADE behaviour, including runs removed by a section cascade.
_EVENT_FK_DDL: tuple[str, ...] = (
    "ALTER TABLE thesis_device_events DROP CONSTRAINT IF EXISTS thesis_device_events_run_id_fkey",
    "ALTER TABLE thesis_device_events DROP CONSTRAINT IF EXISTS thesis_device_events_round_id_fkey",
    "ALTER TABLE thesis_reader_events DROP CONSTRAINT IF EXISTS thesis_reader_events_run_id_fkey",
    "ALTER TABLE thesis_reader_events DROP CONSTRAINT IF EXISTS thesis_reader_events_round_id_fkey",
    """
    CREATE OR REPLACE FUNCTION thesis_runs_delete_events() RETURNS trigger AS $$
    BEGIN
      DELETE FROM thesis_device_events WHERE run_id = OLD.id;
      DELETE FROM thesis_reader_events WHERE run_id = OLD.id;
      RETURN OLD;
    END $$ LANGUAGE plpgsql
    """,
    "DROP TRIGGER IF EXISTS thesis_runs_delete_events ON thesis_inventory_runs",
    """
    CREATE TRIGGER thesis_runs_delete_events AFTER DELETE ON thesis_inventory_runs
    FOR EACH ROW EXECUTE FUNCTION thesis_runs_delete_events()
    """,
)

_db_ready_url: str | None = None


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
        for table, column, ddl in _ADDED_COLUMNS:
            conn.execute(text(f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS {column} {ddl}"))
        for stmt in _ADDED_INDEXES:
            conn.execute(text(stmt))
        for stmt in _EVENT_FK_DDL:
            conn.execute(text(stmt))
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


def ensure_db() -> None:
    """Run :func:`init_db` once per database URL."""
    global _db_ready_url
    url = database_url()
    if _db_ready_url != url:
        init_db()
        _db_ready_url = url


def get_db():
    ensure_db()
    db = session_factory()()
    try:
        yield db
    finally:
        db.close()
