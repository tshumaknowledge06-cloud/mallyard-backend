from sqlalchemy import Column, Integer, ForeignKey, Boolean, UniqueConstraint
from app.db.base_class import Base

class Route(Base):
    __tablename__ = "routes"

    id = Column(Integer, primary_key=True, index=True)

    origin_city_id = Column(Integer, ForeignKey("cities.id"), nullable=False)
    destination_city_id = Column(Integer, ForeignKey("cities.id"), nullable=False)

    estimated_days_min = Column(Integer, nullable=False)
    estimated_days_max = Column(Integer, nullable=False)

    is_active = Column(Boolean, default=True)

    __table_args__ = (
        UniqueConstraint("origin_city_id", "destination_city_id", name="unique_route"),
    )