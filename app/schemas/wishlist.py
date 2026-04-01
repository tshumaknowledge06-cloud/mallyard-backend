from pydantic import BaseModel
from datetime import datetime

from app.schemas.listing import ListingOut


class WishlistCreate(BaseModel):
    listing_id: int


class WishlistOut(BaseModel):
    id: int
    created_at: datetime
    listing: ListingOut

    class Config:
        from_attributes = True