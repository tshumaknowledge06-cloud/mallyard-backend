from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, aliased
from typing import List, Optional

from app.db.session import get_db
from app.db.models.delivery_request import DeliveryRequest
from app.db.models.delivery_match import DeliveryMatch
from app.db.models.order import Order
from app.db.models.listing import Listing
from app.db.models.merchant import Merchant
from app.db.models.user import User
from app.db.models.delivery_partner import DeliveryPartner


from app.schemas.delivery_request import (
    DeliveryRequestOut,
    PickupCreate,
)

from app.api.deps import get_current_user
from app.services.notifications import create_notification

router = APIRouter(
    prefix="/delivery-requests",
    tags=["Delivery Requests"]
)

# ----------------------------------------
# Seller submits pickup details
# ----------------------------------------
@router.post("/{order_id}/submit-pickup")
def submit_pickup_details(
    order_id: int,
    pickup_data: PickupCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):

    delivery_request = (
        db.query(DeliveryRequest)
        .filter(DeliveryRequest.order_id == order_id)
        .first()
    )

    if not delivery_request:
        raise HTTPException(status_code=404, detail="Delivery request not found")

    order = db.query(Order).filter(Order.id == order_id).first()

    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    # ✅ find merchant linked to seller user
    merchant = db.query(Merchant).filter(
        Merchant.user_id == current_user.id
    ).first()

    if not merchant:
        raise HTTPException(status_code=404, detail="Merchant profile not found")

    # ensure seller owns order
    if order.merchant_id != merchant.id:
        raise HTTPException(status_code=403, detail="Not your order")

    # seller submits pickup
    delivery_request.pickup_address = pickup_data.pickup_address
    delivery_request.seller_id = merchant.id
    delivery_request.status = "ready_for_dispatch"

    db.commit()
    db.refresh(delivery_request)

    return delivery_request


# ----------------------------------------
# Admin: View All Delivery Requests
# ----------------------------------------
@router.get("/", response_model=List[DeliveryRequestOut])
def get_all_delivery_requests(
    status: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):

    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Only admins allowed")

    # ✅ FIX: Join with Order to get delivery_price and estimated_delivery_days
    query = db.query(DeliveryRequest, Order).join(
        Order, Order.id == DeliveryRequest.order_id
    )

    if status:
        query = query.filter(DeliveryRequest.status == status)

    results = query.all()

    responses = []

    for delivery_request, order in results:
        responses.append({
            "id": delivery_request.id,
            "seller_id": delivery_request.seller_id,
            "order_id": order.id,
            "pickup_address": delivery_request.pickup_address,
            "dropoff_address": delivery_request.dropoff_address,
            "delivery_instructions": delivery_request.delivery_instructions,
            "status": delivery_request.status,
            "created_at": delivery_request.created_at,
            "delivery_price": order.delivery_price,
            "estimated_delivery_days": order.estimated_delivery_days,
            "distance_km": order.distance_km
        })

    return responses


# ----------------------------------------
# Admin completes delivery
# ----------------------------------------
@router.put("/{request_id}/complete")
def complete_delivery(
    request_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):

    # -----------------------------
    # Admin only
    # -----------------------------
    if current_user.role != "admin":
        raise HTTPException(
            status_code=403,
            detail="Only admins can complete delivery"
        )

    # ✅ FIX: Use filter().first() instead of .get()
    delivery_request = db.query(DeliveryRequest).filter(
        DeliveryRequest.id == request_id
    ).first()

    if not delivery_request:
        raise HTTPException(status_code=404, detail="Delivery request not found")

    # -----------------------------
    # Must already be delivered
    # -----------------------------
    if delivery_request.status != "delivered":
        raise HTTPException(
            status_code=400,
            detail="Delivery must be delivered first"
        )

    # -----------------------------
    # Find assigned partner
    # -----------------------------
    match = db.query(DeliveryMatch).filter(
        DeliveryMatch.delivery_request_id == delivery_request.id
    ).first()

    if not match:
        raise HTTPException(
            status_code=400,
            detail="No delivery partner assigned"
        )

    partner = db.query(DeliveryPartner).filter(
        DeliveryPartner.id == match.delivery_partner_id
    ).first()

    if not partner:
        raise HTTPException(
            status_code=404,
            detail="Delivery partner not found"
        )

    # -----------------------------
    # ✅ VERIFY DELIVERY
    # -----------------------------
    delivery_request.status = "verified"

    # ✅ UPDATE PARTNER STATS
    partner.completed_deliveries += 1

    db.commit()

    db.refresh(delivery_request)
    db.refresh(partner)

    return {
        "message": "Delivery verified and partner credited",
        "delivery_request_id": delivery_request.id,
        "partner_completed_deliveries": partner.completed_deliveries
    }


# ----------------------------------------
# Seller views own delivery requests
# ----------------------------------------

@router.get(
    "/seller",
    response_model=List[DeliveryRequestOut]
)
def get_seller_delivery_requests(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):

    if current_user.role != "seller":
        raise HTTPException(
            status_code=403,
            detail="Seller only"
        )

    merchant = db.query(Merchant).filter(
        Merchant.user_id == current_user.id
    ).first()

    if not merchant:
        return []

    results = (
        db.query(
            DeliveryRequest,
            Order,
            DeliveryPartner,
        )
        .join(
            Order,
            Order.id == DeliveryRequest.order_id
        )
        .outerjoin(
            DeliveryMatch,
            DeliveryMatch.delivery_request_id
            == DeliveryRequest.id
        )
        .outerjoin(
            DeliveryPartner,
            DeliveryPartner.id
            == DeliveryMatch.delivery_partner_id
        )
        .filter(
            DeliveryRequest.seller_id
            == merchant.id
        )
        .all()
    )

    responses = []

    for (
        delivery_request,
        order,
        driver,
    ) in results:

        responses.append({
            "id": delivery_request.id,

            "seller_id":
                delivery_request.seller_id,

            "order_id":
                order.id,

            "pickup_address":
                delivery_request.pickup_address,

            "dropoff_address":
                delivery_request.dropoff_address,

            "delivery_instructions":
                delivery_request.delivery_instructions,

            "status":
                delivery_request.status,

            "created_at":
                delivery_request.created_at,

            "delivery_price":
                order.delivery_price,

            "estimated_delivery_days":
                order.estimated_delivery_days,

            "distance_km":
                order.distance_km,

            # Driver
            "driver_name": (
                driver.full_name
                if driver
                else None
            ),

            "driver_phone": (
                driver.phone_number
                if driver
                else None
            ),
        })

    return responses


# ----------------------------------------
# Delivery Partner: View Assigned Deliveries
# ----------------------------------------
@router.get("/partner")
def get_partner_deliveries(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role != "delivery_partner":
        raise HTTPException(status_code=403, detail="Delivery partner only")

    delivery_partner = db.query(DeliveryPartner).filter(
        DeliveryPartner.user_id == current_user.id
    ).first()

    if not delivery_partner:
        raise HTTPException(
            status_code=404,
            detail="Delivery partner profile not found"
        )

    SellerUser = aliased(User)
    BuyerUser = aliased(User)

    results = (
        db.query(
            DeliveryRequest,
            Order,
            Listing,
            Merchant,
            SellerUser,
            BuyerUser
        )
        .join(
            DeliveryMatch,
            DeliveryMatch.delivery_request_id == DeliveryRequest.id
        )
        .join(Order, Order.id == DeliveryRequest.order_id)
        .join(Listing, Listing.id == Order.listing_id)
        .join(Merchant, Merchant.id == Order.merchant_id)
        .join(SellerUser, SellerUser.id == Merchant.user_id)
        .join(BuyerUser, BuyerUser.id == Order.buyer_id)
        .filter(
            DeliveryMatch.delivery_partner_id == delivery_partner.id
        )
        .all()
    )

    deliveries = []

    for (
        delivery_request,
        order,
        listing,
        merchant,
        seller_user,
        buyer
    ) in results:
        order_item = order.items[0] if order.items else None

        deliveries.append({
            "delivery_request_id": delivery_request.id,
            "order_id": order.id,
            "status": delivery_request.status,

            "listing_name": listing.name,
            "quantity": order_item.quantity if order_item else 0,

            "seller_name": merchant.business_name,
            "seller_phone": merchant.contact_phone,

            "customer_name": buyer.full_name,
            "customer_phone": order.customer_phone,

            "pickup_address": delivery_request.pickup_address,
            "dropoff_address": order.dropoff_address,
            "delivery_instructions": order.delivery_instructions,

            "delivery_price": order.delivery_price or 0,
            "estimated_delivery_days": order.estimated_delivery_days or 0,
            "distance_km": order.distance_km or 0,
        })

    return deliveries


# ----------------------------------------
# Delivery Partner: Update Delivery Status
# ----------------------------------------
@router.patch("/{delivery_request_id}/status")
def update_delivery_status(
    delivery_request_id: int,
    new_status: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):

    # Only delivery partners allowed
    if current_user.role != "delivery_partner":
        raise HTTPException(status_code=403, detail="Delivery partner only")

    delivery_partner = db.query(DeliveryPartner).filter(
        DeliveryPartner.user_id == current_user.id
    ).first()

    if not delivery_partner:
        raise HTTPException(
            status_code=404,
            detail="Delivery partner profile not found"
        )

    # Verify assignment
    # ✅ FIX: Use filter().first() instead of .get()
    match = db.query(DeliveryMatch).filter(
        DeliveryMatch.delivery_request_id == delivery_request_id,
        DeliveryMatch.delivery_partner_id == delivery_partner.id
    ).first()

    if not match:
        raise HTTPException(
            status_code=403,
            detail="Not assigned to this delivery"
        )

    # ✅ FIX: Use filter().first() instead of .get()
    delivery_request = db.query(DeliveryRequest).filter(
        DeliveryRequest.id == delivery_request_id
    ).first()

    if not delivery_request:
        raise HTTPException(
            status_code=404,
            detail="Delivery request not found"
        )

    # Get order for notifications
    order = db.query(Order).filter(Order.id == delivery_request.order_id).first()

    # Allowed transitions
    transitions = {
        "assigned": ["accepted", "rejected"],
        "accepted": ["picked_up"],
        "picked_up": ["in_transit"],
        "in_transit": ["delivered"],
    }

    current_status = delivery_request.status

    if current_status not in transitions:
        raise HTTPException(
            status_code=400,
            detail="Invalid current state"
        )

    if new_status not in transitions[current_status]:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid transition from {current_status} to {new_status}"
        )

    # Update state
    delivery_request.status = new_status

    # 🔔 NOTIFICATIONS for status changes
    if new_status == "picked_up" and order:
        create_notification(
            db=db,
            user_id=order.buyer_id,
            title="Package Picked Up",
            message="Your package has been picked up and is on its way.",
            notification_type="delivery",
            related_id=order.id,
        )

    if new_status == "delivered" and order:
        # Auto-complete order when delivered
        order.status = "completed"

        # Notify buyer
        create_notification(
            db=db,
            user_id=order.buyer_id,
            title="Order Delivered",
            message="Your order has been delivered successfully.",
            notification_type="delivery",
            related_id=order.id,
        )

        # Notify seller
        seller_user = db.query(User).filter(
            User.id == order.buyer_id
        ).first()  # Note: This should be the merchant's user_id, not buyer

        # ✅ Fix: Get merchant and notify seller
        merchant = db.query(Merchant).filter(
            Merchant.id == order.merchant_id
        ).first()

        if merchant:
            create_notification(
                db=db,
                user_id=merchant.user_id,
                title="Order Completed",
                message=f"Order #{order.id} has been completed.",
                notification_type="delivery",
                related_id=order.id,
            )

    db.commit()
    db.refresh(delivery_request)

    return {
        "message": "Delivery status updated",
        "status": delivery_request.status
    }