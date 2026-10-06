from sqlalchemy import select

from data.models.insurance.policy import Policy
from data.repositories.base_repository import BaseRepository


class PolicyRepository(BaseRepository[Policy]):
    model = Policy
    business_id_field = "policy_id"

    def read_by_customer(self, customer_business_id: str) -> list[Policy]:
        stmt = select(Policy).where(Policy.customer_business_id == customer_business_id)
        return list(self.session.execute(stmt).scalars().all())
