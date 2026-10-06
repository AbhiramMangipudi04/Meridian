"""
Deterministic, idempotent seed data for the CONCIERGE domain:
customers, interaction_log, escalation_flags.

Concierge is seeded FIRST (see seed.py) because every other domain's
fixtures reference a customer_business_id that must already exist as a
business concept (not a DB foreign key -- just so the demo data is
coherent).
"""
from __future__ import annotations

import datetime as dt

from sqlalchemy.orm import Session
from data.models.concierge.escalation_flag import HARD_ESCALATION_CATEGORIES
from data.repositories.concierge.customer_repository import CustomerRepository
from data.repositories.concierge.escalation_repository import EscalationRepository
from data.repositories.concierge.interaction_repository import InteractionRepository
from data.repositories.errors import RecordNotFoundError
from data.seed.ids import (
    CUSTOMER_ID_RANGE,
    ESCALATION_ID_RANGE,
    INTERACTION_ID_RANGE,
    SHOWCASE_CUSTOMER_ID,
    SHOWCASE_CUSTOMER_NAME,
    customer_business_id,
    deterministic_email,
    deterministic_full_name,
    deterministic_phone,
    escalation_business_id,
    interaction_business_id,
    rng,
)

def _get_or_create_customer(repo: CustomerRepository, business_id: str, **fields):
    try:
        return repo.read_by_id(business_id)
    except RecordNotFoundError:
        return repo.create(customer_business_id=business_id, **fields)


def seed_customers(session: Session) -> list[str]:
    """Returns the full list of seeded customer_business_ids, showcase included."""
    repo = CustomerRepository(session)
    all_ids: list[str] = []

    # Showcase customer -- explicit fixture, never generated.
    _get_or_create_customer(
        repo,
        SHOWCASE_CUSTOMER_ID,
        full_name=SHOWCASE_CUSTOMER_NAME,
        email="arjun.mehta@meridianmail.example",
        phone="+91-9876500077",
        kyc_status="VERIFIED",
        customer_tier="PREMIUM",
        created_at=dt.datetime(2024, 3, 1, 9, 30),
    )
    all_ids.append(SHOWCASE_CUSTOMER_ID)

    for n in CUSTOMER_ID_RANGE:
        business_id = customer_business_id(n)
        full_name = deterministic_full_name(n)
        _get_or_create_customer(
            repo,
            business_id,
            full_name=full_name,
            email=deterministic_email(full_name, n),
            phone=deterministic_phone(n),
            kyc_status="VERIFIED" if n % 9 != 0 else "PENDING",
            customer_tier="PREMIUM" if n % 11 == 0 else "STANDARD",
            created_at=dt.datetime(2024, 1, 1) + dt.timedelta(days=n % 300),
        )
        all_ids.append(business_id)

    return all_ids


def seed_interaction_log(session: Session, customer_ids: list[str]) -> None:
    repo = InteractionRepository(session)
    channels = ("CHAT", "EMAIL", "PHONE", "SMS")
    types = ("balance_inquiry", "coverage_question", "complaint", "auto_debit_setup", "portfolio_query")
    generator = rng()

    for n in INTERACTION_ID_RANGE:
        business_id = interaction_business_id(n)
        try:
            repo.read_by_id(business_id)
            continue  # already seeded
        except RecordNotFoundError:
            pass
        customer = generator.choice(customer_ids)
        repo.create(
            interaction_id=business_id,
            customer_business_id=customer,
            timestamp=dt.datetime(2025, 1, 1) + dt.timedelta(hours=n * 5),
            channel=generator.choice(channels),
            interaction_type=generator.choice(types),
            summary=f"Customer {customer} contacted Meridian regarding a routine service request.",
            status="CLOSED" if n % 5 != 0 else "OPEN",
        )


def seed_escalation_flags(session: Session, customer_ids: list[str]) -> None:
    """
    Deterministic escalation fixtures covering all three hard categories
    required by the brief, plus ordinary confidence-based escalations.
    Escalation data stays exclusively in this Concierge seed module --
    never duplicated into banking/insurance/wealth seed data.
    """
    repo = EscalationRepository(session)
    generator = rng()
    category_cycle = HARD_ESCALATION_CATEGORIES + ("confidence_based", "confidence_based", "none")

    for n in ESCALATION_ID_RANGE:
        business_id = escalation_business_id(n)
        try:
            repo.read_by_id(business_id)
            continue
        except RecordNotFoundError:
            pass
        category = category_cycle[(n - min(ESCALATION_ID_RANGE)) % len(category_cycle)]
        customer = generator.choice(customer_ids)
        notes = {
            "financial_hardship": "Customer disclosed inability to meet upcoming payment obligations.",
            "safeguarding_concern": "Interaction contained signals requiring safeguarding review.",
            "compliance_override_request": "Customer requested an exception to standard compliance policy.",
            "confidence_based": "Drafting agent confidence fell below the auto-resolution threshold.",
            "none": "Routine flag retained for audit completeness; no escalation action required.",
        }[category]
        repo.create(
            escalation_id=business_id,
            customer_business_id=customer,
            category=category,
            request_reference=f"REQ-{n:05d}",
            status="OPEN" if category in HARD_ESCALATION_CATEGORIES else "RESOLVED",
            notes=notes,
            created_at=dt.datetime(2025, 2, 1) + dt.timedelta(days=n),
        )


def seed_concierge(session: Session) -> list[str]:
    customer_ids = seed_customers(session)
    seed_interaction_log(session, customer_ids)
    seed_escalation_flags(session, customer_ids)
    return customer_ids
