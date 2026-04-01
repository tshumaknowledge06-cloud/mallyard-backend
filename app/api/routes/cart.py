from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.api.deps_auth import get_current_user

from app.db.models.cart_item import CartItem
from app.db.models.listing import Listing
from app.db.models.order import Order
from app.db.models.order_item import OrderItem
from app.db.models.user import User
from app.db.models.merchant import Merchant
from app.schemas.cart import CartCheckoutRequest

router = APIRouter(prefix="/cart", tags=["Cart"])

# --------------------------------
# ADD ITEM TO CART
# --------------------------------
@router.post("/add")
def add_to_cart(
    listing_id: int,
    quantity: int = 1,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):

    listing = db.query(Listing).filter(Listing.id == listing_id).first()

    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")

    if listing.listing_type != "product":
        raise HTTPException(
            status_code=400,
            detail="Only product listings can be added to cart",
        )

    # ✅ GET MERCHANT
    merchant = db.query(Merchant).filter(
        Merchant.id == listing.merchant_id
    ).first()

    # 🚫 PREVENT SELF-CART
    if merchant and merchant.user_id == current_user.id:
        raise HTTPException(
            status_code=400,
            detail="You cannot add your own listing to cart"
        )

    existing = (
        db.query(CartItem)
        .filter(
            CartItem.user_id == current_user.id,
            CartItem.listing_id == listing_id,
        )
        .first()
    )

    if existing:
        existing.quantity += quantity
        db.commit()
        db.refresh(existing)
        return {"message": "Cart updated", "quantity": existing.quantity}

    cart_item = CartItem(
        user_id=current_user.id,
        listing_id=listing.id,
        merchant_id=listing.merchant_id,
        quantity=quantity,
    )

    db.add(cart_item)
    db.commit()
    db.refresh(cart_item)

    return {"message": "Item added to cart"}


# --------------------------------
# CHECKOUT (PER MERCHANT)
# --------------------------------
@router.post("/checkout/{merchant_id}")
def checkout_cart(
    merchant_id: int,
    payload: CartCheckoutRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):

    cart_items = (
        db.query(CartItem)
        .filter(
            CartItem.user_id == current_user.id,
            CartItem.merchant_id == merchant_id
        )
        .all()
    )

    if not cart_items:
        raise HTTPException(status_code=400, detail="Cart is empty")

    # ✅ Validate delivery logic
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

    created_orders = []

    for item in cart_items:

        listing = db.query(Listing).filter(
            Listing.id == item.listing_id,
            Listing.is_active == True
        ).first()

        if not listing:
            continue

        merchant = db.query(Merchant).filter(
            Merchant.id == listing.merchant_id
        ).first()

        # 🚫 PREVENT SELF-CHECKOUT (🔥 CRITICAL SAFETY)
        if merchant and merchant.user_id == current_user.id:
            raise HTTPException(
                status_code=400,
                detail=f"You cannot order your own listing ({listing.name})"
            )

        # ✅ Stock check
        if listing.stock_quantity is not None and item.quantity > listing.stock_quantity:
            raise HTTPException(
                status_code=400,
                detail=f"Insufficient stock for {listing.name}"
            )

        # ✅ CREATE ORDER
        order = Order(
            buyer_id=current_user.id,
            merchant_id=merchant.id,
            listing_id=listing.id,
            status="pending",
            delivery_method=payload.delivery_method,
            dropoff_address=payload.dropoff_address,
            delivery_instructions=payload.delivery_instructions,
            customer_phone=payload.customer_phone,
        )

        db.add(order)
        db.flush()

        # ✅ ORDER ITEM
        order_item = OrderItem(
            order_id=order.id,
            listing_id=listing.id,
            quantity=item.quantity,
            price=listing.price
        )

        db.add(order_item)

        # ✅ Reduce stock
        if listing.stock_quantity is not None:
            listing.stock_quantity -= item.quantity

        created_orders.append(order.id)

        # ✅ Remove from cart
        db.delete(item)

    db.commit()

    return {
        "message": "Orders created successfully",
        "order_ids": created_orders
    }


# --------------------------------
# GET CART (GROUPED BY MERCHANT)
# --------------------------------
@router.get("")
def get_cart(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):

    items = (
        db.query(CartItem)
        .filter(CartItem.user_id == current_user.id)
        .all()
    )

    cart = {}

    for item in items:

        merchant_id = item.merchant_id

        if merchant_id not in cart:
            cart[merchant_id] = {
                "merchant_id": merchant_id,
                "items": [],
                "total": 0
            }

        price = item.listing.price
        subtotal = price * item.quantity

        cart[merchant_id]["items"].append({
            "cart_item_id": item.id,
            "listing_id": item.listing_id,
            "name": item.listing.name,
            "price": price,
            "quantity": item.quantity,
            "subtotal": subtotal
        })

        cart[merchant_id]["total"] += subtotal

    return {"merchant_carts": list(cart.values())}


# --------------------------------
# REMOVE ITEM
# --------------------------------
@router.delete("/remove/{cart_item_id}")
def remove_cart_item(
    cart_item_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):

    item = (
        db.query(CartItem)
        .filter(
            CartItem.id == cart_item_id,
            CartItem.user_id == current_user.id
        )
        .first()
    )

    if not item:
        raise HTTPException(status_code=404, detail="Cart item not found")

    db.delete(item)
    db.commit()

    return {"message": "Item removed from cart"}


