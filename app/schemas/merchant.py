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
class MerchantOut(MerchantBase):
    id: int
    user_id: int
    status: str
    created_at: datetime