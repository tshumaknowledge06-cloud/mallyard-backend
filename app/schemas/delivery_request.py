from typing import Optional
from pydantic import BaseModel
from datetime import datetime

class DeliveryRequestOut(BaseModel):
    id: int
    order_id: int
    seller_id: Optional[int]
    pickup_address: Optional[str]
    dropoff_address: Optional[str]

    delivery_instructions: Optional[str]

    delivery_price: Optional[float]
    estimated_delivery_days: Optional[int]
    distance_km: Optional [float] = None

    status: str
    created_at: datetime

    driver_name: str | None = None
    driver_phone: str | None = None

    class Config:
        from_attributes = True
        

class PickupCreate(BaseModel):
    pickup_address: str


class DeliveryRequestCreate(BaseModel):
    delivery_method: str
    delivery_instructions: Optional[str] = None


class DeliveryPartnerView(BaseModel):
    request_id: int
    order_id: int

    pickup_address: str | None
    dropoff_address: str | None
    delivery_instructions: str | None

    status: str

    seller_name: str
    seller_phone: str | None

    buyer_name: str
    buyer_phone: str | None

    listing_name: str

    # 🔥 CRITICAL ADDITIONS
    delivery_price: float | None
    estimated_delivery_days: int | None
    distance_km: float | None
    
    class Config:
        from_attributes = True

