from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import distinct, func
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_current_user
from app.db.models.user import User
from app.db.models.order import Order
from app.db.models.delivery_request import DeliveryRequest
from app.db.models.delivery_match import DeliveryMatch

router = APIRouter(
    prefix="/admin/analytics",
    tags=["Admin Analytics"],
)


@router.get("")
def get_admin_analytics(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin only")

    now = datetime.now(timezone.utc)
    thirty_days_ago = now - timedelta(days=30)
    eight_weeks_ago = now - timedelta(weeks=8)

    # ----------------------------------------
    # Active customers
    # Distinct buyers who placed orders in last 30 days
    # ----------------------------------------
    active_customers = (
        db.query(func.count(distinct(Order.buyer_id)))
        .filter(Order.created_at >= thirty_days_ago)
        .scalar()
    ) or 0

    # ----------------------------------------
    # Orders per week
    # Last 8 weeks grouped by PostgreSQL week
    # ----------------------------------------
    weekly_rows = (
        db.query(
            func.date_trunc("week", Order.created_at).label("week_start"),
            func.count(Order.id).label("orders"),
        )
        .filter(Order.created_at >= eight_weeks_ago)
        .group_by(func.date_trunc("week", Order.created_at))
        .order_by(func.date_trunc("week", Order.created_at))
        .all()
    )

    orders_per_week = [
        {
            "week_start": row.week_start.date().isoformat(),
            "orders": row.orders,
        }
        for row in weekly_rows
    ]

    # ----------------------------------------
    # Match success rate
    # Matched requests / total requests
    # ----------------------------------------
    total_delivery_requests = (
        db.query(func.count(DeliveryRequest.id)).scalar()
    ) or 0

    matched_delivery_requests = (
        db.query(func.count(distinct(DeliveryMatch.delivery_request_id)))
        .scalar()
    ) or 0

    match_success_rate = (
        round((matched_delivery_requests / total_delivery_requests) * 100, 2)
        if total_delivery_requests > 0
        else 0.0
    )

    return {
        "active_customers": active_customers,
        "orders_per_week": orders_per_week,
        "match_success_rate": match_success_rate,
    }