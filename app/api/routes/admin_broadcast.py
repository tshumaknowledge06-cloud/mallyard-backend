from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_role
from app.db.models.user import User
from app.schemas.admin_broadcast import (
    BroadcastRequest,
    BroadcastResponse,
)
from app.core.email import send_email
from app.core.broadcast_email import build_broadcast_email


router = APIRouter(
    prefix="/admin/broadcast",
    tags=["Admin Broadcast"],
)


# =====================================================
# ADMIN BROADCAST
# =====================================================

@router.post(
    "",
    response_model=BroadcastResponse,
)
def send_broadcast(
    request: BroadcastRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):

    # -------------------------------------------------
    # Determine recipients
    # -------------------------------------------------

    query = db.query(User).filter(
        User.is_active == True,
        User.email.isnot(None),
    )

    if request.audience == "merchants":

        query = query.filter(
            User.role == "seller"
        )

    elif request.audience == "delivery_partners":

        query = query.filter(
            User.role == "delivery_partner"
        )

    elif request.audience == "customers":

        query = query.filter(
            User.role == "customer"
        )

    users = query.all()

    targeted = len(users)

    # -------------------------------------------------
    # Build branded email
    # -------------------------------------------------

    html_body = build_broadcast_email(
        subject=request.subject,
        message=request.message,
    )

    # -------------------------------------------------
    # Send emails
    # -------------------------------------------------

    sent = 0
    failed = 0

    for user in users:

        try:

            send_email(
                to=user.email,
                subject=request.subject,
                body=html_body,
            )

            sent += 1

        except Exception as exc:

            failed += 1

            print(
                f"❌ Broadcast failed for "
                f"{user.email}: {exc}"
            )

    # -------------------------------------------------
    # Response
    # -------------------------------------------------

    return BroadcastResponse(
        message="Broadcast processed successfully.",
        audience=request.audience,
        targeted=targeted,
        sent=sent,
        failed=failed,
    )