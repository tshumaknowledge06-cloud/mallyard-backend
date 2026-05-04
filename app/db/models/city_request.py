from sqlalchemy import Column, Integer, String
from app.db.base_class import Base

class CityRequest(Base):
    __tablename__ = "city_requests"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, unique=True)
    request_count = Column(Integer, default=1)