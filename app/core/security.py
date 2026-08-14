from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any

from fastapi import HTTPException
from jose import jwt, JWTError, ExpiredSignatureError
from passlib.context import CryptContext
from google.oauth2 import id_token
from google.auth.transport import requests

from app.core.config import settings


# -------------------------
# Password hashing context
# -------------------------
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# -------------------------
# Password helpers
# -------------------------

def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


# -------------------------
# JWT helpers
# -------------------------

def create_access_token(
    subject: str,
    expires_delta: Optional[timedelta] = None,
) -> str:

    expire = datetime.now(timezone.utc) + (
        expires_delta
        or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )

    to_encode = {
        "sub": subject,
        "type": "access",
        "iat": datetime.now(timezone.utc),
        "exp": expire,
    }

    encoded_jwt = jwt.encode(
        to_encode,
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM,
    )

    return encoded_jwt


def decode_access_token(token: str) -> Optional[Dict[str, Any]]:
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
        )

        if not payload or payload.get("sub") is None:
            return None

        return payload

    except ExpiredSignatureError:
        return None

    except JWTError:
        return None


# -------------------------
# Google Token Verification
# -------------------------

def verify_google_token(token: str) -> dict:
    """
    Verify a Google OAuth ID token and return user info.
    
    Returns:
        dict: Contains 'email', 'name', 'picture', 'email_verified' etc.
    
    Raises:
        HTTPException: If the token is invalid
    """
    try:
        # Verify the token with Google
        idinfo = id_token.verify_oauth2_token(
            token,
            requests.Request(),
            settings.GOOGLE_CLIENT_ID
        )
        
        # Return user info
        return {
            "email": idinfo.get("email"),
            "name": idinfo.get("name"),
            "picture": idinfo.get("picture"),
            "email_verified": idinfo.get("email_verified", False),
        }
    except ValueError:
        # Invalid token
        raise HTTPException(
            status_code=401,
            detail="Invalid Google token",
        )
    except Exception:
        # Other errors
        raise HTTPException(
            status_code=500,
            detail="Google verification failed",
        )


# Backward compatibility
get_password_hash = hash_password