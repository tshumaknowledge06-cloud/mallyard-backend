from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Float, Text
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
    
    order_specifications = Column(Text, nullable=True)
    delivery_method = Column(String, nullable=True)  
    dropoff_address = Column(String, nullable=True)  
    delivery_instructions = Column(String, nullable=True)
    customer_phone = Column(String, nullable=True)
    delivery_price = Column(Float, nullable=True)
    estimated_delivery_days = Column(Integer, nullable=True)
    distance_km = Column(Float, nullable=True)

    # Relationships
    buyer = relationship("User")
    merchant = relationship("Merchant")
    listing = relationship("Listing")  
    items = relationship(
        "OrderItem",
        back_populates="order",
        cascade="all, delete-orphan"
    )