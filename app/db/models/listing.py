from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    Float,
    DateTime,
    ForeignKey,
    Boolean,
    Enum
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum

from app.db.base_class import Base
from sqlalchemy import JSON


class ListingType(str, enum.Enum):
    product = "product"
    service = "service"


class Listing(Base):
    __tablename__ = "listings"

    id = Column(Integer, primary_key=True, index=True)

    merchant_id = Column(
        Integer,
        ForeignKey("merchants.id", ondelete="CASCADE"),
        nullable=False
    )

    subcategory_id = Column(
        Integer,
        ForeignKey("subcategories.id", ondelete="CASCADE"),
        nullable=False
    )

    listing_type = Column(
        Enum(ListingType),
        nullable=False
    )

    name = Column(String, nullable=False, index=True)

    description = Column(Text, nullable=True)

    price = Column(Float, nullable=False)

    # NEW
    currency = Column(String, default="USD", nullable=False)

    # Product specific
    stock_quantity = Column(Integer, nullable=True)

    # Service specific
    service_duration_minutes = Column(Integer, nullable=True)

    is_active = Column(Boolean, default=True, nullable=False)

    views_count = Column(Integer, default=0)
    wishlist_count = Column(Integer, default=0)
    bookings_count = Column(Integer, default=0)

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )

    merchant = relationship("Merchant", back_populates="listings")

    subcategory = relationship(
        "SubCategory",
        back_populates="listings"
    )

    image_urls = Column(JSON, default=list)
    video_url = Column(String, nullable=True)
