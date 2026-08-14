from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from datetime import timedelta

from app.schemas.auth import UserCreate, UserUpdate, Token
from app.db.models.user import User
from app.db.models.city_request import CityRequest 
from app.api.deps import get_db
from app.services.city_service import resolve_city
from app.api.deps import get_current_user
from app.core.security import (
    hash_password,
    verify_password,
    create_access_token,  
)
from app.core.config import settings
from app.schemas.auth import GoogleAuthSchema, Token
from app.core.security import create_access_token, verify_google_token, hash_password
from slowapi.util import get_remote_address
from fastapi import Request
from slowapi import Limiter
from app.db.models.user_role import UserRole
import time

from app.core.email import send_email
from datetime import datetime, timedelta, timezone
import secrets

from app.services.notifications import create_notification
from app.core.email_templates import password_reset_email
from app.db.models.password_reset_token import PasswordResetToken
from app.schemas.password_reset import (
    ForgotPasswordRequest,
    ResetPasswordRequest,
    PasswordResetResponse,
)

router = APIRouter(
    prefix="/auth",
    tags=["Auth"],
)

limiter = Limiter(key_func=get_remote_address)

# -------------------------
# Register
# -------------------------
@router.post("/register", status_code=status.HTTP_201_CREATED)
def register(
    user_in: UserCreate,
    db: Session = Depends(get_db)
):
    existing_user = (
        db.query(User)
        .filter(User.email == user_in.email)
        .first()
    )

    if existing_user:
        # 🔐 Verify password for existing account
        if not verify_password(
            user_in.password,
            existing_user.hashed_password,
        ):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect password for this account.",
            )

        existing_role = next(
            (
                r
                for r in existing_user.roles
                if r.role == user_in.role
            ),
            None,
        )

        if existing_role:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="You already have this workspace."
            )

        # 🔥 UPDATE EMPTY PROFILE FIELDS
        if (
            (existing_user.full_name is None or existing_user.full_name.strip() == "")
            and user_in.full_name
        ):
            existing_user.full_name = user_in.full_name

        if existing_user.phone_number is None and user_in.phone_number:
            existing_user.phone_number = user_in.phone_number

        if existing_user.default_address is None and user_in.default_address:
            existing_user.default_address = user_in.default_address

        # 🔥 NORMALIZE INPUT FOR CITY
        city_name = user_in.city_name.strip().lower() if user_in.city_name else None
        city_id = None

        if city_name:
            city_id = resolve_city(db, city_name)

            if not city_id:
                # 🔥 UPSERT CITY REQUEST (normalized)
                existing_request = db.query(CityRequest).filter(
                    CityRequest.name == city_name
                ).first()

                if existing_request:
                    existing_request.request_count += 1
                else:
                    new_request = CityRequest(name=city_name)
                    db.add(new_request)

        if existing_user.city_id is None and city_id:
            existing_user.city_id = city_id

        # Existing user - just add new role
        db.add(
            UserRole(
                user_id=existing_user.id,
                role=user_in.role,
            )
        )
        db.commit()

        return {
            "id": existing_user.id,
            "email": existing_user.email,
            "full_name": existing_user.full_name,
            "role": user_in.role,
            "city_supported": True if existing_user.city_id else False,
        }

    # 🔥 NORMALIZE INPUT
    city_name = user_in.city_name.strip().lower() if user_in.city_name else None

    # 🔥 RESOLVE CITY 
    city_id = None

    if city_name:
        city_id = resolve_city(db, city_name)

        if not city_id:
            # 🔥 UPSERT CITY REQUEST (normalized)
            existing_request = db.query(CityRequest).filter(
                CityRequest.name == city_name
            ).first()

            if existing_request:
                existing_request.request_count += 1
            else:
                new_request = CityRequest(name=city_name)
                db.add(new_request)

    hashed_password = hash_password(user_in.password)

    new_user = User(
        email=user_in.email,
        full_name=user_in.full_name,
        hashed_password=hashed_password,
        phone_number=user_in.phone_number,
        default_address=user_in.default_address,
        city_id=city_id,  
        role=user_in.role
    )

    db.add(new_user)
    db.flush()

    db.add(
        UserRole(
            user_id=new_user.id,
            role=new_user.role,
        )
    )

    db.commit()
    db.refresh(new_user)

    return {
        "id": new_user.id,
        "email": new_user.email,
        "full_name": new_user.full_name,
        "role": new_user.role,
        "city_supported": True if city_id else False,
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

    roles = [
        user_role.role
        for user_role in user.roles
    ]

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "roles": roles,
    }


# -----------------------------------------
# Forgot Password
# -----------------------------------------

@router.post(
    "/forgot-password",
    response_model=PasswordResetResponse,
)
def forgot_password(
    data: ForgotPasswordRequest,
    db: Session = Depends(get_db),
):

    user = (
        db.query(User)
        .filter(User.email == data.email)
        .first()
    )

    # Never reveal whether the email exists.
    if not user:
        return PasswordResetResponse(
            message="If an account exists, password reset instructions have been sent."
        )

    token = secrets.token_urlsafe(48)

    expires_at = (
        datetime.now(timezone.utc)
        + timedelta(hours=1)
    )

    db.add(
        PasswordResetToken(
            user_id=user.id,
            token=token,
            expires_at=expires_at,
        )
    )

    db.commit()

    # 🔔 NOTIFICATION: Password Reset Requested
    create_notification(
        db=db,
        user_id=user.id,
        title="Password Reset Requested",
        message="A password reset was requested for your account.",
        notification_type="security",
        related_id=None,
    )

    # Send the reset email
    try:
        reset_link = f"mallyard://reset-password?token={token}"
        send_email(
            to=user.email,
            subject="Reset your Mallyard password",
            body=password_reset_email(reset_link),
        )
    except Exception:
        pass

    return PasswordResetResponse(
        message="If an account exists, password reset instructions have been sent."
    )


# -----------------------------------------
# Reset Password
# -----------------------------------------

@router.post(
    "/reset-password",
    response_model=PasswordResetResponse,
)
def reset_password(
    data: ResetPasswordRequest,
    db: Session = Depends(get_db),
):

    reset_token = (
        db.query(PasswordResetToken)
        .filter(
            PasswordResetToken.token == data.token,
            PasswordResetToken.used == False,
        )
        .first()
    )

    if not reset_token:
        raise HTTPException(
            status_code=400,
            detail="Invalid or expired reset token.",
        )

    if reset_token.expires_at < datetime.now(timezone.utc):
        raise HTTPException(
            status_code=400,
            detail="Reset token has expired.",
        )

    user = (
        db.query(User)
        .filter(User.id == reset_token.user_id)
        .first()
    )

    if not user:
        raise HTTPException(
            status_code=404,
            detail="User not found.",
        )

    # Update password
    user.hashed_password = hash_password(
        data.new_password
    )

    # Mark token as used
    reset_token.used = True

    db.commit()

    # 🔔 NOTIFICATION: Password Changed
    create_notification(
        db=db,
        user_id=user.id,
        title="Password Changed",
        message="Your password has been changed successfully.",
        notification_type="security",
        related_id=None,
    )

    return PasswordResetResponse(
        message="Password reset successful."
    )

# =========================================================
# GOOGLE AUTH
# =========================================================
@router.post("/google", response_model=Token)
def google_auth(
    payload: GoogleAuthSchema,
    db: Session = Depends(get_db),
):
    # Step 1: Verify the Google token with try/except
    try:
        google_user = verify_google_token(payload.id_token)
    except Exception:
        raise HTTPException(
            status_code=401,
            detail="Invalid Google token",
        )
    
    # Step 2: Extract email and name with .get()
    email = google_user.get("email")
    full_name = google_user.get("name")
    
    # Step 3: Verify email is present
    if not email:
        raise HTTPException(
            status_code=400,
            detail="Google account has no email.",
        )
    
    # Step 4: Verify email is verified by Google
    if not google_user.get("email_verified"):
        raise HTTPException(
            status_code=401,
            detail="Google email is not verified.",
        )
    
    # Step 5: Find existing user
    user = (
        db.query(User)
        .filter(User.email == email)
        .first()
    )
    
    # Step 6: Create user if they don't exist
    if not user:
        # Generate a secure random password for Google users
        random_password = secrets.token_urlsafe(32)
        hashed_password = hash_password(random_password)
        
        user = User(
            email=email,
            full_name=full_name or "Google User",
            hashed_password=hashed_password,
            is_verified=True,  # Google has already verified the email
        )
        
        db.add(user)
        db.flush()
        
        db.add(
            UserRole(
                user_id=user.id,
                role="customer",  # Use string directly like register endpoint
            )
        )
        
        db.commit()
        db.refresh(user)
    
    # Step 7: Generate JWT token
    access_token = create_access_token(
        subject=str(user.id)
    )
    
    # Step 8: Collect workspaces
    roles = [
        user_role.role
        for user_role in user.roles
    ]
    
    # Step 9: Return same response as /login
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "roles": roles,
    }

@router.put("/me")
def update_profile(
    payload: UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # 🔥 NORMALIZE INPUT
    city_name = payload.city_name.strip().lower() if payload.city_name else None

    # 🔥 RESOLVE CITY 
    city_id = None

    if city_name:
        city_id = resolve_city(db, city_name)

        if not city_id:
            # 🔥 UPSERT CITY REQUEST (normalized)
            existing_request = db.query(CityRequest).filter(
                CityRequest.name == city_name
            ).first()

            if existing_request:
                existing_request.request_count += 1
            else:
                new_request = CityRequest(name=city_name)
                db.add(new_request)

        current_user.city_id = city_id

    # ✅ Update only provided fields (NO overwriting with None)
    if payload.full_name is not None:
        current_user.full_name = payload.full_name

    if payload.phone_number is not None:
        current_user.phone_number = payload.phone_number

    if payload.default_address is not None:
        current_user.default_address = payload.default_address

    db.commit()
    db.refresh(current_user)

    return {
        "id": current_user.id,
        "full_name": current_user.full_name,
        "phone_number": current_user.phone_number,
        "default_address": current_user.default_address,
        "city": current_user.city.name if current_user.city else None
    }