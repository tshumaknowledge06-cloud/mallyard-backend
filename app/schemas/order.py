from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List  # ✅ FIX: import List


# -----------------------------------------
# CREATE ORDER (Buyer Request)
# -----------------------------------------
class OrderCreate(BaseModel):
    listing_id: int
    quantity: int
    delivery_method: Optional[str] = None
    dropoff_address: Optional[str] = None
    delivery_instructions: Optional[str] = None
    customer_phone: str | None = None
    


# -----------------------------------------
# UPDATE ORDER STATUS (Seller Action)
# -----------------------------------------
class OrderStatusUpdate(BaseModel):
    status: str


# -----------------------------------------
# ORDER RESPONSE
# -----------------------------------------
class OrderOut(BaseModel):
    id: int
    buyer_id: int
    merchant_id: int
    listing_id: int
    status: str
    delivery_method: Optional[str]
    dropoff_address: Optional[str]
    delivery_instructions: Optional[str]
    customer_phone: Optional[str] = None
    created_at: datetime

    quantity: Optional[int] = 1
    total_price: Optional[float] = None

    # ✅ MEDIA SUPPORT
    image_urls: Optional[List[str]] = None
    video_url: Optional[str] = None

    class Config:
        from_attributes = True


# ✅ VERY IMPORTANT (Pydantic v2 safety)
OrderOut.model_rebuild()