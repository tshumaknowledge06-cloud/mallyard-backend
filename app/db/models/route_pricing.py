from sqlalchemy import Column, Integer, ForeignKey, String, Float
from app.db.base_class import Base

class RoutePricing(Base):
    __tablename__ = "route_pricing"

    id = Column(Integer, primary_key=True, index=True)

    route_id = Column(Integer, ForeignKey("routes.id"), nullable=False)

    package_type = Column(String, nullable=False)  # small | medium | large
    base_price = Column(Float, nullable=False)