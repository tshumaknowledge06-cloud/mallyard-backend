from sqlalchemy import Column, Integer, String, ForeignKey, Boolean
from sqlalchemy.orm import relationship

from app.db.base import Base

class SellerProfile(Base):
    __tablename__ = "seller_profiles"

    id = Column(Integer, primary_key=True, index=True)

    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    business_name = Column(String, nullable=False)
    description = Column(String, nullable=True)

    city = Column(String, nullable=False)
    country = Column(String, nullable=False)

    is_service_provider = Column(Boolean, default=False)
    is_verified = Column(Boolean, default=False)

    user = relationship("User")
