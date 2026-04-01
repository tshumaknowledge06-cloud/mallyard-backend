from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

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
        raise HTTPException(404, "Delivery request not found")

    order = db.query(Order).filter(Order.id == order_id).first()

    if not order:
        raise HTTPException(404, "Order not found")

    # ✅ find merchant linked to seller user
    merchant = db.query(Merchant).filter(
        Merchant.user_id == current_user.id
    ).first()

    if not merchant:
        raise HTTPException(404, "Merchant profile not found")

    # ensure seller owns order
    if order.merchant_id != merchant.id:
        raise HTTPException(403, "Not your order")

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
from typing import Optional

@router.get("/", response_model=list[DeliveryRequestOut])
def get_all_delivery_requests(
    status: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):

    if current_user.role != "admin":
        raise HTTPException(403, "Only admins allowed")

    query = db.query(DeliveryRequest)

    if status:
        query = query.filter(DeliveryRequest.status == status)

    return query.all()


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

    delivery_request = db.query(DeliveryRequest).filter(
        DeliveryRequest.id == request_id
    ).first()

    if not delivery_request:
        raise HTTPException(404, "Delivery request not found")

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
@router.get("/seller", response_model=list[DeliveryRequestOut])
def get_seller_delivery_requests(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):

    if current_user.role != "seller":
        raise HTTPException(403, "Seller only")

    merchant = db.query(Merchant).filter(
        Merchant.user_id == current_user.id
    ).first()

    if not merchant:
        return []

    return (
        db.query(DeliveryRequest)
        .join(Order, DeliveryRequest.order_id == Order.id)
        .filter(Order.merchant_id == merchant.id)
        .all()
    )


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

    from sqlalchemy.orm import aliased

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
    match = db.query(DeliveryMatch).filter(
        DeliveryMatch.delivery_request_id == delivery_request_id,
        DeliveryMatch.delivery_partner_id == delivery_partner.id
    ).first()

    if not match:
        raise HTTPException(
            status_code=403,
            detail="Not assigned to this delivery"
        )

    delivery_request = db.query(DeliveryRequest).get(delivery_request_id)

    if not delivery_request:
        raise HTTPException(
            status_code=404,
            detail="Delivery request not found"
        )

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

    # Auto-complete order when delivered
    if new_status == "delivered":
        order = db.query(Order).get(delivery_request.order_id)
        if order:
            order.status = "completed"

    db.commit()
    db.refresh(delivery_request)

    return {
        "message": "Delivery status updated",
        "status": delivery_request.status
    }
