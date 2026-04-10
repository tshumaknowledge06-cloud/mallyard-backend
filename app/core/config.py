from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    # -------------------------
    # Core
    # -------------------------
    DATABASE_URL: str 
    SECRET_KEY: str = "dev-secret-key-change-later"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    # -------------------------
    # Email (SMTP)
    # -------------------------
    SMTP_SERVER: str
    SMTP_PORT: int = 587
    SMTP_USERNAME: str
    SMTP_PASSWORD: str
    SMTP_FROM: str

    # -------------------------
    # Sandy (AI / Assistant layer)
    # -------------------------
    SANDY_MODE: str = "read_only"
    SANDY_TONE: str = "premium_calm_african_warmth"

    # -------------------------
    # Platform behavior
    # -------------------------
    PLATFORM_ROLE: str = "facilitator_only"
    MANUAL_DELIVERY_MATCHING: bool = True

    # -------------------------
    # Payments (future-ready)
    # -------------------------
    ENABLE_IN_PLATFORM_PAYMENTS: bool = False
    STRIPE_ENABLED: bool = False
    PAYPAL_ENABLED: bool = False

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()

