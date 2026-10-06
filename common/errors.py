"""
Typed, client-safe errors for the MCP server layer.

Per spec §16: MCP tools/resources/prompts must never leak raw database
tracebacks, SQLAlchemy internals, file paths, or secrets to a caller.
Server files catch the Data module's repository errors
(RecordNotFoundError, DatabaseOperationError, ...) and translate them into
one of these clean, client-facing types using `raise ... from exc` so the
full original traceback is still captured by the structured FAILED trace
log (see common/logging_config.py), without ever being returned to the
MCP client itself.
"""
from __future__ import annotations


class MCPToolError(Exception):
    """Base class for every error an MCP tool/resource deliberately raises."""


class ResourceNotFoundError(MCPToolError):
    def __init__(self, kind: str, identifier: str):
        self.kind = kind
        self.identifier = identifier
        super().__init__(f"{kind} '{identifier}' was not found.")


class PermissionDeniedError(MCPToolError):
    """Raised for caller-scope violations, ownership violations, and
    detected prompt-injection attempts -- anything that is a deliberate
    refusal rather than an unexpected failure."""


class InternalServiceError(MCPToolError):
    """
    Raised in place of an unexpected underlying error (e.g. a database
    connectivity problem) so the MCP client only ever sees a generic,
    safe message. The original exception is always attached via
    `raise InternalServiceError(...) from original_exc`, which keeps it
    in the full traceback captured by the FAILED trace log server-side.
    """

    def __init__(self, message: str = "An internal error occurred while processing this request."):
        super().__init__(message)
