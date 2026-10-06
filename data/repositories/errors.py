"""Error types raised by the repository layer."""
from __future__ import annotations


class RepositoryError(Exception):
    """Base class for all repository-layer errors."""


class RecordNotFoundError(RepositoryError):
    def __init__(self, model_name: str, lookup: str, value):
        self.model_name = model_name
        self.lookup = lookup
        self.value = value
        super().__init__(f"{model_name} with {lookup}={value!r} was not found.")


class InvalidUpdateError(RepositoryError):
    def __init__(self, model_name: str, reason: str):
        self.model_name = model_name
        self.reason = reason
        super().__init__(f"Invalid update to {model_name}: {reason}")


class InvalidIdentifierError(RepositoryError):
    def __init__(self, field_name: str, value):
        self.field_name = field_name
        self.value = value
        super().__init__(f"Invalid identifier for '{field_name}': {value!r}")


class DuplicateBusinessIdError(RepositoryError):
    def __init__(self, model_name: str, field_name: str, value):
        self.model_name = model_name
        self.field_name = field_name
        self.value = value
        super().__init__(
            f"{model_name} with {field_name}={value!r} already exists; business "
            f"identifiers must be unique."
        )


class DatabaseOperationError(RepositoryError):
    """Wraps an unexpected underlying database/driver error so callers get
    a stable repository-layer exception type instead of a raw SQLAlchemy
    error. The original exception is always chained (`raise ... from exc`)
    rather than swallowed."""
