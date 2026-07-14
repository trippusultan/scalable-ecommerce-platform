"""Database helpers — one engine/session per service, SQLAlchemy 2.0."""
from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from .config import Settings


class Base(DeclarativeBase):
    pass


_engines: dict[str, "Engine"] = {}


def get_engine(settings: Settings):
    if settings.service_name not in _engines:
        url = settings.resolve_db_url()
        connect_args = {}
        if url.startswith("sqlite"):
            connect_args = {"check_same_thread": False}
        _engines[settings.service_name] = create_engine(
            url, future=True, connect_args=connect_args, pool_pre_ping=True
        )
    return _engines[settings.service_name]


def init_db(settings: Settings) -> None:
    """Create tables for this service. Import your models first!

    Also tolerates schema drift on SQLite: if a model gained a column since the
    DB was first created, we ALTER TABLE ADD COLUMN so an existing dev DB keeps
    working (e.g. adding `status` to the discovery registry) without a manual
    wipe.
    """
    engine = get_engine(settings)
    Base.metadata.create_all(engine)
    # SQLite has no robust ALTER for arbitrary changes, but ADD COLUMN (single
    # new nullable column) is safe and covers our dev schema evolution.
    if engine.dialect.name == "sqlite":
        from sqlalchemy import inspect, text
        inspector = inspect(engine)
        for table in Base.metadata.tables.values():
            if not inspector.has_table(table.name):
                continue
            existing = {c["name"] for c in inspector.get_columns(table.name)}
            for col in table.columns:
                if col.name not in existing:
                    # only support adding simple nullable columns
                    ddl = text(
                        f'ALTER TABLE {table.name} ADD COLUMN {col.name} '
                        f'{col.type.compile(engine.dialect)}'
                    )
                    with engine.begin() as conn:
                        conn.execute(ddl)


def reset_engines() -> None:
    """Test helper: drop cached engines (after disposing test DBs)."""
    for e in _engines.values():
        e.dispose()
    _engines.clear()


@contextmanager
def session_scope(settings: Settings) -> Iterator[Session]:
    session = Session(get_engine(settings), future=True)
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
