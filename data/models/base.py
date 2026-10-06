"""
Shared SQLAlchemy declarative Base.

Every domain's models (banking, insurance, wealth, concierge) inherit from
this single Base so they can all live in one metadata/one physical
database file. Sharing a Base is purely a schema-creation convenience --
it does NOT imply the domains may reference each other's tables. Foreign
keys across domains are forbidden regardless of the shared Base (see
data/models/README notes in each domain package and the project README).
"""
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass
