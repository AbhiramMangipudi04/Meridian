from data.models.banking.account import Account
from data.repositories.base_repository import BaseRepository


class AccountRepository(BaseRepository[Account]):
    model = Account
    business_id_field = "account_id"

    def read_by_customer(self, customer_business_id: str) -> list[Account]:
        """All accounts linked to a customer (backs get_linked_accounts)."""
        from sqlalchemy import select

        stmt = select(Account).where(Account.customer_business_id == customer_business_id)
        return list(self.session.execute(stmt).scalars().all())
