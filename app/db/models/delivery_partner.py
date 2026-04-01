from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Float
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.base_class import Base


class DeliveryPartner(Base):
    __tablename__ = "delivery_partners"

    id = Column(Integer, primary_key=True, index=True)

    # Link to authenticated user
    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        unique=True
    )

    full_name = Column(String, nullable=False)
    phone_number = Column(String, nullable=False)

    # optional duplicate contact storage (kept as you designed)
    email = Column(String, nullable=True)

    vehicle_type = Column(String, nullable=False)
    license_number = Column(String, nullable=True)

    operating_city = Column(String, nullable=False)

    is_active = Column(Boolean, default=False, nullable=False)

    # ✅ DTS v1 fields
    trust_score = Column(Float, default=5.0, nullable=False)
    completed_deliveries = Column(Integer, default=0, nullable=False)

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )

    # relationship to auth user
    user = relationship("User", backref="delivery_partner")

    profile_image_url = Column(String, nullable=True)
    vehicle_image_url = Column(String, nullable=True)