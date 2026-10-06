from sqlalchemy import select

from data.models.wealth.portfolio import Portfolio
from data.repositories.base_repository import BaseRepository


class PortfolioRepository(BaseRepository[Portfolio]):
    model = Portfolio
    business_id_field = "portfolio_id"

    def read_by_customer(self, customer_business_id: str) -> list[Portfolio]:
        stmt = select(Portfolio).where(Portfolio.customer_business_id == customer_business_id)
        return list(self.session.execute(stmt).scalars().all())
