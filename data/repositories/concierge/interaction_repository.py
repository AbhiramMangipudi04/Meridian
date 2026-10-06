from sqlalchemy import select

from data.models.concierge.interaction_log import InteractionLog
from data.repositories.base_repository import BaseRepository


class InteractionRepository(BaseRepository[InteractionLog]):
    model = InteractionLog
    business_id_field = "interaction_id"

    def read_by_customer(self, customer_business_id: str) -> list[InteractionLog]:
        stmt = (
            select(InteractionLog)
            .where(InteractionLog.customer_business_id == customer_business_id)
            .order_by(InteractionLog.timestamp.desc())
        )
        return list(self.session.execute(stmt).scalars().all())
