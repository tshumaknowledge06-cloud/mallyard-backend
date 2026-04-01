from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List

from app.db.session import get_db
from app.db.models.recently_viewed import RecentlyViewed
from app.db.models.listing import Listing
from app.schemas.recently_viewed import RecentlyViewedOut
from app.api.deps import get_current_user
from app.db.models.user import User


router = APIRouter(
    prefix="/recently-viewed",
    tags=["Recently Viewed"]
)


# -----------------------------
# Record Listing View
# -----------------------------

@router.post("/{listing_id}")
def record_view(
    listing_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):

    listing = db.query(Listing).filter(Listing.id == listing_id).first()

    if not listing:
        return {"message": "Listing not found"}
    
    listing.views_count += 1
    db.commit()

    existing = db.query(RecentlyViewed).filter(
        RecentlyViewed.user_id == current_user.id,
        RecentlyViewed.listing_id == listing_id
    ).first()

    if existing:
        existing.viewed_at = None  # triggers update timestamp
        db.commit()
        return {"message": "View updated"}

    view = RecentlyViewed(
        user_id=current_user.id,
        listing_id=listing_id
    )

    db.add(view)
    db.commit()

    return {"message": "View recorded"}


# -----------------------------
# Get Recently Viewed
# -----------------------------

@router.get("/", response_model=List[RecentlyViewedOut])
def get_recently_viewed(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):

    views = db.query(RecentlyViewed).filter(
        RecentlyViewed.user_id == current_user.id
    ).order_by(
        RecentlyViewed.viewed_at.desc()
    ).limit(10).all()

    return views