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
                "ADD COLUMN IF NOT EXISTS marker_scale DOUBLE PRECISION NOT NULL DEFAULT 1"
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
