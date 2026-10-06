from __future__ import annotations

import os
from pathlib import Path

# IMPORTANT: this must run before ANY `data.database.connection` import,
# including the ones a few lines below in this very file, because
# DEFAULT_DB_PATH is computed once, at import time, from this environment
# variable. The servers/*.py modules each build exactly one
# domain-restricted Session at THEIR import time, bound to whatever
# DEFAULT_DB_PATH resolves to -- so every test in this suite, including
# ones that import a server module, must see the same resolved path.
# Per-test fixtures below (db_path/seeded_schema/...) remain fully
# isolated regardless, since they always pass an explicit db_path that
# overrides this default.
_SHARED_TEST_DB_PATH = str(Path(__file__).resolve().parent / "_shared_test_meridian.db")
os.environ.setdefault("MERIDIAN_DB_PATH", _SHARED_TEST_DB_PATH)

import pytest  # noqa: E402

from data.database.connection import init_schema  # noqa: E402
from data.database.session import create_domain_database_access, get_unrestricted_session  # noqa: E402
from data.seed.seed import run_seed  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def _prepare_shared_test_database():
    """
    Creates and deterministically seeds the ONE shared database that
    every server module (servers/banking_server.py, etc.) binds to at
    import time. Runs once per test session, before any test body
    executes -- module-level `create_domain_database_access(...)` calls
    in the server modules are lazy about actually touching the DB file,
    so it is fine for this to run after those modules are imported during
    collection, as long as it runs before any test calls into a tool.
    """
    init_schema(db_path=_SHARED_TEST_DB_PATH, drop_first=True)
    run_seed(db_path=_SHARED_TEST_DB_PATH)
    yield


@pytest.fixture()
def db_path(tmp_path) -> str:
    """A brand-new, empty SQLite file path per test -- fully isolated."""
    return str(tmp_path / "meridian_test.db")


@pytest.fixture()
def seeded_schema(db_path) -> str:
    """Initializes (empty) schema at db_path and returns the path."""
    init_schema(db_path=db_path)
    return db_path


@pytest.fixture()
def unrestricted_session(seeded_schema):
    session = get_unrestricted_session(db_path=seeded_schema)
    yield session
    session.close()


@pytest.fixture()
def domain_session_factory(seeded_schema):
    """Returns a callable: domain_session_factory("banking_server") -> Session."""
    created = []

    def _factory(server: str):
        session = create_domain_database_access(server=server, db_path=seeded_schema)
        created.append(session)
        return session

    yield _factory

    for session in created:
        session.close()
