from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.db.models.order import Order
from app.db.models.listing import Listing
from app.db.models.user import User
from app.db.models.merchant import Merchant

from app.schemas.order import OrderCreate, OrderOut, OrderStatusUpdate
from app.db.models.delivery_request import DeliveryRequest
from app.db.models.order_item import OrderItem
from app.api.deps import get_current_user
from app.core.email import send_email
from app.services.order_state_machine import validate_transition

router = APIRouter(
    prefix="/orders",
    tags=["Orders"]
)

# =========================================================
# CREATE ORDER (Buyer / Seller / Delivery Partner)
# =========================================================
@router.post("/", response_model=OrderOut)
def create_order(
    payload: OrderCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):

    listing = db.query(Listing).filter(
        Listing.id == payload.listing_id,
        Listing.is_active == True
    ).first()

    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")

    if payload.quantity <= 0:
        raise HTTPException(status_code=400, detail="Invalid quantity")

    if listing.stock_quantity is not None and payload.quantity > listing.stock_quantity:
        raise HTTPException(status_code=400, detail="Insufficient stock")

    # ✅ DELIVERY VALIDATION
    if payload.delivery_method == "delivery" and not payload.dropoff_address:
        raise HTTPException(
            status_code=400,
            detail="Dropoff address is required for delivery"
        )

    if not payload.customer_phone:
        raise HTTPException(
            status_code=400,
            detail="Customer phone is required"
        )

    # ✅ GET MERCHANT
    merchant = db.query(Merchant).filter(
        Merchant.id == listing.merchant_id
    ).first()

    if not merchant:
        raise HTTPException(status_code=404, detail="Merchant not found")

    # 🚫 PREVENT SELF-ORDERING (🔥 CORE FIX)
    if merchant.user_id == current_user.id:
        raise HTTPException(
            status_code=400,
            detail="You cannot order your own listing"
        )

    # ✅ CREATE ORDER
    order = Order(
        buyer_id=current_user.id,
        merchant_id=merchant.id,
        listing_id=listing.id,
        delivery_method=payload.delivery_method,
        dropoff_address=payload.dropoff_address,
        delivery_instructions=payload.delivery_instructions,
        customer_phone=payload.customer_phone,
        status="pending"
    )

    db.add(order)
    db.flush()

    order_item = OrderItem(
        order_id=order.id,
        listing_id=listing.id,
        quantity=payload.quantity,
        price=listing.price,
        total_price = listing.price * payload.quantity
    )

    db.add(order_item)

    # ✅ STOCK REDUCTION
    if listing.stock_quantity is not None:
        listing.stock_quantity -= payload.quantity

    try:
        db.commit()
        db.refresh(order)
    except Exception:
        db.rollback()
        raise HTTPException(status_code=500, detail="Order creation failed")

    # ✅ NON-BLOCKING EMAIL
    seller_user = db.query(User).filter(
        User.id == merchant.user_id
    ).first()

    if seller_user:
        try:
            send_email(
                to=seller_user.email,
                subject="New Order Pending Confirmation",
                body=f"New order received. Order ID: {order.id}. Kindly access your dasboard to review the order details"
            )
        except Exception:
            pass

    return order


# =========================================================
# SELLER STATUS UPDATE (accepted → preparing → packaged)
# =========================================================
@router.patch("/{order_id}/status", response_model=OrderOut)
def update_order_status(
    order_id: int,
    status_update: OrderStatusUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):

    order = db.query(Order).filter(Order.id == order_id).first()

    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    new_status = status_update.status

    # Seller-only states
    seller_states = ["accepted", "rejected", "preparing", "packaged"]

    merchant = db.query(Merchant).filter(
        Merchant.user_id == current_user.id
    ).first()

    if not merchant or merchant.id != order.merchant_id:
        raise HTTPException(status_code=403, detail="Seller only action")

    validate_transition(order.status, new_status)
    order.status = new_status

    db.commit()
    db.refresh(order)

    # =====================================================
    # AUTO DELIVERY FLOW TRIGGER
    # =====================================================
    if new_status == "packaged":

        # ONSITE
        if order.delivery_method == "onsite":
            order.status = "completed"
            db.commit()
            db.refresh(order)
            return order

        # DELIVERY
        if order.delivery_method == "delivery":

            existing_request = db.query(DeliveryRequest).filter(
                DeliveryRequest.order_id == order.id
            ).first()

            if not existing_request:
                delivery_request = DeliveryRequest(
                    order_id=order.id,
                    seller_id=order.merchant_id,
                    dropoff_address=order.dropoff_address,
                    delivery_instructions=order.delivery_instructions,
                    status="pending_assignment"
                )
                db.add(delivery_request)

            order.status = "delivery_requested"

            db.commit()
            db.refresh(order)

    return order


# =========================================================
# GET ORDERS
# =========================================================
@router.get("/", response_model=list[OrderOut])
def get_orders(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):

    # -----------------------------------------
    # GET BASE ORDERS (UNCHANGED LOGIC)
    # -----------------------------------------
    if current_user.role == "customer":
        orders = db.query(Order).filter(
            Order.buyer_id == current_user.id
        ).all()

    elif current_user.role == "seller":
        merchant = db.query(Merchant).filter(
            Merchant.user_id == current_user.id
        ).first()

        if not merchant:
            return []

        orders = db.query(Order).filter(
            Order.merchant_id == merchant.id
        ).all()

    elif current_user.role == "delivery_partner":
        orders = db.query(Order).filter(
            Order.buyer_id == current_user.id
        ).all()

    elif current_user.role == "admin":
        orders = db.query(Order).all()

    else:
        raise HTTPException(status_code=403, detail="Unauthorized role")

    # -----------------------------------------
    # 🔥 ENRICH WITH ORDER ITEM DATA
    # -----------------------------------------
    result = []

    for order in orders:
        item = db.query(OrderItem).filter(
            OrderItem.order_id == order.id
        ).first()

        result.append({
            **order.__dict__,
            "quantity": item.quantity if item else 1,
            "total_price": (item.price * item.quantity) if item else None
        })

    return result


# =========================================================
# GET MY PURCHASES (ALL ROLES AS BUYERS)
# =========================================================
@router.get("/my-purchases", response_model=list[OrderOut])
def get_my_purchases(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return db.query(Order).filter(
        Order.buyer_id == current_user.id
    ).order_by(Order.id.desc()).all()