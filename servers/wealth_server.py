"""
Wealth MCP server.

Owns exactly: portfolios, investment_products. Imports ONLY Wealth
repositories. No Resource is assigned to this server -- the 4 required
Resources map to customer/account/policy/knowledgebase, none of which
belong to the wealth domain.

Run standalone:
    python -m servers.wealth_server
"""
from __future__ import annotations

import os

from fastmcp import FastMCP

from common.errors import InternalServiceError, ResourceNotFoundError
from common.guardrails import (
    enforce_caller_scope_ownership,
    enforce_domain_scope,
    mask_fields_in_dict,
    minimize_portfolio_fields,
    redact_for_logging,
)
from common.logging_config import get_logger, trace
from common.validate import validate_business_id, validate_caller_scope, validate_risk_profile
from data.database.session import create_domain_database_access
from data.repositories.errors import DatabaseOperationError, RecordNotFoundError
from data.repositories.wealth.investment_product_repository import InvestmentProductRepository
from data.repositories.wealth.portfolio_repository import PortfolioRepository

logger = get_logger("wealth_server")
mcp = FastMCP("wealth_server")

_session = create_domain_database_access(server="wealth_server")
_portfolio_repo = PortfolioRepository(_session)
_product_repo = InvestmentProductRepository(_session)

WEALTH_ALLOWED_SCOPES = {"user", "wealth_manager"}

HOST = os.environ.get("WEALTH_SERVER_HOST", "127.0.0.1")
PORT = int(os.environ.get("WEALTH_SERVER_PORT", "8003"))

# Deterministic suitability rule: a product is suitable for a risk
# profile if the product's own risk rating is AT MOST as aggressive as
# the customer's stated tolerance.
_RISK_TOLERANCE_ORDER = ("CONSERVATIVE", "MODERATE", "AGGRESSIVE")


def _is_suitable(product_risk_rating: str, customer_risk_profile: str) -> bool:
    try:
        product_rank = _RISK_TOLERANCE_ORDER.index(product_risk_rating)
        customer_rank = _RISK_TOLERANCE_ORDER.index(customer_risk_profile)
    except ValueError:
        return False
    return product_rank <= customer_rank


# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------
@mcp.tool()
@trace(logger, redact=redact_for_logging)
def get_portfolio_summary(portfolio_id: str, caller_scope: str, caller_customer_id: str | None = None) -> dict:
    """Portfolio lookup, fields minimized per caller_scope, portfolio number masked."""
    portfolio_id = validate_business_id("portfolio_business_id", portfolio_id)
    caller_scope = validate_caller_scope(caller_scope)
    enforce_domain_scope(caller_scope, WEALTH_ALLOWED_SCOPES)

    try:
        portfolio = _portfolio_repo.read_by_id(portfolio_id)
    except RecordNotFoundError as exc:
        raise ResourceNotFoundError("Portfolio", portfolio_id) from exc
    except DatabaseOperationError as exc:
        raise InternalServiceError() from exc

    enforce_caller_scope_ownership(caller_scope, caller_customer_id, portfolio.customer_business_id)

    minimized = minimize_portfolio_fields(portfolio, caller_scope)
    return mask_fields_in_dict(minimized, ("portfolio_id",))


@mcp.tool()
@trace(logger, redact=redact_for_logging)
def get_investment_product_details(product_id: str, caller_scope: str | None = None) -> dict:
    """Single investment product lookup. Products are a catalog, not customer data, so no masking applies."""
    product_id = validate_business_id("product_business_id", product_id)
    if caller_scope is not None:
        enforce_domain_scope(caller_scope, WEALTH_ALLOWED_SCOPES)
    try:
        product = _product_repo.read_by_id(product_id)
    except RecordNotFoundError as exc:
        raise ResourceNotFoundError("InvestmentProduct", product_id) from exc
    except DatabaseOperationError as exc:
        raise InternalServiceError() from exc

    return {
        "product_id": product.product_id,
        "name": product.name,
        "category": product.category,
        "risk_rating": product.risk_rating,
        "min_investment": float(product.min_investment),
        "description": product.description,
    }


@mcp.tool()
@trace(logger, redact=redact_for_logging)
def check_product_suitability(product_id: str, risk_profile: str, caller_scope: str | None = None) -> dict:
    """
    Suitability check only: no write, no customer data beyond the
    supplied risk profile, no access to accounts or policies.
    """
    product_id = validate_business_id("product_business_id", product_id)
    risk_profile = validate_risk_profile(risk_profile)
    if caller_scope is not None:
        enforce_domain_scope(caller_scope, WEALTH_ALLOWED_SCOPES)

    try:
        product = _product_repo.read_by_id(product_id)
    except RecordNotFoundError as exc:
        raise ResourceNotFoundError("InvestmentProduct", product_id) from exc
    except DatabaseOperationError as exc:
        raise InternalServiceError() from exc

    suitable = _is_suitable(product.risk_rating, risk_profile)
    return {
        "product_id": product.product_id,
        "risk_profile": risk_profile,
        "product_risk_rating": product.risk_rating,
        "suitable": suitable,
    }


if __name__ == "__main__":
    mcp.run(transport="http", host=HOST, port=PORT)
