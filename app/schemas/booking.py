from pydantic import BaseModel
from typing import Optional
from datetime import datetime


# ----------------------------
# Create Booking
# ----------------------------

class BookingCreate(BaseModel):
    listing_id: int
    description: str
    contact_number: str
    preferred_time: Optional[datetime] = None


# ----------------------------
# Update Booking
# ----------------------------

class BookingUpdate(BaseModel):
    status: str


# ----------------------------
# Output Booking
# ----------------------------

class BookingOut(BaseModel):
    id: int

    listing_id: int
    customer_id: int
    seller_id: int

    description: str
    contact_number: str
    preferred_time: Optional[datetime] = None

    status: str
    created_at: datetime

    # Listing information
    listing_name: str
    image_urls: list[str] = []
    price: float
    currency: str

    # Merchant information
    business_name: str

    class Config:
        from_attributes = True