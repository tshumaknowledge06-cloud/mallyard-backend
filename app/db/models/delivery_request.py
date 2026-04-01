from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Text
from sqlalchemy.sql import func
import enum

from app.db.base_class import Base


class DeliveryRequestStatus(str, enum.Enum):
    pending = "pending"
    assigned = "assigned"
    out_for_delivery = "out_for_delivery"
    completed = "completed"


class DeliveryRequest(Base):
    __tablename__ = "delivery_requests"

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"))
    seller_id = Column(Integer, ForeignKey("merchants.id"), nullable=True)

    pickup_address = Column(String, nullable=True)
    dropoff_address = Column(String, nullable=True)

    # ✅ NEW FIELD
    delivery_instructions = Column(Text, nullable=True)

    status = Column(String, default="pending_assignment")
    created_at = Column(DateTime(timezone=True), server_default=func.now())