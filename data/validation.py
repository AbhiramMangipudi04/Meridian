"""
Business identifier format validation.

These formats come directly from the capstone specification (see the project
brief, Security & Guardrails requirements): every cross-domain business
identifier used anywhere in Nexus must match one fixed, documented pattern.
The Data module is the single place this is defined so that every
model/repository (and, later, every MCP server) validates identically instead
of re-implementing its own regexes.

    CUS-XXXXX      customer_business_id   e.g. CUS-20077
    ACC-XXXXX      account_business_id    e.g. ACC-20077
    POL-XX-XXXXX   policy_business_id     e.g. POL-IN-30091
    PORT-XXXXX     portfolio_business_id  e.g. PORT-10045
    PROD-XX-XX     product_business_id    e.g. PROD-EQ-01
    CLM-XXXXX      claim_business_id      e.g. CLM-50012

A few identifiers are internal to the Concierge domain only and are not part
of the cross-domain contract above (interaction/escalation/audit IDs). They
still get a fixed, deterministic format for consistency, but their shape is
an internal implementation detail of this module rather than a spec-mandated
wire format.
"""
from __future__ import annotations

import re


class InvalidBusinessIdentifierError(ValueError):
    """Raised when a business identifier does not match its required format."""

    def __init__(self, field_name: str, value: str, expected_format: str):
        self.field_name = field_name
        self.value = value
        self.expected_format = expected_format
        super().__init__(
            f"Invalid value for '{field_name}': {value!r} does not match "
            f"required format {expected_format!r}."
        )


# Spec-mandated cross-domain business ID formats.
PATTERNS: dict[str, str] = {
    "customer_business_id": r"^CUS-\d{5}$",
    "account_business_id": r"^ACC-\d{5}$",
    "policy_business_id": r"^POL-[A-Z]{2}-\d{5}$",
    "portfolio_business_id": r"^PORT-\d{5}$",
    "product_business_id": r"^PROD-[A-Z]{2}-\d{2}$",
    "claim_business_id": r"^CLM-\d{5}$",
    # Internal-only identifiers (Concierge domain), not part of the
    # cross-domain wire contract but still validated for consistency.
    "interaction_id": r"^INT-\d{6}$",
    "escalation_id": r"^ESC-\d{5}$",
    "audit_id": r"^AUD-\d{6}$",
    "transaction_id": r"^TXN-\d{6}$",
}

_COMPILED = {name: re.compile(pattern) for name, pattern in PATTERNS.items()}


def validate_business_id(field_name: str, value: str) -> str:
    """
    Validate ``value`` against the named pattern in PATTERNS.

    Returns the value unchanged on success so this can be used inline:
        self.customer_business_id = validate_business_id("customer_business_id", value)

    Raises InvalidBusinessIdentifierError on mismatch, including when value
    is None or not a string.
    """
    pattern = _COMPILED.get(field_name)
    if pattern is None:
        raise KeyError(f"No business-id pattern registered for field '{field_name}'.")
    if not isinstance(value, str) or not pattern.match(value):
        raise InvalidBusinessIdentifierError(field_name, value, PATTERNS[field_name])
    return value


def is_valid_business_id(field_name: str, value: str) -> bool:
    """Boolean, non-raising variant of validate_business_id."""
    try:
        validate_business_id(field_name, value)
        return True
    except InvalidBusinessIdentifierError:
        return False
