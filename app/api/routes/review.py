from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.db.models.review import Review
from app.db.models.user import User
from app.db.models.listing import Listing

from app.schemas.review import ReviewCreate, ReviewOut
from app.api.deps import get_current_user

router = APIRouter(
    prefix="/reviews",
    tags=["Reviews"]
)


# =========================================================
# CREATE REVIEW (AUTHENTICATED USERS)
# =========================================================
@router.post("/", response_model=ReviewOut)
def create_review(
    payload: ReviewCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # ✅ CHECK LISTING EXISTS
    listing = db.query(Listing).filter(
        Listing.id == payload.listing_id,
        Listing.is_active == True
    ).first()

    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")

    # ✅ VALIDATE CONTENT
    if not payload.content or not payload.content.strip():
        raise HTTPException(status_code=400, detail="Review cannot be empty")

    # ✅ CREATE REVIEW
    review = Review(
        user_id=current_user.id,
        listing_id=payload.listing_id,
        content=payload.content.strip(),
    )

    db.add(review)

    try:
        db.commit()
        db.refresh(review)
    except Exception:
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to create review")

    return ReviewOut(
        id=review.id,
        content=review.content,
        created_at=review.created_at,
        user_name=current_user.email,
    )


# =========================================================
# GET REVIEWS (PUBLIC)
# =========================================================
@router.get("/{listing_id}", response_model=list[ReviewOut])
def get_reviews(
    listing_id: int,
    db: Session = Depends(get_db),
):
    # ✅ CHECK LISTING EXISTS
    listing = db.query(Listing).filter(
        Listing.id == listing_id,
        Listing.is_active == True
    ).first()

    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")

    # ✅ JOIN USER SAFELY
    reviews = db.query(Review, User).join(
        User, Review.user_id == User.id
    ).filter(
        Review.listing_id == listing_id
    ).order_by(
        Review.created_at.desc()
    ).all()

    # ✅ FORMAT RESPONSE (SAFE)
    results = []
    for review, user in reviews:
        results.append(
            ReviewOut(
                id=review.id,
                content=review.content,
                created_at=review.created_at,
                user_name=user.email,
            )
        )

    return results