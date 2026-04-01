from sqlalchemy import Column, Integer, String, Boolean, DateTime, Enum
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import enum

from app.db.base_class import Base


class Role(str, enum.Enum):
    admin = "admin"
    seller = "seller"
    customer = "customer"
    delivery_partner = "delivery_partner"


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)

    email = Column(String, unique=True, index=True, nullable=False)
    full_name = Column(String, nullable=False)
    phone_number = Column(String, nullable=True)
    hashed_password = Column(String, nullable=False)

    role = Column(
        Enum(Role, name="role", create_type=False),
        nullable=False
    )

    is_active = Column(Boolean, default=True, nullable=False)
    is_verified = Column(Boolean, default=False, nullable=False)

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )

    merchant = relationship("Merchant", back_populates="user", uselist=False)