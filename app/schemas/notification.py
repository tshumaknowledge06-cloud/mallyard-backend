from datetime import datetime
from pydantic import BaseModel


# ==========================================
# Notification Response
# ==========================================

class NotificationOut(BaseModel):
    id: int

    title: str
    message: str

    notification_type: str

    related_id: int | None = None

    is_read: bool

    created_at: datetime

    class Config:
        from_attributes = True


# ==========================================
# Mark Notification Read
# ==========================================

class NotificationReadUpdate(BaseModel):
    is_read: bool = True