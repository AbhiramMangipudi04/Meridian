"""
Caller-scope tests, organized by role, per the capstone spec §4/§19.

Every test calls the real server tool functions directly (see
test_mcp_tools.py's module docstring for why this is valid without a
running HTTP server).
"""
from __future__ import annotations

import pytest

fastmcp = pytest.importorskip("fastmcp")

from common.guardrails import CallerScopeViolationError
from common.validate import ALLOWED_CALLER_SCOPES, ValidationError, validate_caller_scope
from data.seed.ids import SHOWCASE_ACCOUNT_ID, SHOWCASE_CUSTOMER_ID


def test_allowed_caller_scopes_is_the_closed_five_role_set():
    assert set(ALLOWED_CALLER_SCOPES) == {
        "user",
        "bank_manager",
        "policy_manager",
        "wealth_manager",
        "operations",
    }


def test_arbitrary_caller_scope_string_rejected():
    with pytest.raises(ValidationError):
        validate_caller_scope("super_admin")


# ---------------------------------------------------------------------------
# USER
# ---------------------------------------------------------------------------
def test_user_can_access_own_account():
    from servers import banking_server

    result = banking_server.get_account_summary(
        SHOWCASE_ACCOUNT_ID, caller_scope="user", caller_customer_id=SHOWCASE_CUSTOMER_ID
    )
    assert result["account_id"] == "****0077"


def test_user_cannot_access_another_customers_account():
    from servers import banking_server

    with pytest.raises(CallerScopeViolationError):
        banking_server.get_account_summary(
            SHOWCASE_ACCOUNT_ID, caller_scope="user", caller_customer_id="CUS-20001"
        )


# ---------------------------------------------------------------------------
# BANK MANAGER
# ---------------------------------------------------------------------------
def test_bank_manager_can_access_banking_data():
    from servers import banking_server

    result = banking_server.get_account_summary(SHOWCASE_ACCOUNT_ID, caller_scope="bank_manager")
    assert result["account_id"] == "****0077"


def test_bank_manager_cannot_access_insurance_tool_scope():
    from servers import insurance_server

    with pytest.raises(CallerScopeViolationError):
        insurance_server.get_policy_details("POL-IN-30091", caller_scope="bank_manager")


def test_bank_manager_cannot_access_wealth_tool_scope():
    from servers import wealth_server

    with pytest.raises(CallerScopeViolationError):
        wealth_server.get_investment_product_details("PROD-EQ-01", caller_scope="bank_manager")


def test_operations_scope_cannot_call_banking_tool():
    from servers import banking_server

    with pytest.raises(CallerScopeViolationError):
        banking_server.get_account_summary(SHOWCASE_ACCOUNT_ID, caller_scope="operations")


# ---------------------------------------------------------------------------
# POLICY MANAGER
# ---------------------------------------------------------------------------
def test_policy_manager_can_access_insurance_data():
    from servers import insurance_server

    result = insurance_server.get_policy_details("POL-IN-30091", caller_scope="policy_manager")
    assert result["policy_id"] == "****0091"


def test_policy_manager_cannot_access_banking_tool_scope():
    from servers import banking_server

    with pytest.raises(CallerScopeViolationError):
        banking_server.get_account_summary(SHOWCASE_ACCOUNT_ID, caller_scope="policy_manager")


def test_policy_manager_cannot_access_wealth_tool_scope():
    from servers import wealth_server

    with pytest.raises(CallerScopeViolationError):
        wealth_server.get_investment_product_details("PROD-EQ-01", caller_scope="policy_manager")


# ---------------------------------------------------------------------------
# WEALTH MANAGER
# ---------------------------------------------------------------------------
def test_wealth_manager_can_access_wealth_data():
    from servers import wealth_server

    portfolio = wealth_server._portfolio_repo.read_all()[0]
    result = wealth_server.get_portfolio_summary(portfolio.portfolio_id, caller_scope="wealth_manager")
    assert result["portfolio_id"].startswith("****")


def test_wealth_manager_cannot_access_banking_tool_scope():
    from servers import banking_server

    with pytest.raises(CallerScopeViolationError):
        banking_server.get_account_summary(SHOWCASE_ACCOUNT_ID, caller_scope="wealth_manager")


def test_wealth_manager_cannot_access_insurance_tool_scope():
    from servers import insurance_server

    with pytest.raises(CallerScopeViolationError):
        insurance_server.get_policy_details("POL-IN-30091", caller_scope="wealth_manager")


# ---------------------------------------------------------------------------
# OPERATIONS
# ---------------------------------------------------------------------------
def test_operations_can_access_concierge_data():
    from servers import concierge_ops_server

    result = concierge_ops_server.get_customer_kyc_status(SHOWCASE_CUSTOMER_ID, caller_scope="operations")
    assert result["kyc_status"] == "VERIFIED"


def test_operations_cannot_access_banking_tool_scope():
    from servers import banking_server

    with pytest.raises(CallerScopeViolationError):
        banking_server.get_account_summary(SHOWCASE_ACCOUNT_ID, caller_scope="operations")


def test_operations_cannot_access_insurance_tool_scope():
    from servers import insurance_server

    with pytest.raises(CallerScopeViolationError):
        insurance_server.get_policy_details("POL-IN-30091", caller_scope="operations")


def test_operations_cannot_access_wealth_tool_scope():
    from servers import wealth_server

    with pytest.raises(CallerScopeViolationError):
        wealth_server.get_investment_product_details("PROD-EQ-01", caller_scope="operations")


def test_user_scope_rejected_on_kyc_tool():
    """'user' is not in CONCIERGE_ALLOWED_SCOPES -- KYC is Operations-only."""
    from servers import concierge_ops_server

    with pytest.raises(CallerScopeViolationError):
        concierge_ops_server.get_customer_kyc_status(SHOWCASE_CUSTOMER_ID, caller_scope="user")


# ---------------------------------------------------------------------------
# Field minimization
# ---------------------------------------------------------------------------
def test_account_field_minimization_differs_by_scope():
    from servers import banking_server

    user_view = banking_server.get_account_summary(
        SHOWCASE_ACCOUNT_ID, caller_scope="user", caller_customer_id=SHOWCASE_CUSTOMER_ID
    )
    manager_view = banking_server.get_account_summary(SHOWCASE_ACCOUNT_ID, caller_scope="bank_manager")

    assert "customer_business_id" not in user_view
    assert "opened_at" not in user_view
    assert manager_view["customer_business_id"] == SHOWCASE_CUSTOMER_ID
    assert "opened_at" in manager_view


def test_portfolio_field_minimization_differs_by_scope():
    from servers import wealth_server

    portfolio = wealth_server._portfolio_repo.read_all()[0]

    user_view = wealth_server.get_portfolio_summary(
        portfolio.portfolio_id, caller_scope="user", caller_customer_id=portfolio.customer_business_id
    )
    manager_view = wealth_server.get_portfolio_summary(portfolio.portfolio_id, caller_scope="wealth_manager")

    assert "customer_business_id" not in user_view
    assert manager_view["customer_business_id"] == portfolio.customer_business_id
