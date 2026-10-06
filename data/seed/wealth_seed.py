"""
Deterministic, idempotent seed data for the WEALTH domain: portfolios,
investment_products. Seeded last, after concierge, banking, and insurance.
"""
from __future__ import annotations

import datetime as dt

from sqlalchemy.orm import Session

from data.repositories.errors import RecordNotFoundError
from data.repositories.wealth.investment_product_repository import InvestmentProductRepository
from data.repositories.wealth.portfolio_repository import PortfolioRepository
from data.seed.ids import PORTFOLIO_ID_RANGE, portfolio_business_id, product_business_id, rng

RISK_PROFILES = ("CONSERVATIVE", "MODERATE", "AGGRESSIVE")

PRODUCT_CATALOG = [
    ("EQ", "Meridian Large Cap Equity Fund", "EQUITY", "AGGRESSIVE", 5000),
    ("EQ", "Meridian Mid Cap Growth Fund", "EQUITY", "AGGRESSIVE", 5000),
    ("EQ", "Meridian Index Tracker Fund", "EQUITY", "MODERATE", 2500),
    ("DT", "Meridian Short Duration Debt Fund", "DEBT", "CONSERVATIVE", 1000),
    ("DT", "Meridian Corporate Bond Fund", "DEBT", "CONSERVATIVE", 1000),
    ("DT", "Meridian Gilt Fund", "DEBT", "CONSERVATIVE", 1000),
    ("HY", "Meridian Balanced Advantage Fund", "HYBRID", "MODERATE", 2000),
    ("HY", "Meridian Conservative Hybrid Fund", "HYBRID", "CONSERVATIVE", 2000),
    ("GL", "Meridian Gold Savings Fund", "COMMODITY", "MODERATE", 1500),
    ("GL", "Meridian Global Diversified Fund", "EQUITY", "AGGRESSIVE", 5000),
    ("FX", "Meridian US Opportunities Fund", "EQUITY", "AGGRESSIVE", 5000),
    ("FX", "Meridian Emerging Markets Fund", "EQUITY", "AGGRESSIVE", 5000),
]


def seed_investment_products(session: Session) -> list[str]:
    repo = InvestmentProductRepository(session)
    all_ids: list[str] = []
    counters: dict[str, int] = {}

    for category_code, name, category, risk_rating, min_investment in PRODUCT_CATALOG:
        counters[category_code] = counters.get(category_code, 0) + 1
        business_id = product_business_id(category_code, counters[category_code])
        try:
            repo.read_by_id(business_id)
            all_ids.append(business_id)
            continue
        except RecordNotFoundError:
            pass
        repo.create(
            product_id=business_id,
            name=name,
            category=category,
            risk_rating=risk_rating,
            min_investment=min_investment,
            description=f"{name} is a {category.lower()} product suited to {risk_rating.lower()} risk investors.",
        )
        all_ids.append(business_id)

    return all_ids


def seed_portfolios(session: Session, customer_ids: list[str]) -> list[str]:
    repo = PortfolioRepository(session)
    generator = rng()
    all_ids: list[str] = []

    for n in PORTFOLIO_ID_RANGE:
        business_id = portfolio_business_id(n)
        try:
            repo.read_by_id(business_id)
            all_ids.append(business_id)
            continue
        except RecordNotFoundError:
            pass
        customer = customer_ids[n % len(customer_ids)]
        repo.create(
            portfolio_id=business_id,
            customer_business_id=customer,
            risk_profile=generator.choice(RISK_PROFILES),
            total_value=round(generator.uniform(10000, 2000000), 2),
            currency="INR",
            status="ACTIVE",
        )
        all_ids.append(business_id)

    return all_ids


def seed_wealth(session: Session, customer_ids: list[str]) -> None:
    seed_investment_products(session)
    seed_portfolios(session, customer_ids)
