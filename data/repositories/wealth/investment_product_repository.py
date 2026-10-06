from data.models.wealth.investment_product import InvestmentProduct
from data.repositories.base_repository import BaseRepository


class InvestmentProductRepository(BaseRepository[InvestmentProduct]):
    model = InvestmentProduct
    business_id_field = "product_id"
