from __future__ import annotations

import datetime as dt

import pytest

from data.repositories.banking.account_repository import AccountRepository
from data.repositories.banking.transaction_repository import TransactionRepository
from data.repositories.concierge.customer_repository import CustomerRepository
from data.repositories.errors import (
    DuplicateBusinessIdError,
    InvalidUpdateError,
    RecordNotFoundError,
)
from data.repositories.insurance.policy_repository import PolicyRepository
from data.repositories.wealth.portfolio_repository import PortfolioRepository


# ---------------------------------------------------------------------------
# Customer (concierge_ops_server)
# ---------------------------------------------------------------------------
def test_customer_create_and_read_by_id(domain_session_factory):
    session = domain_session_factory("concierge_ops_server")
    repo = CustomerRepository(session)

    repo.create(
        customer_business_id="CUS-20077",
        full_name="Arjun Mehta",
        email="arjun@example.com",
        phone="+91-9876500077",
    )
    fetched = repo.read_by_id("CUS-20077")
    assert fetched.full_name == "Arjun Mehta"


def test_customer_read_by_id_missing_raises(domain_session_factory):
    session = domain_session_factory("concierge_ops_server")
    repo = CustomerRepository(session)
    with pytest.raises(RecordNotFoundError):
        repo.read_by_id("CUS-99999")


def test_customer_duplicate_business_id_raises(domain_session_factory):
    session = domain_session_factory("concierge_ops_server")
    repo = CustomerRepository(session)
    repo.create(
        customer_business_id="CUS-20001", full_name="A", email="a@example.com", phone="1"
    )
    with pytest.raises(DuplicateBusinessIdError):
        repo.create(
            customer_business_id="CUS-20001", full_name="B", email="b@example.com", phone="2"
        )


def test_customer_update(domain_session_factory):
    session = domain_session_factory("concierge_ops_server")
    repo = CustomerRepository(session)
    repo.create(
        customer_business_id="CUS-20002", full_name="A", email="a@example.com", phone="1"
    )
    updated = repo.update("CUS-20002", kyc_status="PENDING")
    assert updated.kyc_status == "PENDING"


def test_customer_update_cannot_reassign_business_id(domain_session_factory):
    session = domain_session_factory("concierge_ops_server")
    repo = CustomerRepository(session)
    repo.create(
        customer_business_id="CUS-20003", full_name="A", email="a@example.com", phone="1"
    )
    with pytest.raises(InvalidUpdateError):
        repo.update("CUS-20003", customer_business_id="CUS-99999")


def test_customer_update_with_no_fields_raises(domain_session_factory):
    session = domain_session_factory("concierge_ops_server")
    repo = CustomerRepository(session)
    repo.create(
        customer_business_id="CUS-20004", full_name="A", email="a@example.com", phone="1"
    )
    with pytest.raises(InvalidUpdateError):
        repo.update("CUS-20004")


def test_customer_read_all(domain_session_factory):
    session = domain_session_factory("concierge_ops_server")
    repo = CustomerRepository(session)
    for i in range(3):
        repo.create(
            customer_business_id=f"CUS-2010{i}", full_name=f"P{i}", email=f"p{i}@x.com", phone=str(i)
        )
    assert len(repo.read_all()) == 3


# ---------------------------------------------------------------------------
# Banking: Account + Transaction (same-domain FK)
# ---------------------------------------------------------------------------
def test_account_create_and_transaction_fk(domain_session_factory):
    session = domain_session_factory("banking_server")
    account_repo = AccountRepository(session)
    txn_repo = TransactionRepository(session)

    account = account_repo.create(
        account_id="ACC-20077",
        customer_business_id="CUS-20077",
        account_type="SAVINGS",
        balance=1000,
        opened_at=dt.datetime(2024, 1, 1),
    )
    txn_repo.create(
        transaction_id="TXN-500001",
        account_id_fk=account.id,
        amount=250.0,
        transaction_type="DEBIT",
        description="test",
        timestamp=dt.datetime(2025, 1, 1),
    )
    history = txn_repo.read_by_account(account.id)
    assert len(history) == 1
    assert history[0].amount == 250.0


def test_account_read_by_customer(domain_session_factory):
    session = domain_session_factory("banking_server")
    account_repo = AccountRepository(session)
    account_repo.create(
        account_id="ACC-20001",
        customer_business_id="CUS-30001",
        account_type="SAVINGS",
        opened_at=dt.datetime(2024, 1, 1),
    )
    account_repo.create(
        account_id="ACC-20002",
        customer_business_id="CUS-30001",
        account_type="CURRENT",
        opened_at=dt.datetime(2024, 1, 1),
    )
    linked = account_repo.read_by_customer("CUS-30001")
    assert len(linked) == 2


# ---------------------------------------------------------------------------
# Insurance: Policy (showcase fixture)
# ---------------------------------------------------------------------------
def test_policy_showcase_fixture_round_trip(domain_session_factory):
    session = domain_session_factory("insurance_server")
    repo = PolicyRepository(session)
    repo.create(
        policy_id="POL-IN-30091",
        customer_business_id="CUS-20077",
        linked_account_business_id="ACC-20077",
        policy_type="GENERAL",
        premium_amount=4250.0,
        auto_debit_supported=True,
        payment_method="AUTO_DEBIT",
        start_date=dt.date(2024, 3, 10),
    )
    fetched = repo.read_by_id("POL-IN-30091")
    assert fetched.auto_debit_supported is True
    assert fetched.linked_account_business_id == "ACC-20077"


# ---------------------------------------------------------------------------
# Wealth: Portfolio
# ---------------------------------------------------------------------------
def test_portfolio_create_and_read(domain_session_factory):
    session = domain_session_factory("wealth_server")
    repo = PortfolioRepository(session)
    repo.create(
        portfolio_id="PORT-10001",
        customer_business_id="CUS-20077",
        risk_profile="MODERATE",
        total_value=50000,
    )
    fetched = repo.read_by_id("PORT-10001")
    assert fetched.risk_profile == "MODERATE"
