"""
These tests are the core proof required by the brief: table isolation
between servers must be ACTUALLY ENFORCED, not merely documented. Every
negative test below attempts a real read or write and asserts it is
rejected with UnauthorizedTableAccessError; every positive test proves
the matching legitimate access still works.
"""
from __future__ import annotations

import datetime as dt

import pytest
from sqlalchemy import select

from data.database.access_control import SERVER_TABLE_ACCESS, UnauthorizedTableAccessError
from data.models.banking.account import Account
from data.models.concierge.customer import Customer
from data.models.insurance.policy import Policy
from data.models.wealth.portfolio import Portfolio
from data.repositories.banking.account_repository import AccountRepository
from data.repositories.concierge.customer_repository import CustomerRepository
from data.repositories.insurance.policy_repository import PolicyRepository
from data.repositories.wealth.portfolio_repository import PortfolioRepository


# ---------------------------------------------------------------------------
# Positive access: each server CAN reach its own tables.
# ---------------------------------------------------------------------------
def test_banking_can_access_accounts(domain_session_factory):
    session = domain_session_factory("banking_server")
    repo = AccountRepository(session)
    repo.create(
        account_id="ACC-20077",
        customer_business_id="CUS-20077",
        account_type="SAVINGS",
        opened_at=dt.datetime(2024, 1, 1),
    )
    assert repo.read_by_id("ACC-20077").account_id == "ACC-20077"


def test_insurance_can_access_policies(domain_session_factory):
    session = domain_session_factory("insurance_server")
    repo = PolicyRepository(session)
    repo.create(
        policy_id="POL-IN-30091",
        customer_business_id="CUS-20077",
        policy_type="GENERAL",
        premium_amount=100,
        start_date=dt.date(2024, 1, 1),
    )
    assert repo.read_by_id("POL-IN-30091").policy_id == "POL-IN-30091"


def test_wealth_can_access_portfolios(domain_session_factory):
    session = domain_session_factory("wealth_server")
    repo = PortfolioRepository(session)
    repo.create(portfolio_id="PORT-10001", customer_business_id="CUS-20077")
    assert repo.read_by_id("PORT-10001").portfolio_id == "PORT-10001"


def test_concierge_can_access_customers(domain_session_factory):
    session = domain_session_factory("concierge_ops_server")
    repo = CustomerRepository(session)
    repo.create(
        customer_business_id="CUS-20077", full_name="Arjun Mehta", email="a@x.com", phone="1"
    )
    assert repo.read_by_id("CUS-20077").full_name == "Arjun Mehta"


# ---------------------------------------------------------------------------
# Negative access: each server CANNOT reach other domains' tables, via
# BOTH the repository layer (read_all / read_by_id) AND a direct raw ORM
# query against a wrong-domain session, AND the flush path (session.add).
# ---------------------------------------------------------------------------
def test_insurance_cannot_access_accounts(domain_session_factory):
    session = domain_session_factory("insurance_server")
    with pytest.raises(UnauthorizedTableAccessError):
        session.execute(select(Account))


def test_insurance_cannot_access_customers(domain_session_factory):
    session = domain_session_factory("insurance_server")
    with pytest.raises(UnauthorizedTableAccessError):
        session.execute(select(Customer))


def test_insurance_cannot_access_portfolios(domain_session_factory):
    session = domain_session_factory("insurance_server")
    with pytest.raises(UnauthorizedTableAccessError):
        session.execute(select(Portfolio))


def test_banking_cannot_access_customers(domain_session_factory):
    session = domain_session_factory("banking_server")
    with pytest.raises(UnauthorizedTableAccessError):
        session.execute(select(Customer))


def test_banking_cannot_access_policies(domain_session_factory):
    session = domain_session_factory("banking_server")
    with pytest.raises(UnauthorizedTableAccessError):
        session.execute(select(Policy))


def test_wealth_cannot_access_policies(domain_session_factory):
    session = domain_session_factory("wealth_server")
    with pytest.raises(UnauthorizedTableAccessError):
        session.execute(select(Policy))


def test_wealth_cannot_access_accounts(domain_session_factory):
    session = domain_session_factory("wealth_server")
    with pytest.raises(UnauthorizedTableAccessError):
        session.execute(select(Account))


def test_concierge_cannot_access_transactions(domain_session_factory):
    session = domain_session_factory("concierge_ops_server")
    from data.models.banking.transaction import Transaction

    with pytest.raises(UnauthorizedTableAccessError):
        session.execute(select(Transaction))


def test_concierge_cannot_access_accounts(domain_session_factory):
    session = domain_session_factory("concierge_ops_server")
    with pytest.raises(UnauthorizedTableAccessError):
        session.execute(select(Account))


def test_concierge_cannot_access_policies_or_claims(domain_session_factory):
    session = domain_session_factory("concierge_ops_server")
    with pytest.raises(UnauthorizedTableAccessError):
        session.execute(select(Policy))


def test_concierge_cannot_access_portfolios(domain_session_factory):
    session = domain_session_factory("concierge_ops_server")
    with pytest.raises(UnauthorizedTableAccessError):
        session.execute(select(Portfolio))


# ---------------------------------------------------------------------------
# Negative access via the repository layer directly (not just raw queries):
# an InsuranceRepository instance constructed with a banking_server session
# must fail identically.
# ---------------------------------------------------------------------------
def test_policy_repository_with_banking_session_is_rejected(domain_session_factory):
    session = domain_session_factory("banking_server")
    repo = PolicyRepository(session)
    with pytest.raises(UnauthorizedTableAccessError):
        repo.read_all()


def test_account_repository_with_insurance_session_is_rejected(domain_session_factory):
    session = domain_session_factory("insurance_server")
    repo = AccountRepository(session)
    with pytest.raises(UnauthorizedTableAccessError):
        repo.read_all()


# ---------------------------------------------------------------------------
# Negative access via the write/flush path: session.add() + commit() must
# also be rejected, since this does NOT go through do_orm_execute.
# ---------------------------------------------------------------------------
def test_insurance_session_cannot_write_a_customer_row(domain_session_factory):
    session = domain_session_factory("insurance_server")
    session.add(Customer(customer_business_id="CUS-50000", full_name="X", email="x@x.com", phone="1"))
    with pytest.raises(UnauthorizedTableAccessError):
        session.commit()


def test_banking_session_cannot_write_a_policy_row(domain_session_factory):
    session = domain_session_factory("banking_server")
    session.add(
        Policy(
            policy_id="POL-IN-99999",
            customer_business_id="CUS-20077",
            policy_type="GENERAL",
            premium_amount=100,
            start_date=dt.date(2024, 1, 1),
        )
    )
    with pytest.raises(UnauthorizedTableAccessError):
        session.commit()


# ---------------------------------------------------------------------------
# Same checks again, but against the REAL module-level sessions the four
# server processes actually use (servers/*.py), not a test-constructed
# session. This proves the running servers themselves are isolated, not
# just the access-control mechanism in the abstract.
# ---------------------------------------------------------------------------
def test_real_banking_server_session_is_isolated():
    fastmcp = pytest.importorskip("fastmcp")
    from servers import banking_server

    with pytest.raises(UnauthorizedTableAccessError):
        banking_server._session.execute(select(Policy))


def test_real_insurance_server_session_is_isolated():
    fastmcp = pytest.importorskip("fastmcp")
    from servers import insurance_server

    with pytest.raises(UnauthorizedTableAccessError):
        insurance_server._session.execute(select(Account))


def test_real_wealth_server_session_is_isolated():
    fastmcp = pytest.importorskip("fastmcp")
    from servers import wealth_server

    with pytest.raises(UnauthorizedTableAccessError):
        wealth_server._session.execute(select(Policy))


def test_real_concierge_server_session_is_isolated():
    fastmcp = pytest.importorskip("fastmcp")
    from servers import concierge_ops_server
    from data.models.banking.transaction import Transaction

    with pytest.raises(UnauthorizedTableAccessError):
        concierge_ops_server._session.execute(select(Transaction))


def test_real_banking_server_session_can_read_accounts():
    fastmcp = pytest.importorskip("fastmcp")
    from servers import banking_server

    # Should not raise: accounts is banking_server's own table.
    banking_server._session.execute(select(Account)).scalars().first()


# ---------------------------------------------------------------------------
# Matrix-level sanity: every server's allowlist matches the brief exactly.
# ---------------------------------------------------------------------------
def test_server_table_access_matrix_matches_spec():
    assert SERVER_TABLE_ACCESS["banking_server"] == frozenset({"accounts", "transactions"})
    assert SERVER_TABLE_ACCESS["insurance_server"] == frozenset({"policies", "claims"})
    assert SERVER_TABLE_ACCESS["wealth_server"] == frozenset(
        {"portfolios", "investment_products"}
    )
    assert SERVER_TABLE_ACCESS["concierge_ops_server"] == frozenset(
        {"customers", "interaction_log", "escalation_flags", "audit_log"}
    )
