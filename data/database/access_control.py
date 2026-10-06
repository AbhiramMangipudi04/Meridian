"""
Central, single-source-of-truth mapping of which server may access which
tables. Every other place in the codebase (session.py's enforcement
listeners, repositories, tests, and -- later -- the MCP servers
themselves) must import this instead of re-declaring the matrix.
"""
from __future__ import annotations

SERVER_TABLE_ACCESS: dict[str, frozenset[str]] = {
    "banking_server": frozenset({"accounts", "transactions"}),
    "insurance_server": frozenset({"policies", "claims"}),
    "wealth_server": frozenset({"portfolios", "investment_products"}),
    "concierge_ops_server": frozenset(
        {"customers", "interaction_log", "escalation_flags", "audit_log"}
    ),
}

# Reverse index: table name -> owning server. Useful for error messages and
# for the DOMAIN_OWNERSHIP export consumed by docs/tests.
TABLE_OWNER: dict[str, str] = {
    table: server for server, tables in SERVER_TABLE_ACCESS.items() for table in tables
}

ALL_KNOWN_SERVERS = tuple(SERVER_TABLE_ACCESS.keys())
ALL_KNOWN_TABLES = frozenset(TABLE_OWNER.keys())


class UnauthorizedTableAccessError(PermissionError):
    """
    Raised when a domain-restricted database session attempts to read or
    write a table outside its server's allowlist.

    This is the enforcement mechanism required by the project brief: it is
    raised from live SQLAlchemy event hooks (see session.py), not merely
    documented as a rule developers are expected to follow.
    """

    def __init__(self, server: str, table: str):
        self.server = server
        self.table = table
        allowed = sorted(SERVER_TABLE_ACCESS.get(server, frozenset()))
        super().__init__(
            f"Server '{server}' attempted to access table '{table}', which it "
            f"is not authorized to reach. '{server}' may only access: {allowed}."
        )
