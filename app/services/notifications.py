from typing import Optional

from sqlalchemy.orm import Session

from app.db.models.notification import Notification


def create_notification(
    db: Session,
    *,
    user_id: int,
    title: str,
    message: str,
    notification_type: str,
    related_id: Optional[int] = None,
) -> Notification:
    """
    Creates an in-app notification.
    """

    notification = Notification(
        user_id=user_id,
        title=title,
        message=message,
        notification_type=notification_type,
        related_id=related_id,
    )

    db.add(notification)
    db.commit()
    db.refresh(notification)

    return notification