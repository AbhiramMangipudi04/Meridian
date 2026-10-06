from sqlalchemy import select

from data.models.banking.transaction import Transaction
from data.repositories.base_repository import BaseRepository


class TransactionRepository(BaseRepository[Transaction]):
    model = Transaction
    business_id_field = "transaction_id"

    def read_by_account(self, account_pk: int, limit: int = 20) -> list[Transaction]:
        """
        Most-recent-first transactions for one account (backs
        get_transaction_history). Takes the account's internal PK, which
        the caller obtains from AccountRepository.read_by_id(...).id --
        this repository never joins against `accounts` itself, since
        `transactions.account_id_fk` is a same-domain FK, not a reason to
        reach across repository boundaries.
        """
        stmt = (
            select(Transaction)
            .where(Transaction.account_id_fk == account_pk)
            .order_by(Transaction.timestamp.desc())
            .limit(limit)
        )
        return list(self.session.execute(stmt).scalars().all())
