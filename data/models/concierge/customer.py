"""
Customer model -- owned exclusively by the CONCIERGE_OPS domain.

This is the ONLY place customer_business_id is a primary, owned
identifier. Every other domain only ever stores it as a plain string
business reference, never a foreign key into this table.
"""
from __future__ import annotations

import datetime as dt

from sqlalchemy import DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from data.models.base import Base
from data.validation import validate_business_id


class Customer(Base):
    __tablename__ = "customers"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    # Business identifier, format CUS-XXXXX.
    customer_business_id: Mapped[str] = mapped_column(String(16), unique=True, nullable=False, index=True)

    full_name: Mapped[str] = mapped_column(String(128), nullable=False)
    email: Mapped[str] = mapped_column(String(128), nullable=False)
    phone: Mapped[str] = mapped_column(String(32), nullable=False)

    kyc_status: Mapped[str] = mapped_column(String(16), nullable=False, default="VERIFIED")
    customer_tier: Mapped[str] = mapped_column(String(16), nullable=False, default="STANDARD")

    created_at: Mapped[dt.datetime] = mapped_column(DateTime, nullable=False, default=dt.datetime.utcnow)
    updated_at: Mapped[dt.datetime] = mapped_column(
        DateTime, nullable=False, default=dt.datetime.utcnow, onupdate=dt.datetime.utcnow
    )

    def __init__(self, **kwargs):
        if "customer_business_id" in kwargs:
            validate_business_id("customer_business_id", kwargs["customer_business_id"])
        super().__init__(**kwargs)

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Customer customer_business_id={self.customer_business_id} name={self.full_name!r}>"
