from datetime import datetime, timedelta
from sqlalchemy import func
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.db.session import get_db
from app.db.models.listing import Listing
from app.db.models.merchant import Merchant
from app.db.models.recently_viewed import RecentlyViewed
from app.schemas.listing import ListingOut

router = APIRouter(
    prefix="/trending",
    tags=["Trending"]
)


@router.get("/", response_model=List[ListingOut])
def get_trending_listings(
    limit: int = 20,
    db: Session = Depends(get_db)
):

    seven_days_ago = datetime.utcnow() - timedelta(days=7)

    # Subquery for recent views
    recent_views = (
        db.query(
            RecentlyViewed.listing_id,
            func.count(RecentlyViewed.id).label('view_count')
        )
        .filter(RecentlyViewed.viewed_at >= seven_days_ago)
        .group_by(RecentlyViewed.listing_id)
        .subquery()
    )

    # Main query
    trending = (
        db.query(Listing)
        .join(Merchant, Listing.merchant_id == Merchant.id)
        .outerjoin(recent_views, recent_views.c.listing_id == Listing.id)
        .filter(Merchant.status == "approved")
        .order_by(
            (
                func.coalesce(recent_views.c.view_count, 0) +
                (Listing.wishlist_count * 3) +
                (Listing.bookings_count * 5)
            ).desc()
        )
        .limit(limit)
        .all()
    )

    return trending