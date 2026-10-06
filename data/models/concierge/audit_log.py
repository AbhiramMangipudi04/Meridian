"""
AuditLog model -- owned exclusively by the CONCIERGE_OPS domain.

audit_log is accessible to concierge_ops_server ONLY. No other server may
read or write this table; access_control.py enforces that structurally.
The Data module provides the repository (create/read_all/read_by_id/
update); the future concierge_ops_server's write_audit_log tool is what
will generate runtime rows for every write operation it performs.
"""
from __future__ import annotations

import datetime as dt

from sqlalchemy import DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from data.models.base import Base
from data.validation import validate_business_id


class AuditLog(Base):
    __tablename__ = "audit_log"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    # Business identifier, internal format AUD-XXXXXX.
    audit_id: Mapped[str] = mapped_column(String(16), unique=True, nullable=False, index=True)

    timestamp: Mapped[dt.datetime] = mapped_column(DateTime, nullable=False, default=dt.datetime.utcnow)
    action_type: Mapped[str] = mapped_column(String(64), nullable=False)
    performed_by: Mapped[str] = mapped_column(String(64), nullable=False)  # server/agent identity
    customer_business_id: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    outcome: Mapped[str] = mapped_column(String(32), nullable=False)  # SUCCESS, FAILURE, BLOCKED
    details: Mapped[str] = mapped_column(Text, nullable=False, default="")

    def __init__(self, **kwargs):
        if "audit_id" in kwargs:
            validate_business_id("audit_id", kwargs["audit_id"])
        if "customer_business_id" in kwargs:
            validate_business_id("customer_business_id", kwargs["customer_business_id"])
        super().__init__(**kwargs)

    def __repr__(self) -> str:  # pragma: no cover
        return f"<AuditLog audit_id={self.audit_id} action_type={self.action_type}>"
