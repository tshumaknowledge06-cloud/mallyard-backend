from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime


class DeliveryPartnerCreate(BaseModel):
    full_name: str
    phone_number: str
    email: EmailStr
    password: str
    vehicle_type: str
    license_number: Optional[str] = None
    operating_city: str


class DeliveryPartnerUpdate(BaseModel):
    full_name: str
    phone_number: str
    vehicle_type: str
    license_number: Optional[str] = None
    operating_city: str

class DeliveryPartnerOut(BaseModel):
    id: int
    full_name: str
    phone_number: str
    vehicle_type: str
    operating_city: str
    is_active: bool

    trust_score: float
    completed_deliveries: int

    profile_image_url: Optional[str] = None
    vehicle_image_url: Optional[str] = None

    created_at: datetime

    class Config:
        from_attributes = True
