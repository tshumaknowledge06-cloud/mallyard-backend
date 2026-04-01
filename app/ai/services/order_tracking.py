from sqlalchemy.orm import Session
from app.db.models.order import Order
from app.db.models.delivery_request import DeliveryRequest


def get_order_tracking_response(user_id: int, db: Session):

    order = (
        db.query(Order)
        .filter(Order.buyer_id == user_id)
        .order_by(Order.created_at.desc())
        .first()
    )

    if not order:
        return "You don't have any active orders yet."

    delivery = (
        db.query(DeliveryRequest)
        .filter(DeliveryRequest.order_id == order.id)
        .first()
    )

    if not delivery:
        return f"Your order #{order.id} is being prepared by the seller."

    status_map = {
        "assigned": "A delivery partner has been assigned.",
        "accepted": "The rider confirmed your delivery.",
        "picked_up": "Your order has been picked up.",
        "in_transit": "Your order is on the way 🚚.",
        "delivered": "Your order has been delivered ✅.",
    }

    message = status_map.get(
        delivery.status,
        f"Current status: {delivery.status}"
    )

    return f"Order #{order.id}: {message}"