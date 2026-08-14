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
from app.services.delivery_pricing import (
    get_intercity_price,
    handle_missing_route
)
from app.services.delivery_pricing import get_intracity_price
from app.services.delivery_pricing import suggest_route_pricing
from app.services.notifications import create_notification

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

    # ✅ GET MERCHANT
    merchant = db.query(Merchant).filter(
        Merchant.id == listing.merchant_id
    ).first()

    if not merchant:
        raise HTTPException(status_code=404, detail="Merchant not found")

    # 🚫 PREVENT SELF-ORDERING
    if merchant.user_id == current_user.id:
        raise HTTPException(
            status_code=400,
            detail="You cannot order your own listing"
        )

    # 🔥 STEP 1: RESOLVE FINAL 
    final_address = payload.dropoff_address or current_user.default_address
    final_phone = payload.customer_phone or current_user.phone_number

    # 🔥 STEP 2: VALIDATE using resolved values
    if payload.delivery_method == "delivery" and not final_address:
        raise HTTPException(
            status_code=400,
            detail="Dropoff address is required for delivery"
        )

    if not final_phone:
        raise HTTPException(
            status_code=400,
            detail="Customer phone is required"
        )

    # 🔥 STEP 3: CREATE ORDER using resolved values
    order = Order(
        buyer_id=current_user.id,
        merchant_id=merchant.id,
        listing_id=listing.id,
        order_specifications=payload.order_specifications,
        delivery_method=payload.delivery_method,
        dropoff_address=final_address,
        delivery_instructions=payload.delivery_instructions,
        customer_phone=final_phone,
        status="pending"
    )

    db.add(order)
    db.flush()

    order_item = OrderItem(
        order_id=order.id,
        listing_id=listing.id,
        quantity=payload.quantity,
        price=listing.price,
        total_price=listing.price * payload.quantity
    )

    db.add(order_item)

    # =====================================================
    # 🚀 DELIVERY PRICING ENGINE (PRODUCTION SAFE)
    # =====================================================
    if payload.delivery_method == "delivery":

        customer_city_id = current_user.city_id
        package_type = "medium"

        # 🔥 GLOBAL FALLBACK (never zero)
        BASE_PRICE = 2.50
        PRICE_PER_KM = 0.5
        DEFAULT_DISTANCE_KM = 2

        order.distance_km = DEFAULT_DISTANCE_KM
        order.delivery_price = BASE_PRICE + (PRICE_PER_KM * DEFAULT_DISTANCE_KM)
        order.estimated_delivery_days = 1
        order.is_estimated = True

        if merchant.city_id and customer_city_id:

            # 🟢 SAME CITY → INTRA-CITY
            if merchant.city_id == customer_city_id:

                price = get_intracity_price(merchant, current_user)

                if price:
                    order.delivery_price = price
                    order.distance_km = 5  # avg intra-city
                    order.estimated_delivery_days = 1
                    order.is_estimated = False

            # 🔵 DIFFERENT CITY → INTER-CITY
            else:

                result = get_intercity_price(
                    db,
                    merchant.city_id,
                    customer_city_id,
                    package_type
                )

                if result:
                    price, eta_min, eta_max = result

                    order.delivery_price = price
                    order.estimated_delivery_days = eta_max
                    order.is_estimated = False

                    pricing = suggest_route_pricing(
                        db,
                        merchant.city,
                        current_user.city
                    )

                    if pricing:
                        order.distance_km = pricing["distance_km"]

                else:
                    # 🔥 FALLBACK for missing routes
                    handle_missing_route(
                        db,
                        merchant.city_id,
                        customer_city_id
                    )

    # =====================================================
    # 📦 STOCK REDUCTION
    # =====================================================
    if listing.stock_quantity is not None:
        listing.stock_quantity -= payload.quantity

    try:
        db.commit()
        db.refresh(order)
    except Exception:
        db.rollback()
        raise HTTPException(status_code=500, detail="Order creation failed")

    # =====================================================
    # 📧 NON-BLOCKING EMAIL
    # =====================================================
    seller_user = db.query(User).filter(
        User.id == merchant.user_id
    ).first()

    if seller_user:
        try:
            send_email(
                to=seller_user.email,
                subject="New Order Pending Confirmation",
                body=f"""
New Order Alert 🚀

Order ID: {order.id}

A customer has placed an order in your store.

Speed is everything — confirm it quickly and keep the experience premium.

👉 Access your dashboard:
https://themallyard.com/login/merchant

Build trust. Close fast.

— The Mallyard
"""
            )
        except Exception:
            pass

    # 🔔 NOTIFICATION: New Order to Merchant
    create_notification(
        db=db,
        user_id=merchant.user_id,
        title="New Order",
        message=f"You received Order #{order.id}.",
        notification_type="order",
        related_id=order.id,
    )

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

    # 🔔 NOTIFICATION: Order Confirmed or Rejected
    if new_status == "accepted":
        create_notification(
            db=db,
            user_id=order.buyer_id,
            title="Order Confirmed",
            message="Your order has been confirmed by the seller.",
            notification_type="order",
            related_id=order.id,
        )
    elif new_status == "rejected":
        create_notification(
            db=db,
            user_id=order.buyer_id,
            title="Order Cancelled",
            message="Unfortunately the seller declined your order.",
            notification_type="order",
            related_id=order.id,
        )

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
    orders = db.query(Order).filter(
        Order.buyer_id == current_user.id
    ).order_by(Order.id.desc()).all()
    
    # 🔥 ENRICH WITH ORDER ITEM DATA
    result = []
    
    for order in orders:
        # Get the order item for this order
        item = db.query(OrderItem).filter(
            OrderItem.order_id == order.id
        ).first()
        
        # Get the listing for media
        listing = db.query(Listing).filter(
            Listing.id == order.listing_id
        ).first()
        
        result.append({
            "id": order.id,
            "listing_name": listing.name if listing else None,
            "buyer_id": order.buyer_id,
            "merchant_id": order.merchant_id,
            "listing_id": order.listing_id,
            "status": order.status,
            "order_specifications": order.order_specifications,
            "delivery_method": order.delivery_method,
            "dropoff_address": order.dropoff_address,
            "delivery_instructions": order.delivery_instructions,
            "customer_phone": order.customer_phone,
            "created_at": order.created_at,
            "quantity": item.quantity if item else 1,
            "total_price": (item.price * item.quantity) if item else None,
            "delivery_price": order.delivery_price,
            "estimated_delivery_days": order.estimated_delivery_days,
            "image_urls": listing.image_urls if listing else None,
            "video_url": listing.video_url if listing else None,
        })
    
    return result