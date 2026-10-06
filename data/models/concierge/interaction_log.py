"""
InteractionLog model -- owned exclusively by the CONCIERGE_OPS domain.

customer_business_id is a plain business reference string; there is no
foreign key to the Customer table (even though Customer is in the same
domain) because interaction history must remain retrievable/independent
even if a customer record is ever archived. Same-domain FK is permitted
by the architecture but not required here, and this project keeps the
log append-only and decoupled from Customer's lifecycle.
"""
from __future__ import annotations

import datetime as dt

from sqlalchemy import DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from data.models.base import Base
from data.validation import validate_business_id


class InteractionLog(Base):
    __tablename__ = "interaction_log"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    # Business identifier, internal format INT-XXXXXX.
    interaction_id: Mapped[str] = mapped_column(String(16), unique=True, nullable=False, index=True)

    customer_business_id: Mapped[str] = mapped_column(String(16), nullable=False, index=True)

    timestamp: Mapped[dt.datetime] = mapped_column(DateTime, nullable=False, default=dt.datetime.utcnow)
    channel: Mapped[str] = mapped_column(String(16), nullable=False)  # CHAT, EMAIL, PHONE, SMS
    interaction_type: Mapped[str] = mapped_column(String(32), nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False, default="")
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="CLOSED")

    def __init__(self, **kwargs):
        if "interaction_id" in kwargs:
            validate_business_id("interaction_id", kwargs["interaction_id"])
        if "customer_business_id" in kwargs:
            validate_business_id("customer_business_id", kwargs["customer_business_id"])
        super().__init__(**kwargs)

    def __repr__(self) -> str:  # pragma: no cover
        return f"<InteractionLog interaction_id={self.interaction_id} type={self.interaction_type}>"
