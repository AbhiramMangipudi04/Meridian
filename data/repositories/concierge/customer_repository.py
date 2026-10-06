from data.models.concierge.customer import Customer
from data.repositories.base_repository import BaseRepository


class CustomerRepository(BaseRepository[Customer]):
    model = Customer
    business_id_field = "customer_business_id"
