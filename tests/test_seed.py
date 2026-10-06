from __future__ import annotations

from data.database.session import get_unrestricted_session
from data.repositories.banking.account_repository import AccountRepository
from data.repositories.concierge.customer_repository import CustomerRepository
from data.repositories.insurance.policy_repository import PolicyRepository
from data.seed.ids import SHOWCASE_ACCOUNT_ID, SHOWCASE_CUSTOMER_ID, SHOWCASE_POLICY_ID
from data.seed.seed import run_seed


def test_seed_is_idempotent(seeded_schema):
    run_seed(db_path=seeded_schema)
    session = get_unrestricted_session(db_path=seeded_schema)
    try:
        customers_after_first = CustomerRepository(session).read_all()
        count_first = len(customers_after_first)
    finally:
        session.close()

    # Run again -- must not raise DuplicateBusinessIdError, and must not
    # change the row count.
    run_seed(db_path=seeded_schema)
    session = get_unrestricted_session(db_path=seeded_schema)
    try:
        count_second = len(CustomerRepository(session).read_all())
    finally:
        session.close()

    assert count_first == count_second
    assert count_first >= 25  # spec: 25-50 customers


def test_seed_showcase_fixtures_exist(seeded_schema):
    run_seed(db_path=seeded_schema)
    session = get_unrestricted_session(db_path=seeded_schema)
    try:
        customer = CustomerRepository(session).read_by_id(SHOWCASE_CUSTOMER_ID)
        account = AccountRepository(session).read_by_id(SHOWCASE_ACCOUNT_ID)
        policy = PolicyRepository(session).read_by_id(SHOWCASE_POLICY_ID)
    finally:
        session.close()

    assert customer.full_name == "Arjun Mehta"
    assert account.customer_business_id == SHOWCASE_CUSTOMER_ID
    assert policy.customer_business_id == SHOWCASE_CUSTOMER_ID
    assert policy.linked_account_business_id == SHOWCASE_ACCOUNT_ID
    assert policy.auto_debit_supported is True


def test_seed_data_volumes_within_spec_guidelines(seeded_schema):
    run_seed(db_path=seeded_schema)
    session = get_unrestricted_session(db_path=seeded_schema)
    try:
        from data.repositories.banking.transaction_repository import TransactionRepository
        from data.repositories.concierge.escalation_repository import EscalationRepository
        from data.repositories.concierge.interaction_repository import InteractionRepository
        from data.repositories.insurance.claim_repository import ClaimRepository
        from data.repositories.wealth.investment_product_repository import (
            InvestmentProductRepository,
        )
        from data.repositories.wealth.portfolio_repository import PortfolioRepository

        assert 25 <= len(CustomerRepository(session).read_all()) <= 50
        assert 40 <= len(AccountRepository(session).read_all()) <= 70
        assert 150 <= len(TransactionRepository(session).read_all()) <= 300
        assert 25 <= len(PolicyRepository(session).read_all()) <= 50
        assert 15 <= len(ClaimRepository(session).read_all()) <= 30
        assert 15 <= len(PortfolioRepository(session).read_all()) <= 30
        assert 10 <= len(InvestmentProductRepository(session).read_all()) <= 15
        assert 30 <= len(InteractionRepository(session).read_all()) <= 60
        assert 5 <= len(EscalationRepository(session).read_all()) <= 10
    finally:
        session.close()


def test_hard_escalation_categories_represented(seeded_schema):
    run_seed(db_path=seeded_schema)
    session = get_unrestricted_session(db_path=seeded_schema)
    try:
        from data.repositories.concierge.escalation_repository import EscalationRepository

        repo = EscalationRepository(session)
        categories = {flag.category for flag in repo.read_all()}
    finally:
        session.close()

    for required in ("financial_hardship", "safeguarding_concern", "compliance_override_request"):
        assert required in categories
