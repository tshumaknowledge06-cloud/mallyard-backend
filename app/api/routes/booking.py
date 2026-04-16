from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.db.models.booking import Booking
from app.db.models.listing import Listing
from app.schemas.booking import BookingCreate, BookingOut, BookingUpdate
from app.api.deps import get_current_user
from app.db.models.user import User
from app.db.models.merchant import Merchant
from app.core.email import send_email

router = APIRouter()


# ---------------------------------------------------
# CREATE BOOKING
# ---------------------------------------------------
@router.post("/bookings", response_model=BookingOut)
def create_booking(
    booking: BookingCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    listing = db.query(Listing).filter(
        Listing.id == booking.listing_id
    ).first()

    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")

    if listing.listing_type != "service":
        raise HTTPException(
            status_code=400,
            detail="Bookings are only allowed for service listings"
        )

    # ✅ Get merchant
    merchant = db.query(Merchant).filter(
        Merchant.id == listing.merchant_id
    ).first()

    if not merchant:
        raise HTTPException(status_code=404, detail="Merchant not found")

    # 🚫 Prevent self-booking
    if merchant.user_id == current_user.id:
        raise HTTPException(
            status_code=400,
            detail="You cannot book your own service"
        )

    # ✅ Create booking
    new_booking = Booking(
        listing_id=listing.id,
        customer_id=current_user.id,
        seller_id=merchant.id,
        description=booking.description,
        contact_number=booking.contact_number,
        preferred_time=booking.preferred_time,
        status="pending"
    )

    listing.bookings_count = (listing.bookings_count or 0) + 1

    db.add(new_booking)
    db.commit()
    db.refresh(new_booking)

    # ✅ NON-BLOCKING EMAIL (CORRECTED)
    seller_user = db.query(User).filter(
        User.id == merchant.user_id
    ).first()

    if seller_user:
        try:
            send_email(
                to=seller_user.email,
                subject="New Booking Received — Take Action",
                body=f"""
Hey Champ 👊

You just received a new booking on The Mallyard.

Booking ID: {new_booking.id}

A customer is waiting for you right now.

Don’t lose the moment — fast response builds trust and wins repeat business.

👉 Open your dashboard:
https://themallyard.com/login/merchant

Stay sharp. Stay winning.

— The Mallyard
"""
            )
        except Exception:
            pass

    return new_booking


# ---------------------------------------------------
# GET BOOKINGS
# ---------------------------------------------------
@router.get("/bookings", response_model=list[BookingOut])
def get_bookings(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):

    # ✅ CUSTOMER → bookings they made
    if current_user.role == "customer":
        return db.query(Booking).filter(
            Booking.customer_id == current_user.id
        ).order_by(Booking.created_at.desc()).all()

    # ✅ SELLER → bookings to their services (DO NOT TOUCH)
    elif current_user.role == "seller":

        merchant = db.query(Merchant).filter(
            Merchant.user_id == current_user.id
        ).first()

        if not merchant:
            return []

        return db.query(Booking).filter(
            Booking.seller_id == merchant.id
        ).order_by(Booking.created_at.desc()).all()

    # ✅ DELIVERY PARTNER → bookings they made (NEW)
    elif current_user.role == "delivery_partner":
        return db.query(Booking).filter(
            Booking.customer_id == current_user.id
        ).order_by(Booking.created_at.desc()).all()

    # ✅ ADMIN
    elif current_user.role == "admin":
        return db.query(Booking).order_by(
            Booking.created_at.desc()
        ).all()

    else:
        raise HTTPException(status_code=403, detail="Unauthorized role")

# ---------------------------------------------------
# UPDATE BOOKING
# ---------------------------------------------------
@router.patch("/bookings/{booking_id}", response_model=BookingOut)
def update_booking(
    booking_id: int,
    update: BookingUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    booking = db.query(Booking).filter(
        Booking.id == booking_id
    ).first()

    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")

    if current_user.role != "seller":
        raise HTTPException(
            status_code=403,
            detail="Only merchants can update bookings"
        )

    merchant = db.query(Merchant).filter(
        Merchant.user_id == current_user.id
    ).first()

    if not merchant:
        raise HTTPException(
            status_code=403,
            detail="Merchant profile not found"
        )

    # ✅ FIX: compare with merchant.id (consistent with create)
    if booking.seller_id != merchant.id:
        raise HTTPException(
            status_code=403,
            detail="You can only update your own bookings"
        )

    if update.status not in ["accepted", "rejected"]:
        raise HTTPException(
            status_code=400,
            detail="Status must be 'accepted' or 'rejected'"
        )

    booking.status = update.status

    db.commit()
    db.refresh(booking)

    return booking


# ---------------------------------------------------
# GET MY BOOKINGS (ALL ROLES AS CUSTOMERS)
# ---------------------------------------------------
@router.get("/bookings/my-bookings", response_model=list[BookingOut])
def get_my_bookings(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return db.query(Booking).filter(
        Booking.customer_id == current_user.id
    ).order_by(Booking.created_at.desc()).all()