from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from enum import Enum


# -----------------------------
# ENUM
# -----------------------------
class ListingType(str, Enum):
    product = "product"
    service = "service"


# -----------------------------
# Create Schema
# -----------------------------
class ListingCreate(BaseModel):
    name: str
    description: Optional[str] = None
    price: float
    currency: str
    listing_type: ListingType
    stock_quantity: int
    service_duration_minutes: int = 0
    subcategory_id: int

# -----------------------------
# Merchant Short
# -----------------------------
class MerchantShort(BaseModel):
    id: int
    business_name: str
    location: Optional[str] = None
    merchant_type: str
    payment_methods: Optional[List[str]] = None

    class Config:
        from_attributes = True


# -----------------------------
# Subcategory Short
# -----------------------------
class SubcategoryShort(BaseModel):
    id: int
    name: str
    category_id: int

    class Config:
        from_attributes = True


# -----------------------------
# Listing Output
# -----------------------------
class ListingOut(BaseModel):
    id: int
    name: str
    description: Optional[str]
    price: float
    currency: str
    listing_type: str
    stock_quantity: int
    service_duration_minutes: int
    created_at: datetime

    merchant: MerchantShort
    subcategory: SubcategoryShort

    image_urls: Optional[List[str]] = []
    video_url: Optional[str] = None

    class Config:
        from_attributes = True


ListingOut.model_rebuild()


# -----------------------------
# Listing Comparison Output
# -----------------------------
class ListingCompareOut(BaseModel):
    id: int
    name: str
    description: Optional[str]
    price: float
    currency: str
    listing_type: str

    merchant: MerchantShort

    image_urls: Optional[List[str]] = []
    video_url: Optional[str] = None

    class Config:
        from_attributes = True