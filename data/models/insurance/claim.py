"""
Claim model -- owned exclusively by the INSURANCE domain.

policy_id_fk is a SAME-DOMAIN foreign key (claims -> policies), which is
explicitly permitted. No foreign key or relationship to any other domain
exists here.
"""
from __future__ import annotations

import datetime as dt

from sqlalchemy import DateTime, ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from data.models.base import Base
from data.validation import validate_business_id


class Claim(Base):
    __tablename__ = "claims"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    # Business identifier, format CLM-XXXXX.
    claim_id: Mapped[str] = mapped_column(String(16), unique=True, nullable=False, index=True)

    # Same-domain FK: insurance -> insurance. The only FK permitted here.
    policy_id_fk: Mapped[int] = mapped_column(ForeignKey("policies.id"), nullable=False, index=True)

    # Cross-domain business reference ONLY -- never ForeignKey("customers.id").
    customer_business_id: Mapped[str] = mapped_column(String(16), nullable=False, index=True)

    claim_type: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="SUBMITTED")
    amount_claimed: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)

    filed_at: Mapped[dt.datetime] = mapped_column(DateTime, nullable=False)
    resolved_at: Mapped[dt.datetime | None] = mapped_column(DateTime, nullable=True)

    policy = relationship("Policy", back_populates="claims")

    def __init__(self, **kwargs):
        if "claim_id" in kwargs:
            validate_business_id("claim_business_id", kwargs["claim_id"])
        if "customer_business_id" in kwargs:
            validate_business_id("customer_business_id", kwargs["customer_business_id"])
        super().__init__(**kwargs)

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Claim claim_id={self.claim_id} status={self.status}>"
