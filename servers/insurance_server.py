"""
Insurance MCP server.

Owns exactly: policies, claims. Imports ONLY Insurance repositories.

Run standalone:
    python -m servers.insurance_server
"""
from __future__ import annotations

import os

from fastmcp import FastMCP

from common.errors import InternalServiceError, ResourceNotFoundError
from common.guardrails import (
    enforce_domain_scope,
    mask_business_id,
    mask_fields_in_dict,
    redact_for_logging,
)
from common.logging_config import get_logger, trace
from common.validate import validate_business_id, validate_scenario_tag
from data.database.session import create_domain_database_access
from data.repositories.errors import DatabaseOperationError, RecordNotFoundError
from data.repositories.insurance.claim_repository import ClaimRepository
from data.repositories.insurance.policy_repository import PolicyRepository

logger = get_logger("insurance_server")
mcp = FastMCP("insurance_server")

_session = create_domain_database_access(server="insurance_server")
_policy_repo = PolicyRepository(_session)
_claim_repo = ClaimRepository(_session)

HOST = os.environ.get("INSURANCE_SERVER_HOST", "127.0.0.1")
PORT = int(os.environ.get("INSURANCE_SERVER_PORT", "8002"))

# None of these three tools carry caller_scope in the spec's literal tool
# signatures, so it is an OPTIONAL parameter here: omitting it preserves
# the exact spec call pattern (e.g. get_policy_details(policy_id)). When a
# caller does supply it, it is still validated against this domain's
# allowed scopes, which is what tests/test_caller_scope.py exercises for
# the Policy Manager role.
INSURANCE_ALLOWED_SCOPES = {"user", "policy_manager"}


# ---------------------------------------------------------------------------
# Deterministic coverage-clause evaluation (no LLM involved)
# ---------------------------------------------------------------------------
def _clause_auto_debit(policy) -> bool:
    return bool(policy.auto_debit_supported) and policy.status == "ACTIVE"


def _clause_manual_payment(policy) -> bool:
    return policy.status != "LAPSED"


def _clause_premium_grace_period(policy) -> bool:
    return policy.status != "LAPSED"


_COVERAGE_CLAUSE_EVALUATORS = {
    "auto_debit": _clause_auto_debit,
    "manual_payment": _clause_manual_payment,
    "premium_grace_period": _clause_premium_grace_period,
}


# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------
@mcp.tool()
@trace(logger, redact=redact_for_logging)
def get_policy_details(policy_id: str, caller_scope: str | None = None) -> dict:
    """Single policy lookup: premiums, payment terms, status. Policy number masked."""
    policy_id = validate_business_id("policy_business_id", policy_id)
    if caller_scope is not None:
        enforce_domain_scope(caller_scope, INSURANCE_ALLOWED_SCOPES)
    try:
        policy = _policy_repo.read_by_id(policy_id)
    except RecordNotFoundError as exc:
        raise ResourceNotFoundError("Policy", policy_id) from exc
    except DatabaseOperationError as exc:
        raise InternalServiceError() from exc

    return {
        "policy_id": mask_business_id(policy.policy_id),
        "policy_type": policy.policy_type,
        "status": policy.status,
        "premium_amount": float(policy.premium_amount),
        "premium_frequency": policy.premium_frequency,
        "auto_debit_supported": policy.auto_debit_supported,
        "payment_method": policy.payment_method,
        "start_date": policy.start_date.isoformat(),
        "end_date": policy.end_date.isoformat() if policy.end_date else None,
    }


@mcp.tool()
@trace(logger, redact=redact_for_logging)
def check_coverage_clause(policy_id: str, scenario_tag: str, caller_scope: str | None = None) -> dict:
    """
    Deterministic check of whether `scenario_tag` is covered under this
    policy's clauses. No LLM is used for the coverage decision itself --
    see _COVERAGE_CLAUSE_EVALUATORS above.
    """
    policy_id = validate_business_id("policy_business_id", policy_id)
    scenario_tag = validate_scenario_tag(scenario_tag)
    if caller_scope is not None:
        enforce_domain_scope(caller_scope, INSURANCE_ALLOWED_SCOPES)

    try:
        policy = _policy_repo.read_by_id(policy_id)
    except RecordNotFoundError as exc:
        raise ResourceNotFoundError("Policy", policy_id) from exc
    except DatabaseOperationError as exc:
        raise InternalServiceError() from exc

    evaluator = _COVERAGE_CLAUSE_EVALUATORS.get(scenario_tag)
    if evaluator is None:
        return {
            "policy_id": mask_business_id(policy.policy_id),
            "scenario_tag": scenario_tag,
            "covered": False,
            "reason": "no_explicit_clause_for_scenario_tag",
        }

    covered = evaluator(policy)
    return {
        "policy_id": mask_business_id(policy.policy_id),
        "scenario_tag": scenario_tag,
        "covered": covered,
        "reason": "evaluated_against_structured_policy_record",
    }


@mcp.tool()
@trace(logger, redact=redact_for_logging)
def get_claim_status(claim_id: str, caller_scope: str | None = None) -> dict:
    """
    Claim status lookup only -- carries no settlement authority. Claim
    and policy identifiers in the response are masked.
    """
    claim_id = validate_business_id("claim_business_id", claim_id)
    if caller_scope is not None:
        enforce_domain_scope(caller_scope, INSURANCE_ALLOWED_SCOPES)
    try:
        claim = _claim_repo.read_by_id(claim_id)
    except RecordNotFoundError as exc:
        raise ResourceNotFoundError("Claim", claim_id) from exc
    except DatabaseOperationError as exc:
        raise InternalServiceError() from exc

    return {
        "claim_id": mask_business_id(claim.claim_id),
        "claim_type": claim.claim_type,
        "status": claim.status,
        "filed_at": claim.filed_at.isoformat(),
        "settlement_authority": False,
    }


# ---------------------------------------------------------------------------
# Resource
# ---------------------------------------------------------------------------
@mcp.resource("policy://{policy_id}/summary")
@trace(logger, redact=redact_for_logging)
def policy_summary_resource(policy_id: str) -> dict:
    """Templated Resource returning a single policy's non-bulk summary, masked."""
    policy_id = validate_business_id("policy_business_id", policy_id)
    try:
        policy = _policy_repo.read_by_id(policy_id)
    except RecordNotFoundError as exc:
        raise ResourceNotFoundError("Policy", policy_id) from exc
    except DatabaseOperationError as exc:
        raise InternalServiceError() from exc

    return mask_fields_in_dict(
        {
            "policy_id": policy.policy_id,
            "policy_type": policy.policy_type,
            "status": policy.status,
            "premium_frequency": policy.premium_frequency,
            "auto_debit_supported": policy.auto_debit_supported,
        },
        ("policy_id",),
    )


if __name__ == "__main__":
    mcp.run(transport="http", host=HOST, port=PORT)
