"""
Verifies the actual FastMCP registrations for all four servers -- the
real `fastmcp.FastMCP` instance, not a fake/mocked MCP server standing in
for it (spec §25).

Uses `fastmcp.Client` for in-memory introspection (the documented FastMCP
testing pattern: `Client(mcp_instance)` talks to the server object
directly, no network/HTTP transport needed for this check -- HTTP
transport itself is what `mcp.run(transport="http", ...)` provides at
runtime, exercised by actually starting a server process, not by this
test file).

NOTE: FastMCP's exact Client/introspection method names can differ
slightly between versions. Per the spec ("The exact FastMCP API syntax
should follow the installed fastmcp version in the environment"), if the
installed version exposes these under different method names, adjust the
calls in `_list_tool_names` / `_list_resource_uris` / `_list_prompt_names`
below -- the assertions themselves (which names must be present) are the
part that encodes the actual requirement.
"""
from __future__ import annotations

import asyncio

import pytest

fastmcp = pytest.importorskip("fastmcp")
from fastmcp import Client  # noqa: E402


def _run(coro):
    return asyncio.run(coro)


def _list_tool_names(mcp_instance) -> set[str]:
    async def _inner():
        async with Client(mcp_instance) as client:
            tools = await client.list_tools()
            return {t.name for t in tools}

    return _run(_inner())


def _list_resource_uris(mcp_instance) -> set[str]:
    async def _inner():
        async with Client(mcp_instance) as client:
            uris = set()
            try:
                resources = await client.list_resources()
                uris |= {str(r.uri) for r in resources}
            except Exception:
                pass
            try:
                templates = await client.list_resource_templates()
                uris |= {str(t.uriTemplate) for t in templates}
            except Exception:
                pass
            return uris

    return _run(_inner())


def _list_prompt_names(mcp_instance) -> set[str]:
    async def _inner():
        async with Client(mcp_instance) as client:
            prompts = await client.list_prompts()
            return {p.name for p in prompts}

    return _run(_inner())


# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------
def test_banking_server_registers_its_three_tools():
    from servers import banking_server

    names = _list_tool_names(banking_server.mcp)
    assert {"get_account_summary", "get_transaction_history", "get_linked_accounts"} <= names


def test_insurance_server_registers_its_three_tools():
    from servers import insurance_server

    names = _list_tool_names(insurance_server.mcp)
    assert {"get_policy_details", "check_coverage_clause", "get_claim_status"} <= names


def test_wealth_server_registers_its_three_tools():
    from servers import wealth_server

    names = _list_tool_names(wealth_server.mcp)
    assert {
        "get_portfolio_summary",
        "get_investment_product_details",
        "check_product_suitability",
    } <= names


def test_concierge_server_registers_its_four_tools():
    from servers import concierge_ops_server

    names = _list_tool_names(concierge_ops_server.mcp)
    assert {
        "get_customer_kyc_status",
        "run_escalation_check",
        "send_customer_notification",
        "write_audit_log",
    } <= names


def test_thirteen_tools_total_across_all_four_servers():
    from servers import banking_server, concierge_ops_server, insurance_server, wealth_server

    total = (
        len(_list_tool_names(banking_server.mcp))
        + len(_list_tool_names(insurance_server.mcp))
        + len(_list_tool_names(wealth_server.mcp))
        + len(_list_tool_names(concierge_ops_server.mcp))
    )
    assert total == 13


# ---------------------------------------------------------------------------
# Resources (templated URIs)
# ---------------------------------------------------------------------------
def test_banking_server_registers_account_resource():
    from servers import banking_server

    uris = _list_resource_uris(banking_server.mcp)
    assert any("account://" in uri for uri in uris)


def test_insurance_server_registers_policy_resource():
    from servers import insurance_server

    uris = _list_resource_uris(insurance_server.mcp)
    assert any("policy://" in uri for uri in uris)


def test_concierge_server_registers_customer_and_knowledgebase_resources():
    from servers import concierge_ops_server

    uris = _list_resource_uris(concierge_ops_server.mcp)
    assert any("customer://" in uri for uri in uris)
    assert any("knowledgebase://" in uri for uri in uris)


def test_four_resources_total_across_all_servers():
    from servers import banking_server, concierge_ops_server, insurance_server, wealth_server

    total = (
        len(_list_resource_uris(banking_server.mcp))
        + len(_list_resource_uris(insurance_server.mcp))
        + len(_list_resource_uris(wealth_server.mcp))
        + len(_list_resource_uris(concierge_ops_server.mcp))
    )
    assert total == 4


# ---------------------------------------------------------------------------
# Prompts
# ---------------------------------------------------------------------------
def test_concierge_server_registers_both_prompts():
    from servers import concierge_ops_server

    names = _list_prompt_names(concierge_ops_server.mcp)
    assert {"request_classification_prompt", "response_drafting_prompt"} <= names
