"""
Generic CRUD repository base class.

Repositories encapsulate database operations only: no LLM logic, no MCP
logic, no business orchestration, and no direct access to another
domain's repository or model. Every repository is constructed with a
domain-restricted Session (see data/database/session.py), which is what
makes cross-domain access structurally impossible rather than merely
discouraged.
"""
from __future__ import annotations

from typing import Generic, TypeVar

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from data.repositories.errors import (
    DatabaseOperationError,
    DuplicateBusinessIdError,
    InvalidIdentifierError,
    InvalidUpdateError,
    RecordNotFoundError,
)
from data.validation import InvalidBusinessIdentifierError

ModelT = TypeVar("ModelT")


class BaseRepository(Generic[ModelT]):
    #: SQLAlchemy model class this repository manages. Set by subclasses.
    model: type = None  # type: ignore[assignment]
    #: Name of the model's unique business-identifier attribute, e.g.
    #: "account_id", "policy_id", "customer_business_id". Set by subclasses.
    business_id_field: str = ""

    def __init__(self, session: Session):
        if self.model is None or not self.business_id_field:
            raise NotImplementedError("Subclasses must set `model` and `business_id_field`.")
        self.session = session

    # ------------------------------------------------------------------
    # create
    # ------------------------------------------------------------------
    def create(self, **fields) -> ModelT:
        try:
            instance = self.model(**fields)
        except InvalidBusinessIdentifierError as exc:
            raise InvalidIdentifierError(exc.field_name, exc.value) from exc

        self.session.add(instance)
        try:
            self.session.commit()
        except IntegrityError as exc:
            self.session.rollback()
            raise DuplicateBusinessIdError(
                self.model.__name__, self.business_id_field, fields.get(self.business_id_field)
            ) from exc
        except SQLAlchemyError as exc:
            self.session.rollback()
            raise DatabaseOperationError(str(exc)) from exc
        return instance

    # ------------------------------------------------------------------
    # read
    # ------------------------------------------------------------------
    def read_all(self, limit: int | None = None, offset: int = 0) -> list[ModelT]:
        try:
            stmt = select(self.model).offset(offset)
            if limit is not None:
                stmt = stmt.limit(limit)
            return list(self.session.execute(stmt).scalars().all())
        except SQLAlchemyError as exc:
            raise DatabaseOperationError(str(exc)) from exc

    def read_by_id(self, business_id: str) -> ModelT:
        try:
            stmt = select(self.model).where(
                getattr(self.model, self.business_id_field) == business_id
            )
            result = self.session.execute(stmt).scalars().first()
        except SQLAlchemyError as exc:
            raise DatabaseOperationError(str(exc)) from exc
        if result is None:
            raise RecordNotFoundError(self.model.__name__, self.business_id_field, business_id)
        return result

    # ------------------------------------------------------------------
    # update
    # ------------------------------------------------------------------
    def update(self, business_id: str, **fields) -> ModelT:
        instance = self.read_by_id(business_id)  # raises RecordNotFoundError if missing

        if not fields:
            raise InvalidUpdateError(self.model.__name__, "update() called with no fields to change")

        if self.business_id_field in fields and fields[self.business_id_field] != business_id:
            raise InvalidUpdateError(
                self.model.__name__,
                f"business identifier field '{self.business_id_field}' cannot be reassigned via update()",
            )

        for key, value in fields.items():
            if not hasattr(instance, key):
                raise InvalidUpdateError(self.model.__name__, f"unknown field '{key}'")
            setattr(instance, key, value)

        try:
            self.session.commit()
        except SQLAlchemyError as exc:
            self.session.rollback()
            raise DatabaseOperationError(str(exc)) from exc
        return instance
