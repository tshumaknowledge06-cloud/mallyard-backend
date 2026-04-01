from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.core.jwt import decode_access_token
from app.db.models.user import User

# --------------------------------
# OAuth2 scheme
# --------------------------------
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


# --------------------------------
# Get current authenticated user
# --------------------------------
def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:

    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    payload = decode_access_token(token)

    if not payload or "sub" not in payload:
        raise credentials_exception

    user_id = payload.get("sub")

    user = db.query(User).filter(User.id == int(user_id)).first()

    if not user:
        raise credentials_exception

    if not getattr(user, "is_active", True):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user",
        )

    return user


# --------------------------------
# Role requirement dependency
# --------------------------------
def require_role(required_role: str):

    def role_checker(current_user: User = Depends(get_current_user)):

        # Convert Enum → string safely
        user_role = current_user.role

        if hasattr(user_role, "value"):
            user_role = user_role.value

        if user_role.lower() != required_role.lower():
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Operation requires {required_role} role. You are {user_role}",
            )

        return current_user

    return role_checker