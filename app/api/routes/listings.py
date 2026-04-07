from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List

from app.db.models.user import User
from app.db.session import get_db
from app.db.models.listing import Listing
from app.db.models.merchant import Merchant
from app.db.models.category import Category
from app.db.models.subcategory import SubCategory

from app.schemas.listing import ListingCreate, ListingOut, ListingCompareOut
from app.api.deps import get_current_user
from fastapi import UploadFile, File
from app.utils.file_upload import upload_file

router = APIRouter(
    tags=["Listings"]
)


# -------------------------------------------------
# Create Listing (Merchant Only)
# -------------------------------------------------

@router.post("/", response_model=ListingOut)
def create_listing(
    listing_in: ListingCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    merchant = db.query(Merchant).filter(
        Merchant.user_id == current_user.id
    ).first()

    if not merchant:
        raise HTTPException(status_code=403, detail="Not a merchant")

    if merchant.status != "approved":
        raise HTTPException(status_code=403, detail="Merchant not approved")

    listing = Listing(
        merchant_id=merchant.id,
        subcategory_id=listing_in.subcategory_id,
        listing_type=listing_in.listing_type,
        name=listing_in.name,
        description=listing_in.description,
        price=listing_in.price,
        currency=listing_in.currency,
        stock_quantity=listing_in.stock_quantity,
        service_duration_minutes=listing_in.service_duration_minutes,
    )

    db.add(listing)
    db.commit()
    db.refresh(listing)

    return listing


# -------------------------------------------------
# Update Listing (Merchant Only)
# -------------------------------------------------

@router.put("/{listing_id}", response_model=ListingOut)
def update_listing(
    listing_id: int,
    listing_in: ListingCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    listing = db.query(Listing).filter(Listing.id == listing_id).first()

    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")

    merchant = db.query(Merchant).filter(
        Merchant.id == listing.merchant_id
    ).first()

    if not merchant or merchant.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")

    # ✅ Update fields
    listing.name = listing_in.name
    listing.description = listing_in.description
    listing.price = listing_in.price
    listing.currency = listing_in.currency
    listing.listing_type = listing_in.listing_type
    listing.subcategory_id = listing_in.subcategory_id
    listing.stock_quantity = listing_in.stock_quantity
    listing.service_duration_minutes = listing_in.service_duration_minutes

    db.commit()
    db.refresh(listing)

    return listing


# -------------------------------------------------
# Delete Listing (Merchant Only)
# -------------------------------------------------

@router.delete("/{listing_id}")
def delete_listing(
    listing_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    # 1. Get listing
    listing = db.query(Listing).filter(Listing.id == listing_id).first()

    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")

    # 2. Check ownership
    merchant = db.query(Merchant).filter(
        Merchant.id == listing.merchant_id
    ).first()

    if not merchant or merchant.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")

    # 3. Get related order IDs
    order_ids = [o.id for o in listing.orders]

    if order_ids:
        # 4. Get delivery requests linked to orders
        delivery_requests = db.query(DeliveryRequest).filter(
            DeliveryRequest.order_id.in_(order_ids)
        ).all()

        delivery_request_ids = [dr.id for dr in delivery_requests]

        if delivery_request_ids:
            # 5. Delete delivery matches FIRST (deepest)
            db.query(DeliveryMatch).filter(
                DeliveryMatch.delivery_request_id.in_(delivery_request_ids)
            ).delete(synchronize_session=False)

            # 6. Delete delivery requests
            db.query(DeliveryRequest).filter(
                DeliveryRequest.id.in_(delivery_request_ids)
            ).delete(synchronize_session=False)

        # 7. Delete orders
        db.query(Order).filter(
            Order.id.in_(order_ids)
        ).delete(synchronize_session=False)

    # 8. Delete listing
    db.delete(listing)

    # 9. Commit once
    db.commit()

    return {"message": "Listing deleted successfully"}

@router.get("/mine", response_model=List[ListingOut])
def get_my_listings(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):

    merchant = db.query(Merchant).filter(
        Merchant.user_id == current_user.id
    ).first()

    if not merchant:
        return []

    listings = db.query(Listing).filter(
        Listing.merchant_id == merchant.id
    ).all()

    return listings


# -------------------------------------------------
# Public Marketplace
# -------------------------------------------------

@router.get("/marketplace", response_model=List[ListingOut])
def get_marketplace_listings(
    page: int = 1,
    page_size: int = 10,
    category_id: int | None = None,
    subcategory_id: int | None = None,
    min_price: float | None = None,
    max_price: float | None = None,
    listing_type: str | None = None,
    search: str | None = None,
    location: str | None = Query(None),
    db: Session = Depends(get_db)
):

    skip = (page - 1) * page_size

    query = (
        db.query(Listing)
        .join(Merchant)
        .join(SubCategory)
        .join(Category)
        .filter(
            Listing.is_active == True,
            Merchant.status == "approved"
        )
    )

    if category_id:
        query = query.filter(Category.id == category_id)

    if subcategory_id:
        query = query.filter(SubCategory.id == subcategory_id)

    if min_price is not None:
        query = query.filter(Listing.price >= min_price)

    if max_price is not None:
        query = query.filter(Listing.price <= max_price)

    if listing_type:
        query = query.filter(Listing.listing_type == listing_type)

    if search:
        query = query.filter(Listing.name.ilike(f"%{search}%"))

    # ✅ LOCATION FILTER
    if location:
        query = query.filter(
            Merchant.location.ilike(f"%{location}%")
        )

    listings = query.offset(skip).limit(page_size).all()

    return listings


# ---------------------------------------------------
# Get comparable listings
# ---------------------------------------------------

from sqlalchemy import or_

@router.get("/{listing_id}/comparables", response_model=List[ListingCompareOut])
def get_comparable_listings(
    listing_id: int,
    db: Session = Depends(get_db)
):

    listing = db.query(Listing).filter(Listing.id == listing_id).first()

    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")

    # 🔥 STEP 1: Extract keywords from listing name
    words = listing.name.lower().split()

    # Remove very short/common words (optional but powerful)
    keywords = [w for w in words if len(w) > 2]

    # 🔥 STEP 2: Build LIKE filters
    name_filters = [
        Listing.name.ilike(f"%{word}%")
        for word in keywords
    ]

    # 🔥 STEP 3: Try smart name matching
    comparables = (
        db.query(Listing)
        .join(Merchant)
        .filter(
            Listing.id != listing.id,
            Listing.listing_type == listing.listing_type,
            Listing.is_active == True,
            Merchant.status == "approved",
            or_(*name_filters) if name_filters else False
        )
        .limit(20)
        .all()
    )

    # 🔥 STEP 4: FALLBACK → subcategory
    if len(comparables) == 0:
        comparables = (
            db.query(Listing)
            .join(Merchant)
            .filter(
                Listing.id != listing.id,
                Listing.listing_type == listing.listing_type,
                Listing.subcategory_id == listing.subcategory_id,
                Listing.is_active == True,
                Merchant.status == "approved"
            )
            .limit(20)
            .all()
        )

    return comparables


# ---------------------------------------------------
# Compare selected listings
# ---------------------------------------------------

from fastapi import Query
from typing import List, Union

@router.get("/compare", response_model=List[ListingCompareOut])
def compare_listings(
    ids: Union[List[int], str] = Query(...),
    db: Session = Depends(get_db)
):
    if isinstance(ids, str):
        ids = [int(i) for i in ids.split(",")]

    if len(ids) > 5:
        raise HTTPException(
            status_code=400,
            detail="Maximum comparison limit is 5 listings"
        )

    listings = (
        db.query(Listing)
        .join(Merchant)
        .filter(
            Listing.id.in_(ids),
            Listing.is_active == True,
            Merchant.status == "approved"
        )
        .all()
    )

    return listings


# -------------------------------------------------
# Get Listing Detail
# -------------------------------------------------

@router.get("/{listing_id}", response_model=ListingOut)
def get_listing_detail(
    listing_id: int,
    db: Session = Depends(get_db)
):

    listing = (
        db.query(Listing)
        .join(Merchant)
        .filter(
            Listing.id == listing_id,
            Listing.is_active == True,
            Merchant.status == "approved"
        )
        .first()
    )

    if not listing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Listing not found"
        )

    return listing


# -------------------------------------------------
# Upload Listing Images (CLOUD STORAGE)
# -------------------------------------------------

@router.post("/{listing_id}/upload-images")
def upload_listing_images(
    listing_id: int,
    files: List[UploadFile] = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):

    # ✅ Allowed types
    ALLOWED_TYPES = ["image/jpeg", "image/png", "image/webp"]

    # ✅ Max size (5MB per image)
    MAX_SIZE = 5 * 1024 * 1024

    # ✅ Get listing
    listing = db.query(Listing).filter(
        Listing.id == listing_id
    ).first()

    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")

    # ✅ Ownership check
    merchant = db.query(Merchant).filter(
        Merchant.id == listing.merchant_id
    ).first()

    if not merchant or merchant.user_id != current_user.id:
        raise HTTPException(
            status_code=403,
            detail="Not authorized"
        )

    new_images = []

    for file in files:

        if file.content_type not in ALLOWED_TYPES:
            raise HTTPException(
                status_code=400,
                detail="Only JPG, PNG, WEBP allowed"
            )

        contents = file.file.read()

        if len(contents) > MAX_SIZE:
            raise HTTPException(
                status_code=400,
                detail="Image too large (max 5MB)"
            )

        file.file.seek(0)

        # 🔥 CLOUD UPLOAD (no local file saving)
        file_url = upload_file(file)
        new_images.append(file_url)

    # 🔥 APPEND (NOT REPLACE)
    existing = listing.image_urls or []
    listing.image_urls = existing + new_images

    db.commit()
    db.refresh(listing)

    return {
        "message": "Images uploaded successfully",
        "image_urls": listing.image_urls
    }


# -------------------------------------------------
# Delete Listing Image
# -------------------------------------------------

@router.delete("/{listing_id}/images")
def delete_listing_image(
    listing_id: int,
    image_url: str,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    listing = db.query(Listing).filter(Listing.id == listing_id).first()

    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")

    merchant = db.query(Merchant).filter(
        Merchant.id == listing.merchant_id
    ).first()

    if not merchant or merchant.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")

    if not listing.image_urls or image_url not in listing.image_urls:
        raise HTTPException(status_code=404, detail="Image not found")

    # ✅ Remove from DB only (files in cloud storage)
    listing.image_urls = [
        img for img in listing.image_urls if img != image_url
    ]

    db.commit()
    db.refresh(listing)

    return {
        "message": "Image removed",
        "image_urls": listing.image_urls
    }


# -------------------------------------------------
# Upload Listing Video (CLOUD STORAGE)
# -------------------------------------------------

@router.post("/{listing_id}/upload-video")
def upload_listing_video(
    listing_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):

    # ✅ Allowed types
    ALLOWED_TYPES = ["video/mp4", "video/webm", "video/quicktime"]

    # ✅ Max size (20MB)
    MAX_SIZE = 20 * 1024 * 1024

    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(
            status_code=400,
            detail="Only MP4, WEBM, MOV videos allowed"
        )

    # ✅ Read file to check size
    contents = file.file.read()
    if len(contents) > MAX_SIZE:
        raise HTTPException(
            status_code=400,
            detail="Video too large (max 20MB)"
        )

    # Reset pointer after reading
    file.file.seek(0)

    # ✅ Get listing
    listing = db.query(Listing).filter(
        Listing.id == listing_id
    ).first()

    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")

    # ✅ Ownership check
    merchant = db.query(Merchant).filter(
        Merchant.id == listing.merchant_id
    ).first()

    if not merchant or merchant.user_id != current_user.id:
        raise HTTPException(
            status_code=403,
            detail="Not authorized"
        )

    # 🔥 CLOUD UPLOAD (no local file saving)
    video_url = upload_file(file)

    listing.video_url = video_url

    db.commit()
    db.refresh(listing)

    return {
        "message": "Video uploaded successfully",
        "video_url": video_url
    }


# -------------------------------------------------
# Delete Listing Video
# -------------------------------------------------

@router.delete("/{listing_id}/video")
def delete_listing_video(
    listing_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    listing = db.query(Listing).filter(Listing.id == listing_id).first()

    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")

    merchant = db.query(Merchant).filter(
        Merchant.id == listing.merchant_id
    ).first()

    if not merchant or merchant.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")

    if not listing.video_url:
        raise HTTPException(status_code=404, detail="No video to delete")

    # ✅ Remove from DB only (files in cloud storage)
    listing.video_url = None

    db.commit()
    db.refresh(listing)

    return {"message": "Video deleted"}