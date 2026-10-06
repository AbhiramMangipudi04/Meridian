"""
InvestmentProduct model -- owned exclusively by the WEALTH domain.

This table is intentionally standalone (no FK to portfolios): products are
a catalog, not something that belongs to one customer or one portfolio.
"""
from __future__ import annotations

import datetime as dt

from sqlalchemy import DateTime, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from data.models.base import Base
from data.validation import validate_business_id


class InvestmentProduct(Base):
    __tablename__ = "investment_products"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    # Business identifier, format PROD-XX-XX (e.g. PROD-EQ-01).
    product_id: Mapped[str] = mapped_column(String(16), unique=True, nullable=False, index=True)

    name: Mapped[str] = mapped_column(String(128), nullable=False)
    category: Mapped[str] = mapped_column(String(32), nullable=False)  # EQUITY, DEBT, HYBRID, etc.
    risk_rating: Mapped[str] = mapped_column(String(16), nullable=False, default="MODERATE")
    min_investment: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")

    created_at: Mapped[dt.datetime] = mapped_column(DateTime, nullable=False, default=dt.datetime.utcnow)

    def __init__(self, **kwargs):
        if "product_id" in kwargs:
            validate_business_id("product_business_id", kwargs["product_id"])
        super().__init__(**kwargs)

    def __repr__(self) -> str:  # pragma: no cover
        return f"<InvestmentProduct product_id={self.product_id} name={self.name!r}>"
