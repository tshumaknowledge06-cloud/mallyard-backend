from sqlalchemy.orm import Session

from app.db.models.user import User
from app.core.security import hash_password


def create_user(
    db: Session,
    *,
    email: str,
    password: str,
    role: str = "user"
) -> User:
    user = User(
        email=email,
        hashed_password=hash_password(password),
        role=role,
        is_active=True,
        is_verified=False,
    )

    db.add(user)
    db.commit()
    db.refresh(user)
    return user
