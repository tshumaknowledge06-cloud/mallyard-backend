from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, Boolean, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.base_class import Base


class Merchant(Base):
    __tablename__ = "merchants"

    id = Column(Integer, primary_key=True, index=True)

    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        unique=True
    )

    business_name = Column(String, nullable=False, index=True)
    description = Column(Text, nullable=True)

    merchant_type = Column(String, nullable=False)
    location = Column(String, nullable=True)
    contact_phone = Column(String, nullable=True)

    # 🔥 Payment configuration
    payment_methods = Column(JSON, nullable=True)  # ["card", "ecocash", "cod"]

    external_account_id = Column(String, nullable=True)
    payment_ready = Column(Boolean, default=False)
    logo_url = Column(String, nullable=True)

    # Merchant lifecycle status
    status = Column(
        String,
        nullable=False,
        default="pending_profile_completion"
    )

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )

    # Relationships
    user = relationship(
        "User",
        back_populates="merchant"
    )

    listings = relationship(
        "Listing",
        back_populates="merchant",
        cascade="all, delete"
    )