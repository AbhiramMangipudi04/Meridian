from sqlalchemy import select

from data.models.concierge.escalation_flag import EscalationFlag
from data.repositories.base_repository import BaseRepository


class EscalationRepository(BaseRepository[EscalationFlag]):
    model = EscalationFlag
    business_id_field = "escalation_id"

    def read_by_customer(self, customer_business_id: str) -> list[EscalationFlag]:
        stmt = select(EscalationFlag).where(
            EscalationFlag.customer_business_id == customer_business_id
        )
        return list(self.session.execute(stmt).scalars().all())

    def read_open_by_category(self, category: str) -> list[EscalationFlag]:
        stmt = select(EscalationFlag).where(
            EscalationFlag.category == category, EscalationFlag.status == "OPEN"
        )
        return list(self.session.execute(stmt).scalars().all())
