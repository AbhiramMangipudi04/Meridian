"""
Deterministic seed orchestrator.

Runs each domain's seed module in the controlled order required by the
brief (Concierge -> Banking -> Insurance -> Wealth) so that
customer_business_id values exist as a coherent business concept before
other domains' fixtures reference them. There are NO database-level
foreign keys enforcing this order -- it is purely about producing
sensible demo data.

Idempotent: every seed_* function checks for an existing row by business
ID before inserting, so running this twice does not create duplicates or
raise DuplicateBusinessIdError.

Uses the UNRESTRICTED session on purpose: the seed process is
infrastructure, not server traffic, and must be able to write to every
domain in one coordinated run. No server or repository caller outside of
this module should ever request an unrestricted session.
"""
from __future__ import annotations

from data.database.session import get_unrestricted_session
from data.seed.banking_seed import seed_banking
from data.seed.concierge_seed import seed_concierge
from data.seed.insurance_seed import seed_insurance
from data.seed.wealth_seed import seed_wealth


def run_seed(db_path: str | None = None) -> None:
    session = get_unrestricted_session(db_path)
    try:
        customer_ids = seed_concierge(session)
        seed_banking(session, customer_ids)
        seed_insurance(session, customer_ids)
        seed_wealth(session, customer_ids)
    finally:
        session.close()


if __name__ == "__main__":
    run_seed()
    print("Seeding complete.")
