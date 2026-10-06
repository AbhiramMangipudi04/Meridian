"""
Policy model -- owned exclusively by the INSURANCE domain.

No foreign key or relationship to accounts, customers, or any other
domain's tables exists here. `customer_business_id` and
`linked_account_business_id` are plain business-identifier strings used
for cross-domain business logic later (e.g. "which account funds this
policy's auto-debit"), never relational foreign keys.
"""
from __future__ import annotations

import datetime as dt

from sqlalchemy import Boolean, Date, DateTime, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from data.models.base import Base
from data.validation import validate_business_id


class Policy(Base):
    __tablename__ = "policies"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    # Business identifier, format POL-XX-XXXXX (e.g. POL-IN-30091).
    policy_id: Mapped[str] = mapped_column(String(16), unique=True, nullable=False, index=True)

    # Cross-domain business references ONLY -- never ForeignKey(...).
    customer_business_id: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    linked_account_business_id: Mapped[str | None] = mapped_column(String(16), nullable=True)

    policy_type: Mapped[str] = mapped_column(String(32), nullable=False)  # e.g. GENERAL, HEALTH, MOTOR
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="ACTIVE")

    premium_amount: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    premium_frequency: Mapped[str] = mapped_column(String(16), nullable=False, default="MONTHLY")

    # Structured, authoritative payment-terms fields. These are the source
    # of truth the hybrid-retrieval layer must prefer over any wording
    # found in the unstructured knowledge base (see docs/policy_docs and
    # the retrieval-conflict fixture).
    auto_debit_supported: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    payment_method: Mapped[str] = mapped_column(String(32), nullable=False, default="MANUAL")

    start_date: Mapped[dt.date] = mapped_column(Date, nullable=False)
    end_date: Mapped[dt.date | None] = mapped_column(Date, nullable=True)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, nullable=False, default=dt.datetime.utcnow)

    claims = relationship("Claim", back_populates="policy", cascade="all, delete-orphan")

    def __init__(self, **kwargs):
        if "policy_id" in kwargs:
            validate_business_id("policy_business_id", kwargs["policy_id"])
        if "customer_business_id" in kwargs:
            validate_business_id("customer_business_id", kwargs["customer_business_id"])
        if kwargs.get("linked_account_business_id"):
            validate_business_id("account_business_id", kwargs["linked_account_business_id"])
        super().__init__(**kwargs)

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Policy policy_id={self.policy_id} status={self.status}>"
