from sqlalchemy import Column, Integer, ForeignKey, DateTime
from sqlalchemy.sql import func
from app.db.base import Base


class DeliveryMatch(Base):
    __tablename__ = "delivery_matches"

    id = Column(Integer, primary_key=True, index=True)

    delivery_request_id = Column(
        Integer,
        ForeignKey("delivery_requests.id"),
        nullable=False
    )

    delivery_partner_id = Column(
        Integer,
        ForeignKey("delivery_partners.id"),
        nullable=False
    )

    assigned_at = Column(
        DateTime(timezone=True),
        server_default=func.now()
    )
