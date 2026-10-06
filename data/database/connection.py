"""
Engine creation and schema initialization for the shared meridian.db SQLite
database.

All four domains (banking, insurance, wealth, concierge) live inside this
one physical SQLite file. Logical isolation between servers is NOT enforced
here -- it is enforced in `session.py` / `access_control.py`. This module
only owns: where the file lives, how the engine is configured, and how the
schema gets created.
"""
from __future__ import annotations

import os
from pathlib import Path

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine

DEFAULT_DB_PATH = os.environ.get(
    "MERIDIAN_DB_PATH",
    str(Path(__file__).resolve().parents[2] / "meridian.db"),
)

_engine_cache: dict[str, Engine] = {}


def _enable_sqlite_pragmas(dbapi_connection, _connection_record) -> None:
    """Enable WAL mode and foreign-key enforcement on every new connection."""
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


def get_engine(db_path: str | None = None) -> Engine:
    """
    Return a (process-wide cached) SQLAlchemy Engine for the given SQLite
    file path. Reusing the same Engine object per path is required for the
    WAL pragma and connection pooling to behave sensibly, and for the
    `do_orm_execute` / `before_flush` listeners registered in session.py to
    apply consistently.
    """
    path = db_path or DEFAULT_DB_PATH
    if path not in _engine_cache:
        engine = create_engine(f"sqlite:///{path}", future=True)
        event.listen(engine, "connect", _enable_sqlite_pragmas)
        _engine_cache[path] = engine
    return _engine_cache[path]


def init_schema(db_path: str | None = None, drop_first: bool = False) -> Engine:
    """
    Create (or, if drop_first=True, recreate) every table declared on the
    shared declarative Base. Safe to call repeatedly: SQLAlchemy's
    create_all() only creates tables that do not already exist.
    """
    # Imported lazily to avoid a circular import: models import Base from
    # here-adjacent module, and model modules must all be imported at least
    # once so their tables register on Base.metadata before create_all().
    from data.models.base import Base
    import data.models.banking.account  # noqa: F401
    import data.models.banking.transaction  # noqa: F401
    import data.models.insurance.policy  # noqa: F401
    import data.models.insurance.claim  # noqa: F401
    import data.models.wealth.portfolio  # noqa: F401
    import data.models.wealth.investment_product  # noqa: F401
    import data.models.concierge.customer  # noqa: F401
    import data.models.concierge.interaction_log  # noqa: F401
    import data.models.concierge.escalation_flag  # noqa: F401
    import data.models.concierge.audit_log  # noqa: F401

    engine = get_engine(db_path)
    if drop_first:
        Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    return engine
