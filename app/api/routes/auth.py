from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from datetime import timedelta

from app.schemas.auth import UserCreate, Token
from app.db.models.user import User
from app.api.deps import get_db
from app.core.security import (
    hash_password,
    verify_password,
    create_access_token,   # ✅ IMPORT FIX
)
from app.core.config import settings
from app.schemas.auth import GoogleAuthSchema
from slowapi.util import get_remote_address
from fastapi import Request
from slowapi import Limiter
import time

router = APIRouter(
    prefix="/auth",
    tags=["Auth"],
)

limiter = Limiter(key_func=get_remote_address)

# -------------------------
# Register
# -------------------------
@router.post("/register", status_code=status.HTTP_201_CREATED)
def register(user_in: UserCreate, db: Session = Depends(get_db)):

    existing_user = db.query(User).filter(User.email == user_in.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )

    hashed_password = hash_password(user_in.password)

    new_user = User(
        email=user_in.email,
        full_name=user_in.full_name,
        hashed_password=hashed_password,
        role = user_in.role if user_in.role in ["customer", "seller"] else "customer"
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return {
        "id": new_user.id,
        "email": new_user.email,
        "full_name": new_user.full_name,
        "role": new_user.role
    }


# -------------------------
# Login
# -------------------------
@router.post("/login", response_model=Token)
@limiter.limit("5/minute")
def login(
    request: Request,   
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.email == form_data.username).first()

    # 🔐 Brute-force protection
    if not user or not verify_password(form_data.password, user.hashed_password):
        time.sleep(1)  # slows down attackers
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    access_token_expires = timedelta(
        minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
    )

    access_token = create_access_token(
        subject=str(user.id),
        expires_delta=access_token_expires,
    )

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "role": user.role
    }


@router.post("/google")
def google_auth(payload: GoogleAuthSchema, db: Session = Depends(get_db)):

    user = db.query(User).filter(User.email == payload.email).first()

    if not user:
        user = User(
            email=payload.email,
            full_name=payload.full_name,
            role=payload.role,
            hashed_password=None  # ✅ No password
        )
        db.add(user)
        db.commit()
        db.refresh(user)

    return {
        "id": user.id,
        "email": user.email,
        "full_name": user.full_name,
        "role": user.role
    }
