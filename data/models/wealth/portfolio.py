"""
Portfolio model -- owned exclusively by the WEALTH domain.

customer_business_id is a plain business-identifier string; there is no
foreign key or relationship to customers or any other domain anywhere in
this file.
"""
from __future__ import annotations

import datetime as dt

from sqlalchemy import DateTime, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from data.models.base import Base
from data.validation import validate_business_id


class Portfolio(Base):
    __tablename__ = "portfolios"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    # Business identifier, format PORT-XXXXX.
    portfolio_id: Mapped[str] = mapped_column(String(16), unique=True, nullable=False, index=True)

    # Cross-domain business reference ONLY -- never ForeignKey("customers.id").
    customer_business_id: Mapped[str] = mapped_column(String(16), nullable=False, index=True)

    risk_profile: Mapped[str] = mapped_column(String(16), nullable=False, default="MODERATE")
    total_value: Mapped[float] = mapped_column(Numeric(14, 2), nullable=False, default=0)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="INR")
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="ACTIVE")

    created_at: Mapped[dt.datetime] = mapped_column(DateTime, nullable=False, default=dt.datetime.utcnow)
    updated_at: Mapped[dt.datetime] = mapped_column(
        DateTime, nullable=False, default=dt.datetime.utcnow, onupdate=dt.datetime.utcnow
    )

    def __init__(self, **kwargs):
        if "portfolio_id" in kwargs:
            validate_business_id("portfolio_business_id", kwargs["portfolio_id"])
        if "customer_business_id" in kwargs:
            validate_business_id("customer_business_id", kwargs["customer_business_id"])
        super().__init__(**kwargs)

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Portfolio portfolio_id={self.portfolio_id} status={self.status}>"
