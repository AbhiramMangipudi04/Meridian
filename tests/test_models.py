from __future__ import annotations

import datetime as dt

import pytest
from sqlalchemy import inspect as sa_inspect

from data.models.banking.account import Account
from data.models.banking.transaction import Transaction
from data.models.insurance.claim import Claim
from data.models.insurance.policy import Policy
from data.models.wealth.investment_product import InvestmentProduct
from data.models.wealth.portfolio import Portfolio
from data.models.concierge.customer import Customer
from data.validation import InvalidBusinessIdentifierError


# ---------------------------------------------------------------------------
# Business ID format validation
# ---------------------------------------------------------------------------
def test_account_rejects_invalid_account_id():
    with pytest.raises(InvalidBusinessIdentifierError):
        Account(
            account_id="NOT-VALID",
            customer_business_id="CUS-20077",
            account_type="SAVINGS",
            opened_at=dt.datetime.utcnow(),
        )


def test_account_rejects_invalid_customer_business_id():
    with pytest.raises(InvalidBusinessIdentifierError):
        Account(
            account_id="ACC-20077",
            customer_business_id="12345",
            account_type="SAVINGS",
            opened_at=dt.datetime.utcnow(),
        )


def test_account_accepts_valid_ids():
    account = Account(
        account_id="ACC-20077",
        customer_business_id="CUS-20077",
        account_type="SAVINGS",
        opened_at=dt.datetime.utcnow(),
    )
    assert account.account_id == "ACC-20077"


def test_policy_id_format_requires_two_letter_code():
    with pytest.raises(InvalidBusinessIdentifierError):
        Policy(
            policy_id="POL-30091",  # missing the 2-letter type code
            customer_business_id="CUS-20077",
            policy_type="GENERAL",
            premium_amount=100,
            start_date=dt.date(2024, 1, 1),
        )


def test_policy_accepts_valid_showcase_id():
    policy = Policy(
        policy_id="POL-IN-30091",
        customer_business_id="CUS-20077",
        policy_type="GENERAL",
        premium_amount=4250,
        auto_debit_supported=True,
        start_date=dt.date(2024, 3, 10),
    )
    assert policy.auto_debit_supported is True


def test_portfolio_id_format():
    with pytest.raises(InvalidBusinessIdentifierError):
        Portfolio(portfolio_id="PORTFOLIO-1", customer_business_id="CUS-20077")


def test_investment_product_id_format():
    with pytest.raises(InvalidBusinessIdentifierError):
        InvestmentProduct(product_id="PROD-EQUITY-1", name="x", category="EQUITY")


def test_claim_id_format():
    with pytest.raises(InvalidBusinessIdentifierError):
        Claim(
            claim_id="CLAIM-1",
            policy_id_fk=1,
            customer_business_id="CUS-20077",
            claim_type="ACCIDENT",
            amount_claimed=100,
            filed_at=dt.datetime.utcnow(),
        )


def test_customer_business_id_format():
    with pytest.raises(InvalidBusinessIdentifierError):
        Customer(customer_business_id="20077", full_name="x", email="x@x.com", phone="123")


# ---------------------------------------------------------------------------
# Same-domain FK works; cross-domain FKs structurally do not exist
# ---------------------------------------------------------------------------
def test_transaction_has_same_domain_fk_to_accounts():
    mapper = sa_inspect(Transaction)
    fk_targets = {
        fk.target_fullname for column in mapper.columns for fk in column.foreign_keys
    }
    assert any(target.startswith("accounts.") for target in fk_targets)


def test_claim_has_same_domain_fk_to_policies():
    mapper = sa_inspect(Claim)
    fk_targets = {
        fk.target_fullname for column in mapper.columns for fk in column.foreign_keys
    }
    assert any(target.startswith("policies.") for target in fk_targets)


@pytest.mark.parametrize(
    "model, forbidden_prefixes",
    [
        (Account, ("customers.",)),
        (Transaction, ("customers.", "policies.", "portfolios.")),
        (Policy, ("customers.", "accounts.")),
        (Claim, ("customers.", "accounts.")),
        (Portfolio, ("customers.",)),
        (InvestmentProduct, ("customers.", "portfolios.")),
    ],
)
def test_model_has_no_cross_domain_foreign_keys(model, forbidden_prefixes):
    mapper = sa_inspect(model)
    fk_targets = {
        fk.target_fullname for column in mapper.columns for fk in column.foreign_keys
    }
    for target in fk_targets:
        assert not any(target.startswith(prefix) for prefix in forbidden_prefixes), (
            f"{model.__name__} has a forbidden cross-domain foreign key to {target}"
        )


def test_model_has_no_cross_domain_orm_relationships():
    """
    Every declared relationship() on these models must point at a mapper
    whose table is in the SAME domain. This directly enforces requirement
    #7 in the brief: no `customer = relationship("Customer")` inside
    Account/Policy, no `account = relationship("Account")` inside Policy.
    """
    same_domain_tables = {
        "accounts": {"accounts", "transactions"},
        "transactions": {"accounts", "transactions"},
        "policies": {"policies", "claims"},
        "claims": {"policies", "claims"},
        "portfolios": {"portfolios", "investment_products"},
        "investment_products": {"portfolios", "investment_products"},
    }

    for model in (Account, Transaction, Policy, Claim, Portfolio, InvestmentProduct):
        mapper = sa_inspect(model)
        allowed = same_domain_tables[model.__tablename__]
        for rel in mapper.relationships:
            target_table = rel.mapper.local_table.name
            assert target_table in allowed, (
                f"{model.__name__}.{rel.key} relationship reaches into "
                f"'{target_table}', outside its own domain."
            )
