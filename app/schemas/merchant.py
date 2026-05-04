from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List


# ==========================
# Base Schema
# ==========================
class MerchantBase(BaseModel):
    business_name: str
    description: Optional[str] = None
    merchant_type: str
    location: Optional[str] = None
    contact_phone: str
    payment_methods: Optional[List[str]] = None
    pickup_address: Optional[str] = None
    city_name: str

class MerchantUpdate(BaseModel):
    business_name: Optional[str] = None
    description: Optional[str] = None
    location: Optional[str] = None
    pickup_address: Optional[str] = None
    contact_phone: Optional[str] = None
    city_name: Optional[str] = None

    class Config:
        from_attributes = True


# ==========================
# Create Schema
# ==========================
class MerchantCreate(MerchantBase):
    pass


# ==========================
# Output Schema
# ==========================
class MerchantOut(BaseModel):
    id: int
    user_id: int
    business_name: Optional[str]
    description: Optional[str]
    merchant_type: str
    location: Optional[str]
    contact_phone: str
    pickup_address: Optional[str]
    status: str
    created_at: datetime

    city_id: int
    city_name: Optional[str]  

    class Config:
        from_attributes = True