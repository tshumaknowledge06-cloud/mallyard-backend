from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app.db.session import get_db
from app.db.models.wishlist import Wishlist
from app.db.models.listing import Listing
from app.db.models.merchant import Merchant
from app.schemas.wishlist import WishlistCreate, WishlistOut
from app.api.deps import get_current_user
from app.db.models.user import User


router = APIRouter(
    prefix="/wishlist",
    tags=["Wishlist"]
)


# -----------------------------------------
# Add to Wishlist
# -----------------------------------------

@router.post("/", response_model=WishlistOut)
def add_to_wishlist(
    data: WishlistCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):

    listing = db.query(Listing).filter(
        Listing.id == data.listing_id
    ).first()

    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")

    # ✅ GET MERCHANT
    merchant = db.query(Merchant).filter(
        Merchant.id == listing.merchant_id
    ).first()

    if merchant and merchant.user_id == current_user.id:
        raise HTTPException(
            status_code=400,
            detail="You cannot wishlist your own listing"
        )

    existing = db.query(Wishlist).filter(
        Wishlist.user_id == current_user.id,
        Wishlist.listing_id == data.listing_id
    ).first()

    if existing:
        raise HTTPException(status_code=400, detail="Already in wishlist")

    wishlist = Wishlist(
        user_id=current_user.id,
        listing_id=data.listing_id
    )

    listing.wishlist_count = (listing.wishlist_count or 0) + 1

    db.add(wishlist)
    db.commit()
    db.refresh(wishlist)

    return wishlist


# -----------------------------------------
# Get User Wishlist
# -----------------------------------------

@router.get("/", response_model=List[WishlistOut])
def get_wishlist(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):

    return db.query(Wishlist).filter(
        Wishlist.user_id == current_user.id
    ).all()


# -----------------------------------------
# Remove from Wishlist
# -----------------------------------------

@router.delete("/{listing_id}")
def remove_from_wishlist(
    listing_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):

    item = db.query(Wishlist).filter(
        Wishlist.user_id == current_user.id,
        Wishlist.listing_id == listing_id
    ).first()

    if not item:
        raise HTTPException(status_code=404, detail="Not in wishlist")

    # ✅ Optional: reduce count safely
    listing = db.query(Listing).filter(
        Listing.id == listing_id
    ).first()

    if listing and listing.wishlist_count:
        listing.wishlist_count -= 1

    db.delete(item)
    db.commit()

    return {"message": "Removed from wishlist"}