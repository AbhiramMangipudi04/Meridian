"""
Domain-restricted database sessions.

This is the actual enforcement mechanism for server/table isolation,
required by the project brief to be real rather than documentation-only.

Two SQLAlchemy event hooks are registered once, globally, on the Session
class:

  * `do_orm_execute`  -- fires for every session.execute(select/update/
    delete/insert(...)) call AND for every legacy `session.query(...)`
    call (Query compiles to the same unified execution path in SQLAlchemy
    1.4/2.0). This covers reads and bulk writes issued explicitly.

  * `before_flush`    -- fires when the unit-of-work is about to flush
    session.add()/session.delete() changes to the database. This is
    necessary because ORM object persistence via commit() does NOT route
    through `do_orm_execute`; without this hook a restricted session could
    bypass the allowlist simply by using `session.add(SomeOtherDomainRow())`.

Both hooks look at a plain attribute (`_nexus_domain_server`) set on the
Session instance by `create_domain_database_access()`. Sessions without
that attribute (e.g. the unrestricted session used by schema creation and
the seed orchestrator) are left alone.
"""
from __future__ import annotations

from sqlalchemy import event
from sqlalchemy.orm import Session, sessionmaker

from .access_control import ALL_KNOWN_SERVERS, SERVER_TABLE_ACCESS, UnauthorizedTableAccessError
from .connection import get_engine

_DOMAIN_ATTR = "_nexus_domain_server"


def _tables_touched_by_statement(stmt) -> set[str]:
    """Best-effort extraction of every table name a compiled ORM statement touches."""
    tables: set[str] = set()

    get_final_froms = getattr(stmt, "get_final_froms", None)
    if callable(get_final_froms):
        try:
            froms = get_final_froms()
        except Exception:
            froms = []
        for f in froms:
            name = getattr(f, "name", None)
            if name:
                tables.add(name)

    # Insert/Update/Delete core constructs expose `.table` directly.
    table = getattr(stmt, "table", None)
    if table is not None:
        name = getattr(table, "name", None)
        if name:
            tables.add(name)

    return tables


@event.listens_for(Session, "do_orm_execute")
def _enforce_table_access_on_execute(orm_execute_state) -> None:
    session = orm_execute_state.session
    server = getattr(session, _DOMAIN_ATTR, None)
    if server is None:
        return  # unrestricted session (schema creation / seed orchestrator)

    allowed = SERVER_TABLE_ACCESS[server]
    touched = _tables_touched_by_statement(orm_execute_state.statement)
    unauthorized = touched - allowed
    if unauthorized:
        raise UnauthorizedTableAccessError(server, sorted(unauthorized)[0])


@event.listens_for(Session, "before_flush")
def _enforce_table_access_on_flush(session, flush_context, instances) -> None:
    server = getattr(session, _DOMAIN_ATTR, None)
    if server is None:
        return  # unrestricted session

    allowed = SERVER_TABLE_ACCESS[server]
    for obj in list(session.new) + list(session.dirty) + list(session.deleted):
        table_name = obj.__table__.name
        if table_name not in allowed:
            raise UnauthorizedTableAccessError(server, table_name)


def create_domain_database_access(server: str, db_path: str | None = None) -> Session:
    """
    Return a brand-new SQLAlchemy Session that is structurally restricted
    to the tables `server` is allowed to touch, per SERVER_TABLE_ACCESS.

    Example:
        banking_db = create_domain_database_access(server="banking_server")
        insurance_db = create_domain_database_access(server="insurance_server")

    Any attempt by `insurance_db` to query, insert, update, or delete rows
    in `accounts`, `customers`, `portfolios`, etc. raises
    UnauthorizedTableAccessError -- even though all of these tables live
    in the same physical meridian.db SQLite file.
    """
    if server not in SERVER_TABLE_ACCESS:
        raise ValueError(f"Unknown server '{server}'. Known servers: {ALL_KNOWN_SERVERS}")

    engine = get_engine(db_path)
    factory = sessionmaker(bind=engine, future=True, expire_on_commit=False)
    session = factory()
    setattr(session, _DOMAIN_ATTR, server)
    return session


def get_unrestricted_session(db_path: str | None = None) -> Session:
    """
    Return a Session with NO table restriction.

    This exists only for internal infrastructure that is not server
    traffic: schema creation (`database.py`) and the deterministic seed
    orchestrator (`data/seed/seed.py`), which must write across all four
    domains in a controlled order. No server-facing or repository code
    should ever call this directly -- repositories are always constructed
    with a domain-restricted session.
    """
    engine = get_engine(db_path)
    factory = sessionmaker(bind=engine, future=True, expire_on_commit=False)
    return factory()
