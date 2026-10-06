"""
Deterministic ID/name generation helpers and the explicit showcase
fixture constants.

No randomness here comes from system entropy: a single module-level
`random.Random(SEED)` instance is used everywhere, so re-running the seed
process always produces byte-identical business data (determinism
requirement in the project brief). The showcase fixtures are hardcoded
literals, never generated, per the brief's explicit instruction.
"""
from __future__ import annotations

import random

SEED = 20261005  # arbitrary, fixed constant -- never changes across runs
_rng = random.Random(SEED)

# ---------------------------------------------------------------------------
# Showcase fixtures (explicit, not generated) -- see capstone brief §8.1 /
# the Data module brief §14/§16.
# ---------------------------------------------------------------------------
SHOWCASE_CUSTOMER_ID = "CUS-20077"
SHOWCASE_CUSTOMER_NAME = "Arjun Mehta"
SHOWCASE_ACCOUNT_ID = "ACC-20077"
SHOWCASE_POLICY_ID = "POL-IN-30091"

# ---------------------------------------------------------------------------
# Deterministic generation ranges for the rest of the seed data. Ranges are
# chosen so they never collide with the showcase IDs above.
# ---------------------------------------------------------------------------
CUSTOMER_ID_RANGE = range(20001, 20041)       # 40 customers
ACCOUNT_ID_RANGE = range(20001, 20051)        # 50 accounts
TRANSACTION_ID_RANGE = range(500001, 500221)  # 220 transactions
POLICY_ID_RANGE = range(30001, 30041)         # 40 policies (type code GI)
CLAIM_ID_RANGE = range(50001, 50021)          # 20 claims
PORTFOLIO_ID_RANGE = range(10001, 10021)      # 20 portfolios
INTERACTION_ID_RANGE = range(1, 46)           # 45 interactions
ESCALATION_ID_RANGE = range(90001, 90009)     # 8 escalation flags


def customer_business_id(n: int) -> str:
    return f"CUS-{n}"


def account_business_id(n: int) -> str:
    return f"ACC-{n}"


def transaction_business_id(n: int) -> str:
    return f"TXN-{n:06d}"


def policy_business_id(n: int, type_code: str = "GI") -> str:
    return f"POL-{type_code}-{n}"


def claim_business_id(n: int) -> str:
    return f"CLM-{n}"


def portfolio_business_id(n: int) -> str:
    return f"PORT-{n}"


def product_business_id(category_code: str, n: int) -> str:
    return f"PROD-{category_code}-{n:02d}"


def interaction_business_id(n: int) -> str:
    return f"INT-{n:06d}"


def escalation_business_id(n: int) -> str:
    return f"ESC-{n}"


def audit_business_id(n: int) -> str:
    return f"AUD-{n:06d}"


_FIRST_NAMES = [
    "Arjun", "Priya", "Rohan", "Ananya", "Vikram", "Sneha", "Karan", "Divya",
    "Rahul", "Meera", "Aditya", "Kavya", "Sanjay", "Isha", "Nikhil", "Pooja",
    "Varun", "Neha", "Siddharth", "Riya", "Amit", "Shreya", "Gaurav", "Tara",
    "Manoj", "Lakshmi", "Ravi", "Anita", "Suresh", "Deepa", "Kiran", "Nisha",
    "Ajay", "Sunita", "Vijay", "Rekha", "Harish", "Swati", "Mohan", "Geeta",
]
_LAST_NAMES = [
    "Mehta", "Sharma", "Iyer", "Nair", "Reddy", "Gupta", "Patel", "Rao",
    "Chopra", "Desai", "Kulkarni", "Joshi", "Verma", "Bose", "Menon", "Pillai",
    "Agarwal", "Malhotra", "Kapoor", "Bhatt", "Shah", "Saxena", "Banerjee",
    "Chatterjee", "Mukherjee", "Krishnan", "Pandey", "Trivedi", "Suri", "Dutta",
]


def deterministic_full_name(index: int) -> str:
    """Deterministic full name for seed row `index` (does not depend on run order)."""
    first = _FIRST_NAMES[index % len(_FIRST_NAMES)]
    last = _LAST_NAMES[(index * 7 + 3) % len(_LAST_NAMES)]
    return f"{first} {last}"


def deterministic_email(full_name: str, index: int) -> str:
    local = full_name.lower().replace(" ", ".")
    return f"{local}.{index}@meridianmail.example"


def deterministic_phone(index: int) -> str:
    return f"+91-9{(100000000 + index * 37) % 1000000000:09d}"


def rng() -> random.Random:
    """Shared deterministic RNG instance for seed modules that need `choice`/`randint`."""
    return _rng
