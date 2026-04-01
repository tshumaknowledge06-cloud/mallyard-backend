import os
from sqlalchemy.orm import Session
from app.db.models.user import User, Role
from app.core.security import get_password_hash

def seed_users(db: Session):
    """
    Creates default production users if they don't exist.
    Safe to run multiple times.
    """

    users_to_create = [
        {
            "email": os.getenv("ADMIN_EMAIL"),
            "full_name": os.getenv("ADMIN_NAME", "System Admin"),
            "password": os.getenv("ADMIN_PASSWORD", "Admin@123456!"),
            "role": Role.admin,
        },
    ]

    for user_data in users_to_create:
        existing = db.query(User).filter(User.email == user_data["email"]).first()
        if existing:
            continue

        user = User(
            email=user_data["email"],
            full_name=user_data["full_name"],
            hashed_password=get_password_hash(user_data["password"]),
            role=user_data["role"],
            is_active=True,
            is_verified=True,
        )

        db.add(user)

    db.commit()