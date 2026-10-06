"""
EscalationFlag model -- owned exclusively by the CONCIERGE_OPS domain.

Represents the three hard escalation categories (financial_hardship,
safeguarding_concern, compliance_override_request) plus ordinary
confidence-based escalations. These rows are deterministic fixtures that
the future run_escalation_check tool/orchestration layer will read --
this module does not implement that decision logic, only the data it
needs.
"""
from __future__ import annotations

import datetime as dt

from sqlalchemy import DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from data.models.base import Base
from data.validation import validate_business_id

HARD_ESCALATION_CATEGORIES = (
    "financial_hardship",
    "safeguarding_concern",
    "compliance_override_request",
)


class EscalationFlag(Base):
    __tablename__ = "escalation_flags"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    # Business identifier, internal format ESC-XXXXX.
    escalation_id: Mapped[str] = mapped_column(String(16), unique=True, nullable=False, index=True)

    customer_business_id: Mapped[str] = mapped_column(String(16), nullable=False, index=True)

    # One of HARD_ESCALATION_CATEGORIES, or "confidence_based" / "none".
    category: Mapped[str] = mapped_column(String(32), nullable=False)
    request_reference: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="OPEN")
    notes: Mapped[str] = mapped_column(Text, nullable=False, default="")

    created_at: Mapped[dt.datetime] = mapped_column(DateTime, nullable=False, default=dt.datetime.utcnow)
    resolved_at: Mapped[dt.datetime | None] = mapped_column(DateTime, nullable=True)

    def __init__(self, **kwargs):
        if "escalation_id" in kwargs:
            validate_business_id("escalation_id", kwargs["escalation_id"])
        if "customer_business_id" in kwargs:
            validate_business_id("customer_business_id", kwargs["customer_business_id"])
        super().__init__(**kwargs)

    def __repr__(self) -> str:  # pragma: no cover
        return f"<EscalationFlag escalation_id={self.escalation_id} category={self.category}>"
