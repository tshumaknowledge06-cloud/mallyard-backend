from sqlalchemy import Column, Integer, String, Boolean, Float
from app.db.base_class import Base

class City(Base):
    __tablename__ = "cities"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    country = Column(String, nullable=False)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    is_active = Column(Boolean, default=True)