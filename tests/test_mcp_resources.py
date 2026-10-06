"""
Tests for the 4 required MCP Resources:
    customer://{customer_id}/profile
    account://{account_id}/summary
    policy://{policy_id}/summary
    knowledgebase://{document_id}/excerpt

As with tools, the decorated resource functions remain plain, directly
callable Python functions, so these are fast unit tests against real
repository-backed data (the real FastMCP *registration* of these URIs is
covered in test_fastmcp_registration.py).
"""
from __future__ import annotations

import json

import pytest

fastmcp = pytest.importorskip("fastmcp")

from common.errors import ResourceNotFoundError
from data.seed.ids import SHOWCASE_ACCOUNT_ID, SHOWCASE_CUSTOMER_ID, SHOWCASE_POLICY_ID


def test_customer_profile_resource():
    from servers import concierge_ops_server

    result = concierge_ops_server.customer_profile_resource(SHOWCASE_CUSTOMER_ID)
    assert result["customer_id"] == "****0077"
    assert result["full_name"] == "Arjun Mehta"
    # no bulk data: exactly the summary fields, not the whole customer row
    assert set(result.keys()) == {"customer_id", "full_name", "customer_tier"}


def test_customer_profile_resource_not_found():
    from servers import concierge_ops_server

    with pytest.raises(ResourceNotFoundError):
        concierge_ops_server.customer_profile_resource("CUS-99999")


def test_account_summary_resource_masks_account_number():
    from servers import banking_server

    result = banking_server.account_summary_resource(SHOWCASE_ACCOUNT_ID)
    assert result["account_id"] == "****0077"
    assert "customer_business_id" not in result  # user-level field set, no bulk data


def test_policy_summary_resource_masks_policy_number():
    from servers import insurance_server

    result = insurance_server.policy_summary_resource(SHOWCASE_POLICY_ID)
    assert result["policy_id"] == "****0091"
    assert result["auto_debit_supported"] is True


def test_knowledgebase_excerpt_resource_returns_single_document_excerpt():
    from servers import concierge_ops_server

    result = concierge_ops_server.knowledgebase_excerpt_resource("premium_auto_debit_policy")
    assert result["document_id"] == "premium_auto_debit_policy"
    assert "excerpt" in result and len(result["excerpt"]) > 0
    assert result["metadata"].get("retrieval_conflict_fixture") == "true"
    # single document, not the whole knowledge-base collection
    assert "excerpt" in result and isinstance(result["excerpt"], str)


def test_knowledgebase_excerpt_resource_not_found():
    from servers import concierge_ops_server

    with pytest.raises(ResourceNotFoundError):
        concierge_ops_server.knowledgebase_excerpt_resource("does_not_exist_anywhere")


def test_resources_produce_structured_trace_output(capfd):
    """
    Uses capfd (file-descriptor level) rather than capsys: the trace
    logger's StreamHandler is constructed once, the first time any test
    in the session imports a server module, and binds to whatever
    sys.stdout *object* was active at that moment. capsys only
    intercepts the current sys.stdout object, which pytest swaps per
    test, so a handler created in an earlier test's capture context
    would be invisible to a later test's capsys. capfd intercepts the
    real OS file descriptor instead, which is unaffected by that.
    """
    from servers import banking_server

    banking_server.account_summary_resource(SHOWCASE_ACCOUNT_ID)
    captured = capfd.readouterr().out.strip().splitlines()
    assert len(captured) >= 2  # ENTER + EXIT at minimum

    events = [json.loads(line)["event"] for line in captured if line.strip()]
    assert "ENTER" in events
    assert "EXIT" in events
