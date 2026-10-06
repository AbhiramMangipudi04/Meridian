"""
Account model -- owned exclusively by the BANKING domain.

Allowed same-domain FK target: transactions.account_id_fk -> accounts.id
Forbidden: any FK or ORM relationship to customers (concierge domain).
Cross-domain linkage to a customer is expressed only through the plain
string column `customer_business_id` (a business identifier, not a
relational foreign key).
"""
from __future__ import annotations

import datetime as dt

from sqlalchemy import DateTime, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from data.models.base import Base
from data.validation import validate_business_id


class Account(Base):
    __tablename__ = "accounts"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    # Business identifier, format ACC-XXXXX.
    account_id: Mapped[str] = mapped_column(String(16), unique=True, nullable=False, index=True)

    # Cross-domain business reference ONLY -- never a ForeignKey("customers.id").
    customer_business_id: Mapped[str] = mapped_column(String(16), nullable=False, index=True)

    account_type: Mapped[str] = mapped_column(String(32), nullable=False)  # e.g. SAVINGS, CURRENT
    balance: Mapped[float] = mapped_column(Numeric(14, 2), nullable=False, default=0)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="INR")
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="ACTIVE")

    opened_at: Mapped[dt.datetime] = mapped_column(DateTime, nullable=False)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, nullable=False, default=dt.datetime.utcnow)
    updated_at: Mapped[dt.datetime] = mapped_column(
        DateTime, nullable=False, default=dt.datetime.utcnow, onupdate=dt.datetime.utcnow
    )

    # Same-domain relationship only (banking -> banking). Referenced by
    # class name string so this module never has to import Transaction
    # (avoids a circular import; resolved lazily at mapper-configure time).
    transactions = relationship(
        "Transaction", back_populates="account", cascade="all, delete-orphan"
    )

    def __init__(self, **kwargs):
        if "account_id" in kwargs:
            validate_business_id("account_business_id", kwargs["account_id"])
        if "customer_business_id" in kwargs:
            validate_business_id("customer_business_id", kwargs["customer_business_id"])
        super().__init__(**kwargs)

    def __repr__(self) -> str:  # pragma: no cover - debugging convenience
        return f"<Account account_id={self.account_id} status={self.status}>"
