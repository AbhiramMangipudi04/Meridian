"""
Deterministic, idempotent seed data for the INSURANCE domain: policies,
claims. Seeded third, after concierge and banking.
"""
from __future__ import annotations

import datetime as dt

from sqlalchemy.orm import Session

from data.repositories.errors import RecordNotFoundError
from data.repositories.insurance.claim_repository import ClaimRepository
from data.repositories.insurance.policy_repository import PolicyRepository
from data.seed.ids import (
    CLAIM_ID_RANGE,
    POLICY_ID_RANGE,
    SHOWCASE_ACCOUNT_ID,
    SHOWCASE_CUSTOMER_ID,
    SHOWCASE_POLICY_ID,
    claim_business_id,
    policy_business_id,
    rng,
)

POLICY_TYPES = ("GENERAL", "HEALTH", "MOTOR", "HOME")
CLAIM_TYPES = ("ACCIDENT", "THEFT", "MEDICAL", "PROPERTY_DAMAGE")


def seed_policies(session: Session, customer_ids: list[str]) -> list[str]:
    repo = PolicyRepository(session)
    generator = rng()
    all_ids: list[str] = []

    # Showcase policy -- explicit fixture. auto_debit_supported=True here is
    # the STRUCTURED, authoritative answer the showcase scenario depends on;
    # see data/docs/policy_docs for the deliberately-looser unstructured
    # wording that creates the retrieval-conflict fixture.
    try:
        repo.read_by_id(SHOWCASE_POLICY_ID)
    except RecordNotFoundError:
        repo.create(
            policy_id=SHOWCASE_POLICY_ID,
            customer_business_id=SHOWCASE_CUSTOMER_ID,
            linked_account_business_id=SHOWCASE_ACCOUNT_ID,
            policy_type="GENERAL",
            status="ACTIVE",
            premium_amount=4250.00,
            premium_frequency="MONTHLY",
            auto_debit_supported=True,
            payment_method="AUTO_DEBIT",
            start_date=dt.date(2024, 3, 10),
        )
    all_ids.append(SHOWCASE_POLICY_ID)

    non_showcase_customers = [c for c in customer_ids if c != SHOWCASE_CUSTOMER_ID]
    for n in POLICY_ID_RANGE:
        business_id = policy_business_id(n, type_code="GI")
        try:
            repo.read_by_id(business_id)
            all_ids.append(business_id)
            continue
        except RecordNotFoundError:
            pass
        customer = non_showcase_customers[n % len(non_showcase_customers)]
        auto_debit = n % 3 == 0
        repo.create(
            policy_id=business_id,
            customer_business_id=customer,
            policy_type=generator.choice(POLICY_TYPES),
            status="ACTIVE" if n % 13 != 0 else "LAPSED",
            premium_amount=round(generator.uniform(500, 8000), 2),
            premium_frequency=generator.choice(("MONTHLY", "QUARTERLY", "ANNUAL")),
            auto_debit_supported=auto_debit,
            payment_method="AUTO_DEBIT" if auto_debit else "MANUAL",
            start_date=dt.date(2023, 1, 1) + dt.timedelta(days=n % 700),
        )
        all_ids.append(business_id)

    return all_ids


def seed_claims(session: Session, policy_ids: list[str]) -> None:
    policy_repo = PolicyRepository(session)
    claim_repo = ClaimRepository(session)
    generator = rng()

    policy_pk_and_customer = {
        pid: (policy_repo.read_by_id(pid).id, policy_repo.read_by_id(pid).customer_business_id)
        for pid in policy_ids
    }

    for n in CLAIM_ID_RANGE:
        business_id = claim_business_id(n)
        try:
            claim_repo.read_by_id(business_id)
            continue
        except RecordNotFoundError:
            pass
        policy_choice = generator.choice(policy_ids)
        policy_pk, customer_business_id = policy_pk_and_customer[policy_choice]
        claim_repo.create(
            claim_id=business_id,
            policy_id_fk=policy_pk,
            customer_business_id=customer_business_id,
            claim_type=generator.choice(CLAIM_TYPES),
            status=generator.choice(("SUBMITTED", "UNDER_REVIEW", "APPROVED", "REJECTED")),
            amount_claimed=round(generator.uniform(1000, 50000), 2),
            filed_at=dt.datetime(2025, 3, 1) + dt.timedelta(days=n),
        )


def seed_insurance(session: Session, customer_ids: list[str]) -> list[str]:
    policy_ids = seed_policies(session, customer_ids)
    seed_claims(session, policy_ids)
    return policy_ids
