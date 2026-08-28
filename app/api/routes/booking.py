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
from app.services.notifications import create_notification

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

Don't lose the moment — fast response builds trust and wins repeat business.

👉 Open your dashboard:
https://themallyard.com/login/merchant

Stay sharp. Stay winning.

— The Mallyard
"""
            )
        except Exception:
            pass

    # 🔔 NOTIFICATION: New Booking to Seller
    create_notification(
        db=db,
        user_id=merchant.user_id,
        title="New Booking",
        message="A customer requested a booking.",
        notification_type="booking",
        related_id=new_booking.id,
    )

    # ✅ RETURN ENRICHED RESPONSE with all required fields
    return {
        "id": new_booking.id,
        "listing_id": new_booking.listing_id,
        "customer_id": new_booking.customer_id,
        "seller_id": new_booking.seller_id,
        "description": new_booking.description,
        "contact_number": new_booking.contact_number,
        "preferred_time": new_booking.preferred_time,
        "status": new_booking.status,
        "created_at": new_booking.created_at,
        # 🔥 ENRICHED FIELDS from listing and merchant
        "listing_name": listing.name,
        "price": listing.price,
        "currency": listing.currency,
        "business_name": merchant.business_name,
        "image_urls": listing.image_urls or [],
    }


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

    # 🔔 NOTIFICATION: Booking Accepted or Rejected
    if update.status == "accepted":
        create_notification(
            db=db,
            user_id=booking.customer_id,
            title="Booking Accepted",
            message="Your booking has been accepted.",
            notification_type="booking",
            related_id=booking.id,
        )
    elif update.status == "rejected":
        create_notification(
            db=db,
            user_id=booking.customer_id,
            title="Booking Rejected",
            message="Your booking request was declined.",
            notification_type="booking",
            related_id=booking.id,
        )

    return booking


# ---------------------------------------------------
# GET MY BOOKINGS (ALL ROLES AS CUSTOMERS)
# ---------------------------------------------------

@router.get(
    "/bookings/my-bookings",
    response_model=list[BookingOut]
)
def get_my_bookings(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    bookings = (
        db.query(Booking)
        .filter(
            Booking.customer_id == current_user.id
        )
        .order_by(
            Booking.created_at.desc()
        )
        .all()
    )

    result = []

    for booking in bookings:
        listing = booking.listing

        if not listing:
            continue

        merchant = listing.merchant

        if not merchant:
            continue

        result.append(
            BookingOut(
                id=booking.id,
                listing_id=booking.listing_id,
                customer_id=booking.customer_id,
                seller_id=booking.seller_id,

                description=booking.description,
                contact_number=booking.contact_number,
                preferred_time=booking.preferred_time,

                status=booking.status,
                created_at=booking.created_at,

                listing_name=listing.name,
                image_urls=listing.image_urls or [],
                price=listing.price,
                currency=listing.currency,

                business_name=merchant.business_name,
            )
        )

    return result