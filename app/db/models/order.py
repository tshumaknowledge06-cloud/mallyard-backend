from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.base_class import Base


class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True)

    buyer_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False
    )

    merchant_id = Column(
        Integer,
        ForeignKey("merchants.id", ondelete="CASCADE"),
        nullable=False
    )

    # ✅ ADD THIS (CRITICAL)
    listing_id = Column(
        Integer,
        ForeignKey("listings.id", ondelete="CASCADE"),
        nullable=False
    )

    status = Column(
        String,
        default="pending",
        nullable=False
    )

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )

    delivery_method = Column(String, nullable=True)  # onsite | delivery
    dropoff_address = Column(String, nullable=True)  # ✅ needed for delivery
    delivery_instructions = Column(String, nullable=True)
    customer_phone = Column(String, nullable=True)
    
    # Relationships
    buyer = relationship("User")
    merchant = relationship("Merchant")
    listing = relationship("Listing")  # ✅ NEW
    items = relationship(
        "OrderItem",
        back_populates="order",
        cascade="all, delete-orphan"
    )