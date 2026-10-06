"""
Deterministic, idempotent seed data for the BANKING domain: accounts,
transactions. Seeded second (after concierge), per the controlled
seed-dependency order in the project brief -- there are no database-level
foreign keys to concierge, only a coherent re-use of customer business IDs.
"""
from __future__ import annotations

import datetime as dt

from sqlalchemy.orm import Session

from data.repositories.banking.account_repository import AccountRepository
from data.repositories.banking.transaction_repository import TransactionRepository
from data.repositories.errors import RecordNotFoundError
from data.seed.ids import (
    ACCOUNT_ID_RANGE,
    SHOWCASE_ACCOUNT_ID,
    SHOWCASE_CUSTOMER_ID,
    TRANSACTION_ID_RANGE,
    account_business_id,
    rng,
    transaction_business_id,
)

ACCOUNT_TYPES = ("SAVINGS", "CURRENT")


def seed_accounts(session: Session, customer_ids: list[str]) -> list[str]:
    """Returns the full list of seeded account_business_ids, showcase included."""
    repo = AccountRepository(session)
    generator = rng()
    all_ids: list[str] = []

    # Showcase account -- explicit fixture, never generated.
    try:
        repo.read_by_id(SHOWCASE_ACCOUNT_ID)
    except RecordNotFoundError:
        repo.create(
            account_id=SHOWCASE_ACCOUNT_ID,
            customer_business_id=SHOWCASE_CUSTOMER_ID,
            account_type="SAVINGS",
            balance=142350.75,
            currency="INR",
            status="ACTIVE",
            opened_at=dt.datetime(2024, 3, 2, 10, 0),
        )
    all_ids.append(SHOWCASE_ACCOUNT_ID)

    non_showcase_customers = [c for c in customer_ids if c != SHOWCASE_CUSTOMER_ID]
    for n in ACCOUNT_ID_RANGE:
        business_id = account_business_id(n)
        try:
            repo.read_by_id(business_id)
            all_ids.append(business_id)
            continue
        except RecordNotFoundError:
            pass
        customer = non_showcase_customers[n % len(non_showcase_customers)]
        repo.create(
            account_id=business_id,
            customer_business_id=customer,
            account_type=generator.choice(ACCOUNT_TYPES),
            balance=round(generator.uniform(500, 250000), 2),
            currency="INR",
            status="ACTIVE" if n % 17 != 0 else "DORMANT",
            opened_at=dt.datetime(2023, 6, 1) + dt.timedelta(days=n % 500),
        )
        all_ids.append(business_id)

    return all_ids


def seed_transactions(session: Session, account_ids: list[str]) -> None:
    account_repo = AccountRepository(session)
    txn_repo = TransactionRepository(session)
    generator = rng()
    txn_types = ("DEBIT", "CREDIT")
    descriptions = (
        "POS purchase", "Salary credit", "UPI transfer", "ATM withdrawal",
        "Bill payment", "Interest credit", "Insurance premium debit",
    )

    # Resolve account business IDs to internal PKs once, up front.
    account_pk_by_business_id = {bid: account_repo.read_by_id(bid).id for bid in account_ids}

    for n in TRANSACTION_ID_RANGE:
        business_id = transaction_business_id(n)
        try:
            txn_repo.read_by_id(business_id)
            continue
        except RecordNotFoundError:
            pass
        account_business_id_choice = generator.choice(account_ids)
        amount = round(generator.uniform(50, 15000), 2)
        txn_repo.create(
            transaction_id=business_id,
            account_id_fk=account_pk_by_business_id[account_business_id_choice],
            amount=amount,
            currency="INR",
            transaction_type=generator.choice(txn_types),
            description=generator.choice(descriptions),
            status="POSTED",
            timestamp=dt.datetime(2025, 6, 1) + dt.timedelta(hours=n),
        )


def seed_banking(session: Session, customer_ids: list[str]) -> list[str]:
    account_ids = seed_accounts(session, customer_ids)
    seed_transactions(session, account_ids)
    return account_ids
