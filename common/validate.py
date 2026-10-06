"""
Centralized input validation for the MCP server layer.

Every MCP Tool/Resource argument that carries a business identifier,
caller scope, or other constrained value must pass through this module
BEFORE any repository/database call. Business-ID *format* patterns are
not re-declared here -- they are imported from `data/validation.py`,
which remains the single source of truth for format strings shared
between the Data module and this MCP layer. This module adds the
MCP-facing error type and the additional enums (caller scope, channel,
risk profile, ...) that only matter at the server boundary.
"""
from __future__ import annotations

import re

from data.validation import (
    InvalidBusinessIdentifierError,
    PATTERNS,
    validate_business_id as _validate_business_id_format,
)


class ValidationError(ValueError):
    """Raised by every validator in this module. Always safe to show to
    an MCP client: it never contains internal paths, stack traces, or
    secrets -- only the field name, the offending value, and the reason."""

    def __init__(self, field_name: str, value, reason: str):
        self.field_name = field_name
        self.value = value
        self.reason = reason
        super().__init__(f"Invalid value for '{field_name}': {value!r} -- {reason}")


# ---------------------------------------------------------------------------
# Business identifiers (delegates to data/validation.py's patterns)
# ---------------------------------------------------------------------------
def validate_business_id(field_name: str, value: str) -> str:
    """
    field_name must be one of the keys in data.validation.PATTERNS, e.g.
    "account_business_id", "customer_business_id", "policy_business_id",
    "portfolio_business_id", "product_business_id", "claim_business_id".
    """
    try:
        return _validate_business_id_format(field_name, value)
    except InvalidBusinessIdentifierError as exc:
        raise ValidationError(field_name, value, f"must match format {PATTERNS[field_name]!r}") from exc
    except KeyError as exc:
        raise ValidationError(field_name, value, "unknown business-id field") from exc


# ---------------------------------------------------------------------------
# Caller scope -- explicit, closed set. No arbitrary strings accepted.
# ---------------------------------------------------------------------------
ALLOWED_CALLER_SCOPES = (
    "user",
    "bank_manager",
    "policy_manager",
    "wealth_manager",
    "operations",
)


def validate_caller_scope(value: str) -> str:
    if not isinstance(value, str) or value not in ALLOWED_CALLER_SCOPES:
        raise ValidationError(
            "caller_scope", value, f"must be one of {ALLOWED_CALLER_SCOPES}"
        )
    return value


# ---------------------------------------------------------------------------
# Notification channel
# ---------------------------------------------------------------------------
ALLOWED_CHANNELS = ("CHAT", "EMAIL", "PHONE", "SMS")


def validate_channel(value: str) -> str:
    if not isinstance(value, str) or value.upper() not in ALLOWED_CHANNELS:
        raise ValidationError("channel", value, f"must be one of {ALLOWED_CHANNELS}")
    return value.upper()


# ---------------------------------------------------------------------------
# Risk profile
# ---------------------------------------------------------------------------
ALLOWED_RISK_PROFILES = ("CONSERVATIVE", "MODERATE", "AGGRESSIVE")


def validate_risk_profile(value: str) -> str:
    if not isinstance(value, str) or value.upper() not in ALLOWED_RISK_PROFILES:
        raise ValidationError("risk_profile", value, f"must be one of {ALLOWED_RISK_PROFILES}")
    return value.upper()


# ---------------------------------------------------------------------------
# Escalation / request category
# ---------------------------------------------------------------------------
HARD_ESCALATION_CATEGORIES = (
    "financial_hardship",
    "safeguarding_concern",
    "compliance_override_request",
)


def validate_request_category(value: str) -> str:
    """
    Hard categories are a closed set; anything else is accepted as a
    free-form (but length- and charset-limited) classification label, so
    the intake layer's own request_type enum (balance_inquiry,
    coverage_question, complaint, "normal_request", etc.) is not
    duplicated/hardcoded here. The hard-category check itself
    (run_escalation_check) only ever compares against the closed
    HARD_ESCALATION_CATEGORIES tuple, never against this permissive set.
    """
    if not isinstance(value, str) or not value:
        raise ValidationError("request_category", value, "must be a non-empty string")
    if not re.fullmatch(r"[a-z0-9_]{1,64}", value):
        raise ValidationError(
            "request_category", value, "must be lowercase snake_case, max 64 chars"
        )
    return value


# ---------------------------------------------------------------------------
# Confidence score
# ---------------------------------------------------------------------------
def validate_confidence(value) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise ValidationError("draft_confidence", value, "must be a number") from exc
    if not (0.0 <= number <= 1.0):
        raise ValidationError("draft_confidence", value, "must be between 0.0 and 1.0")
    return number


# ---------------------------------------------------------------------------
# Transaction-history limit
# ---------------------------------------------------------------------------
def validate_limit(value, minimum: int = 1, maximum: int = 100) -> int:
    try:
        number = int(value)
    except (TypeError, ValueError) as exc:
        raise ValidationError("limit", value, "must be an integer") from exc
    if not (minimum <= number <= maximum):
        raise ValidationError("limit", value, f"must be between {minimum} and {maximum}")
    return number


# ---------------------------------------------------------------------------
# Free text (length/charset only -- sanitization/injection detection lives
# in common/guardrails.py, which is a distinct responsibility)
# ---------------------------------------------------------------------------
def validate_non_empty_text(value: str, field_name: str, max_length: int = 2000) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValidationError(field_name, value, "must be a non-empty string")
    if len(value) > max_length:
        raise ValidationError(field_name, value, f"must not exceed {max_length} characters")
    return value


# ---------------------------------------------------------------------------
# Knowledge-base document identifiers (not a cross-domain business ID --
# just a filesystem-safe slug used by the knowledgebase:// resource)
# ---------------------------------------------------------------------------
_DOCUMENT_ID_PATTERN = re.compile(r"^[a-z0-9_\-]{1,100}$")


def validate_document_id(value: str) -> str:
    if not isinstance(value, str) or not _DOCUMENT_ID_PATTERN.match(value):
        raise ValidationError(
            "document_id", value, "must be a lowercase slug (letters, digits, '_' and '-' only)"
        )
    return value


# ---------------------------------------------------------------------------
# Scenario tag (check_coverage_clause)
# ---------------------------------------------------------------------------
_SCENARIO_TAG_PATTERN = re.compile(r"^[a-z0-9_]{1,64}$")


def validate_scenario_tag(value: str) -> str:
    if not isinstance(value, str) or not _SCENARIO_TAG_PATTERN.match(value):
        raise ValidationError(
            "scenario_tag", value, "must be lowercase snake_case, max 64 chars"
        )
    return value
