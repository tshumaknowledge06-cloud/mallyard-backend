from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.db.models.delivery_request import DeliveryRequest
from app.db.models.delivery_partner import DeliveryPartner
from app.db.models.delivery_match import DeliveryMatch
from app.schemas.delivery_match import (
    DeliveryMatchCreate,
    DeliveryMatchOut,
)
from app.api.deps import get_current_user
from app.db.models.user import User

router = APIRouter(
    prefix="/delivery-matches",
    tags=["Delivery Matching"]
)


# ---------------------------------------------------
# Assign Delivery Partner (ADMIN ONLY)
# ---------------------------------------------------
@router.post(
    "/assign",
    response_model=DeliveryMatchOut,
    status_code=status.HTTP_201_CREATED
)
def assign_delivery_partner(
    match_in: DeliveryMatchCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):

    # ✅ Admin only
    if current_user.role != "admin":
        raise HTTPException(
            status_code=403,
            detail="Only admins can assign delivery partners"
        )

    # ---------------------------------------------------
    # Get delivery request
    # ---------------------------------------------------
    delivery_request = db.query(DeliveryRequest).filter(
        DeliveryRequest.id == match_in.delivery_request_id
    ).first()

    if not delivery_request:
        raise HTTPException(
            status_code=404,
            detail="Delivery request not found"
        )

    # ---------------------------------------------------
    # Validate workflow state
    # Must be ready_for_dispatch before assignment
    # ---------------------------------------------------
    if delivery_request.status != "ready_for_dispatch":
        raise HTTPException(
            status_code=400,
            detail="Delivery not ready for assignment"
        )

    # ---------------------------------------------------
    # Prevent duplicate assignment
    # ---------------------------------------------------
    existing_match = db.query(DeliveryMatch).filter(
        DeliveryMatch.delivery_request_id == delivery_request.id
    ).first()

    if existing_match:
        raise HTTPException(
            status_code=400,
            detail="Delivery already assigned"
        )

    # ---------------------------------------------------
    # Validate delivery partner exists
    # ---------------------------------------------------
    delivery_partner = db.query(DeliveryPartner).filter(
        DeliveryPartner.id == match_in.delivery_partner_id
    ).first()

    if not delivery_partner:
        raise HTTPException(
            status_code=404,
            detail="Delivery partner not found"
        )

    # ---------------------------------------------------
    # Create match
    # ---------------------------------------------------
    match = DeliveryMatch(
        delivery_request_id=delivery_request.id,
        delivery_partner_id=delivery_partner.id
    )

    # Update delivery status
    delivery_request.status = "assigned"

    db.add(match)
    db.commit()
    db.refresh(match)

    return match