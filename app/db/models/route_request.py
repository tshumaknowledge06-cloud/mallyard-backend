from sqlalchemy import Column, Integer, ForeignKey
from app.db.base_class import Base

class RouteRequest(Base):
    __tablename__ = "route_requests"

    id = Column(Integer, primary_key=True, index=True)

    origin_city_id = Column(Integer, ForeignKey("cities.id"))
    destination_city_id = Column(Integer, ForeignKey("cities.id"))

    request_count = Column(Integer, default=1)