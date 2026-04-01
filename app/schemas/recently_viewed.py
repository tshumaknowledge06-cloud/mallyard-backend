from pydantic import BaseModel
from datetime import datetime
from app.schemas.listing import ListingOut
from typing import Optional, List


class RecentlyViewedOut(BaseModel):
    id: int
    viewed_at: datetime
    listing: ListingOut

    # ✅ MEDIA SUPPORT
    image_urls: List[str] = []
    video_url: Optional[str] = None

    class Config:
        from_attributes = True