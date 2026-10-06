"""
Transaction model -- owned exclusively by the BANKING domain.

account_id_fk is a SAME-DOMAIN foreign key (transactions -> accounts),
which is explicitly permitted by the architecture. There is no foreign key
or relationship anywhere in this file pointing outside the banking domain.
"""
from __future__ import annotations

import datetime as dt

from sqlalchemy import DateTime, ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from data.models.base import Base
from data.validation import validate_business_id


class Transaction(Base):
    __tablename__ = "transactions"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    # Business identifier, internal format TXN-XXXXXX.
    transaction_id: Mapped[str] = mapped_column(String(16), unique=True, nullable=False, index=True)

    # Same-domain FK: banking -> banking. This is the ONLY foreign key
    # permitted on this table.
    account_id_fk: Mapped[int] = mapped_column(ForeignKey("accounts.id"), nullable=False, index=True)

    amount: Mapped[float] = mapped_column(Numeric(14, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="INR")
    transaction_type: Mapped[str] = mapped_column(String(32), nullable=False)  # DEBIT, CREDIT, etc.
    description: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="POSTED")

    timestamp: Mapped[dt.datetime] = mapped_column(DateTime, nullable=False)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, nullable=False, default=dt.datetime.utcnow)

    account = relationship("Account", back_populates="transactions")

    def __init__(self, **kwargs):
        if "transaction_id" in kwargs:
            validate_business_id("transaction_id", kwargs["transaction_id"])
        super().__init__(**kwargs)

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Transaction transaction_id={self.transaction_id} type={self.transaction_type}>"
