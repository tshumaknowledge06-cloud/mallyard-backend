from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List

from app.db.session import get_db
from app.db.models.listing import Listing
from app.schemas.listing import ListingOut


router = APIRouter(
    prefix="/trending",
    tags=["Trending"]
)


@router.get("/", response_model=List[ListingOut])
def get_trending_listings(db: Session = Depends(get_db)):

    listings = db.query(Listing).order_by(
        (
            Listing.views_count +
            (Listing.wishlist_count * 3) +
            (Listing.bookings_count * 5)
        ).desc()
    ).limit(10).all()

    return listings
