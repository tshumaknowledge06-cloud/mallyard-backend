from pydantic import BaseModel, EmailStr, Field


# -----------------------------------------
# Forgot Password Request
# -----------------------------------------

class ForgotPasswordRequest(BaseModel):
    email: EmailStr


# -----------------------------------------
# Reset Password Request
# -----------------------------------------

class ResetPasswordRequest(BaseModel):
    token: str = Field(..., min_length=32)

    new_password: str = Field(
        ...,
        min_length=8,
        max_length=128,
    )


# -----------------------------------------
# Generic Response
# -----------------------------------------

class PasswordResetResponse(BaseModel):
    message: str