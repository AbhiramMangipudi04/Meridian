"""
Banking MCP server.

Owns exactly: accounts, transactions. Imports ONLY Banking repositories
-- never Insurance/Wealth/Concierge repositories -- so accidental
cross-domain access is a straightforward import-time fact, not just a
runtime check. The session this server constructs is also structurally
restricted (see data/database/session.py): even a typo'd attempt to read
another domain's table would be rejected by the Data module itself.

Run standalone:
    python -m servers.banking_server
"""
from __future__ import annotations

import os

from fastmcp import FastMCP

from common.errors import InternalServiceError, ResourceNotFoundError
from common.guardrails import (
    enforce_caller_scope_ownership,
    enforce_domain_scope,
    mask_fields_in_dict,
    minimize_account_fields,
    redact_for_logging,
)
from common.logging_config import get_logger, trace
from common.validate import validate_business_id, validate_caller_scope, validate_limit
from data.database.session import create_domain_database_access
from data.repositories.banking.account_repository import AccountRepository
from data.repositories.banking.transaction_repository import TransactionRepository
from data.repositories.errors import DatabaseOperationError, RecordNotFoundError

logger = get_logger("banking_server")
mcp = FastMCP("banking_server")

# This server's ONE domain-restricted session. banking_server can only
# ever reach `accounts` and `transactions` through it -- enforced by the
# Data module's access-control layer, not by convention.
_session = create_domain_database_access(server="banking_server")
_account_repo = AccountRepository(_session)
_transaction_repo = TransactionRepository(_session)

# Caller scopes permitted to reach the banking domain at all. Policy/
# wealth managers and operations are rejected before any repository call.
BANKING_ALLOWED_SCOPES = {"user", "bank_manager"}

HOST = os.environ.get("BANKING_SERVER_HOST", "127.0.0.1")
PORT = int(os.environ.get("BANKING_SERVER_PORT", "8001"))


# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------
@mcp.tool()
@trace(logger, redact=redact_for_logging)
def get_account_summary(account_id: str, caller_scope: str, caller_customer_id: str | None = None) -> dict:
    """
    Look up a single account, with fields minimized according to
    caller_scope and the account number masked to its last four digits.

    caller_customer_id is required when caller_scope == "user": a user
    may only ever see their own account, never another customer's.
    """
    account_id = validate_business_id("account_business_id", account_id)
    caller_scope = validate_caller_scope(caller_scope)
    enforce_domain_scope(caller_scope, BANKING_ALLOWED_SCOPES)

    try:
        account = _account_repo.read_by_id(account_id)
    except RecordNotFoundError as exc:
        raise ResourceNotFoundError("Account", account_id) from exc
    except DatabaseOperationError as exc:
        raise InternalServiceError() from exc

    enforce_caller_scope_ownership(caller_scope, caller_customer_id, account.customer_business_id)

    minimized = minimize_account_fields(account, caller_scope)
    return mask_fields_in_dict(minimized, ("account_id",))


@mcp.tool()
@trace(logger, redact=redact_for_logging)
def get_transaction_history(account_id: str, limit: int = 20) -> dict:
    """
    Recent transactions for one account, most recent first. The account
    number in the response is masked; transaction IDs are returned
    as-is (they are not customer-identifying cross-domain business IDs).
    """
    account_id = validate_business_id("account_business_id", account_id)
    limit = validate_limit(limit, minimum=1, maximum=100)

    try:
        account = _account_repo.read_by_id(account_id)
    except RecordNotFoundError as exc:
        raise ResourceNotFoundError("Account", account_id) from exc
    except DatabaseOperationError as exc:
        raise InternalServiceError() from exc

    try:
        transactions = _transaction_repo.read_by_account(account.id, limit=limit)
    except DatabaseOperationError as exc:
        raise InternalServiceError() from exc

    return {
        "account_id": "****" + account_id[-4:],
        "transactions": [
            {
                "transaction_id": txn.transaction_id,
                "amount": float(txn.amount),
                "currency": txn.currency,
                "transaction_type": txn.transaction_type,
                "description": txn.description,
                "status": txn.status,
                "timestamp": txn.timestamp.isoformat(),
            }
            for txn in transactions
        ],
    }


@mcp.tool()
@trace(logger, redact=redact_for_logging)
def get_linked_accounts(customer_id: str, caller_scope: str = "user", caller_customer_id: str | None = None) -> dict:
    """
    All accounts linked to a customer, with the same caller-scope field
    minimization and account-number masking used by get_account_summary.
    """
    customer_id = validate_business_id("customer_business_id", customer_id)
    caller_scope = validate_caller_scope(caller_scope)
    enforce_domain_scope(caller_scope, BANKING_ALLOWED_SCOPES)
    enforce_caller_scope_ownership(caller_scope, caller_customer_id, customer_id)

    try:
        accounts = _account_repo.read_by_customer(customer_id)
    except DatabaseOperationError as exc:
        raise InternalServiceError() from exc

    results = []
    for account in accounts:
        minimized = minimize_account_fields(account, caller_scope)
        results.append(mask_fields_in_dict(minimized, ("account_id",)))
    return {"customer_id": "****" + customer_id[-4:], "accounts": results}


# ---------------------------------------------------------------------------
# Resource
# ---------------------------------------------------------------------------
@mcp.resource("account://{account_id}/summary")
@trace(logger, redact=redact_for_logging)
def account_summary_resource(account_id: str) -> dict:
    """
    Templated Resource returning a single account's non-bulk summary,
    with the account number masked. No caller_scope is available on a
    plain Resource fetch, so this always returns the most restrictive
    ("user"-level) field set -- a manager-level Resource read is not
    offered; managers use get_account_summary with their scope instead.
    """
    account_id = validate_business_id("account_business_id", account_id)
    try:
        account = _account_repo.read_by_id(account_id)
    except RecordNotFoundError as exc:
        raise ResourceNotFoundError("Account", account_id) from exc
    except DatabaseOperationError as exc:
        raise InternalServiceError() from exc

    minimized = minimize_account_fields(account, "user")
    return mask_fields_in_dict(minimized, ("account_id",))


if __name__ == "__main__":
    mcp.run(transport="http", host=HOST, port=PORT)
