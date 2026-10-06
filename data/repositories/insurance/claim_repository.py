from sqlalchemy import select

from data.models.insurance.claim import Claim
from data.repositories.base_repository import BaseRepository


class ClaimRepository(BaseRepository[Claim]):
    model = Claim
    business_id_field = "claim_id"

    def read_by_policy(self, policy_pk: int) -> list[Claim]:
        stmt = select(Claim).where(Claim.policy_id_fk == policy_pk)
        return list(self.session.execute(stmt).scalars().all())
