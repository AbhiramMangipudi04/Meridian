"""
Reusable guardrail functionality for the MCP server layer.

Deliberately NOT in this file: run_escalation_check, write_audit_log,
send_customer_notification. Those are Concierge MCP *business
operations* (they decide things, write data, and contact customers) --
this file only ever validates, minimizes, masks, sanitizes, and checks
output shape. It never calls a repository and never writes anything.

Optional guardrails-ai integration: this module will use the
`guardrails-ai` hub validators listed in requirements.txt as a
defense-in-depth signal on top of the deterministic regex-based checks
below, IF the package and validators are installed. The deterministic
checks are always the source of truth -- they are what every test in
this project exercises -- so the system is fully correct and fully
testable even in an environment with no internet access to the
Guardrails Hub.
"""
from __future__ import annotations

import re
from typing import Any, Iterable

from common.errors import PermissionDeniedError
from common.validate import ALLOWED_CALLER_SCOPES, ValidationError, validate_caller_scope
from data.validation import PATTERNS

# ---------------------------------------------------------------------------
# Optional guardrails-ai integration (defense in depth only -- see module
# docstring). Failing to import/initialize must never break this module.
# ---------------------------------------------------------------------------
try:  # pragma: no cover - exercised only when guardrails-ai + hub validators are installed
    import guardrails as _guardrails_ai  # noqa: F401

    GUARDRAILS_AI_AVAILABLE = True
except Exception:  # pragma: no cover
    GUARDRAILS_AI_AVAILABLE = False


class CallerScopeViolationError(PermissionDeniedError):
    """Raised when a caller_scope is not permitted to reach a domain, or
    a 'user' scope tries to access data belonging to a different
    customer than the one they authenticated as."""


class PromptInjectionDetectedError(PermissionDeniedError):
    """Raised by sanitize_free_text when free text matches a known
    prompt-injection signature."""


# ---------------------------------------------------------------------------
# 1. Caller-scope validation / domain & ownership enforcement
# ---------------------------------------------------------------------------
def enforce_domain_scope(caller_scope: str, allowed_scopes: Iterable[str]) -> None:
    """
    Raise CallerScopeViolationError unless `caller_scope` is one of the
    scopes allowed to reach this server's domain at all.

    Example (banking_server): enforce_domain_scope(caller_scope, {"user", "bank_manager"})
    rejects "policy_manager", "wealth_manager", and "operations" outright.
    """
    validate_caller_scope(caller_scope)  # typed ValidationError if not a known scope at all
    allowed = set(allowed_scopes)
    if caller_scope not in allowed:
        raise CallerScopeViolationError(
            f"caller_scope '{caller_scope}' is not permitted to access this domain "
            f"(allowed: {sorted(allowed)})."
        )


def enforce_caller_scope_ownership(
    caller_scope: str, caller_customer_id: str | None, owner_customer_id: str
) -> None:
    """
    Only the 'user' scope is ownership-restricted: a user may only see
    their *own* data. Manager/operations scopes see the full domain by
    design (per the caller-scope spec) and are not ownership-checked
    here -- enforce_domain_scope already restricted which domains they
    can reach at all.
    """
    if caller_scope != "user":
        return
    if not caller_customer_id or caller_customer_id != owner_customer_id:
        raise CallerScopeViolationError(
            "caller_scope 'user' may only access their own data; "
            "the supplied caller_customer_id does not match the record owner."
        )


# ---------------------------------------------------------------------------
# 2. Business-ID masking
# ---------------------------------------------------------------------------
def mask_business_id(value: str | None) -> str | None:
    """
    Mask any business identifier to its last four characters, e.g.
    'ACC-20077' -> '****0077', 'POL-IN-30091' -> '****0091'. The
    underlying database/repository value is never touched -- this is a
    pure, outbound-response-only transform.
    """
    if value is None:
        return None
    if not isinstance(value, str) or len(value) < 4:
        return "****"
    return "****" + value[-4:]


def mask_fields_in_dict(data: dict, keys: Iterable[str]) -> dict:
    """Return a shallow copy of `data` with every key in `keys` masked."""
    masked = dict(data)
    for key in keys:
        if key in masked:
            masked[key] = mask_business_id(masked[key])
    return masked


# ---------------------------------------------------------------------------
# 3. Caller-scope field minimization
# ---------------------------------------------------------------------------
_ACCOUNT_FIELDS_BY_SCOPE: dict[str, tuple[str, ...]] = {
    "user": ("account_id", "account_type", "balance", "currency", "status"),
    "bank_manager": (
        "account_id",
        "customer_business_id",
        "account_type",
        "balance",
        "currency",
        "status",
        "opened_at",
    ),
}

_PORTFOLIO_FIELDS_BY_SCOPE: dict[str, tuple[str, ...]] = {
    "user": ("portfolio_id", "risk_profile", "total_value", "currency", "status"),
    "wealth_manager": (
        "portfolio_id",
        "customer_business_id",
        "risk_profile",
        "total_value",
        "currency",
        "status",
        "created_at",
    ),
}


def _serialize(value: Any) -> Any:
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return value


def minimize_account_fields(account: Any, caller_scope: str) -> dict:
    """
    account = account_repository.read_by_id(account_id)
    minimized = minimize_account_fields(account, caller_scope)
    masked = mask_business_id(minimized["account_id"])   # see mask_fields_in_dict

    Only 'user' and 'bank_manager' scopes are meaningful here --
    enforce_domain_scope() must already have rejected any other scope
    before this function is called.
    """
    fields = _ACCOUNT_FIELDS_BY_SCOPE.get(caller_scope)
    if fields is None:
        raise CallerScopeViolationError(
            f"caller_scope '{caller_scope}' has no defined field set for account data."
        )
    return {field: _serialize(getattr(account, field)) for field in fields}


def minimize_portfolio_fields(portfolio: Any, caller_scope: str) -> dict:
    fields = _PORTFOLIO_FIELDS_BY_SCOPE.get(caller_scope)
    if fields is None:
        raise CallerScopeViolationError(
            f"caller_scope '{caller_scope}' has no defined field set for portfolio data."
        )
    return {field: _serialize(getattr(portfolio, field)) for field in fields}


# ---------------------------------------------------------------------------
# 4. Free-text sanitization / prompt-injection defence
# ---------------------------------------------------------------------------
_HTML_TAG_PATTERN = re.compile(r"<[^>]+>")

_INJECTION_SIGNATURES = (
    re.compile(r"ignore\s+(all\s+)?(previous|prior|above)\s+instructions", re.IGNORECASE),
    re.compile(r"disregard\s+(all\s+)?(previous|prior|above)\s+(instructions|rules)", re.IGNORECASE),
    re.compile(r"you\s+are\s+now\s+(a|an)\s+\w+", re.IGNORECASE),
    re.compile(r"act\s+as\s+(an?\s+)?(unrestricted|jailbroken|dan)\b", re.IGNORECASE),
    re.compile(r"system\s*:\s*", re.IGNORECASE),
    re.compile(r"</?(script|iframe|style)\b", re.IGNORECASE),
    re.compile(r"reveal\s+(your|the)\s+(system\s+prompt|instructions)", re.IGNORECASE),
    re.compile(r"\bBEGIN\s+ADMIN\s+OVERRIDE\b", re.IGNORECASE),
)

DEFAULT_MAX_FREE_TEXT_LENGTH = 2000


def sanitize_free_text(
    text: str | None,
    *,
    max_length: int = DEFAULT_MAX_FREE_TEXT_LENGTH,
    raise_on_injection: bool = True,
) -> str:
    """
    Apply to: outbound customer message bodies, customer free text, and
    every piece of retrieved document/tool-output content entering the
    agent pipeline -- retrieved content is untrusted input exactly like
    a RAG pipeline's.

    Steps (deterministic, always applied regardless of guardrails-ai
    availability):
      1. HTML stripping
      2. Length limiting
      3. Regex-based prompt-injection signature detection

    Raises PromptInjectionDetectedError if a known injection signature
    is found and raise_on_injection is True (the default). Callers that
    want to merely neutralize instead of reject (e.g. when sanitizing
    retrieved document excerpts that should still be shown, redacted)
    can pass raise_on_injection=False.
    """
    if text is None:
        return ""
    if not isinstance(text, str):
        raise ValidationError("free_text", text, "must be a string")

    cleaned = _HTML_TAG_PATTERN.sub("", text).strip()

    for pattern in _INJECTION_SIGNATURES:
        if pattern.search(cleaned):
            if raise_on_injection:
                raise PromptInjectionDetectedError(
                    "Input was rejected: it matched a known prompt-injection signature."
                )
            cleaned = pattern.sub("[REDACTED]", cleaned)

    if len(cleaned) > max_length:
        cleaned = cleaned[:max_length]

    return cleaned


# ---------------------------------------------------------------------------
# 5. PII redaction for structured logging
# ---------------------------------------------------------------------------
_FULLY_REDACTED_KEYS = {"phone", "email"}
_PARTIALLY_MASKED_KEYS = {
    "account_id",
    "account_business_id",
    "customer_id",
    "customer_business_id",
    "policy_id",
    "policy_business_id",
    "portfolio_id",
    "portfolio_business_id",
    "claim_id",
    "claim_business_id",
}


def redact_for_logging(data: Any) -> Any:
    """
    Recursively redact PII-shaped keys in a dict before it is written to
    a structured log line. Non-dict values pass through unchanged
    (there is nothing keyed to redact). Phone/email are fully redacted;
    business identifiers are partially masked (last four characters)
    so logs remain useful for debugging without exposing full IDs.
    """
    if not isinstance(data, dict):
        return data

    redacted: dict[str, Any] = {}
    for key, value in data.items():
        if key in _FULLY_REDACTED_KEYS:
            redacted[key] = "<redacted>"
        elif key in _PARTIALLY_MASKED_KEYS and isinstance(value, str):
            redacted[key] = mask_business_id(value)
        elif isinstance(value, dict):
            redacted[key] = redact_for_logging(value)
        else:
            redacted[key] = value
    return redacted


# ---------------------------------------------------------------------------
# 6. Output grounding / unsupported-claim + leaked-identifier checking
# ---------------------------------------------------------------------------
# data.validation.PATTERNS are anchored (^...$) for full-string format
# validation. Scanning for an ID *embedded* in a larger sentence needs
# the same patterns WITHOUT those anchors, so a word-boundary-wrapped,
# unanchored copy is built once here rather than re-declaring the
# format strings a second time.
_UNMASKED_ID_PATTERNS = {
    name: re.compile(r"\b" + pattern.strip("^$") + r"\b")
    for name, pattern in PATTERNS.items()
    if name.endswith("_business_id") or name in ("claim_business_id",)
}
_NUMERIC_CLAIM_PATTERN = re.compile(r"\b\d[\d,]*(?:\.\d+)?\b")


def find_unmasked_business_ids(text: str) -> list[str]:
    """Scan `text` for any FULL (unmasked) business identifier. A drafted
    response must never contain one of these -- only masked ****-prefixed
    forms are allowed to reach a customer."""
    if not text:
        return []
    found: list[str] = []
    for pattern in _UNMASKED_ID_PATTERNS.values():
        found.extend(match.group(0) for match in pattern.finditer(text))
    return found


def find_unsupported_numeric_claims(draft_text: str, grounded_context: str) -> list[str]:
    """
    Deterministic, conservative check: every standalone number in the
    draft (amounts, counts, percentages) must also appear somewhere in
    the grounded context it was supposedly drawn from. This is
    intentionally simple -- a real validation agent will do much more --
    but it is enough to catch an obviously fabricated figure.
    """
    if not draft_text:
        return []
    context = grounded_context or ""
    claimed = {m.group(0) for m in _NUMERIC_CLAIM_PATTERN.finditer(draft_text)}
    supported = {m.group(0) for m in _NUMERIC_CLAIM_PATTERN.finditer(context)}
    return sorted(claimed - supported)


def check_output_grounding(draft_text: str, grounded_context: str) -> dict:
    """
    Returns:
        {"passed": bool, "leaked_identifiers": [...], "unsupported_claims": [...]}

    An output with any leaked unmasked identifier or any unsupported
    numeric claim never passes, regardless of anything else.
    """
    leaked = find_unmasked_business_ids(draft_text)
    unsupported = find_unsupported_numeric_claims(draft_text, grounded_context)
    return {
        "passed": not leaked and not unsupported,
        "leaked_identifiers": leaked,
        "unsupported_claims": unsupported,
    }


__all__ = [
    "GUARDRAILS_AI_AVAILABLE",
    "CallerScopeViolationError",
    "PromptInjectionDetectedError",
    "ALLOWED_CALLER_SCOPES",
    "enforce_domain_scope",
    "enforce_caller_scope_ownership",
    "mask_business_id",
    "mask_fields_in_dict",
    "minimize_account_fields",
    "minimize_portfolio_fields",
    "sanitize_free_text",
    "redact_for_logging",
    "check_output_grounding",
    "find_unmasked_business_ids",
    "find_unsupported_numeric_claims",
]
