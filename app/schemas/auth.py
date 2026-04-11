from pydantic import BaseModel, EmailStr, constr
from app.db.models.user import Role
from pydantic import field_validator


class UserCreate(BaseModel):
    email: EmailStr

    password: constr(
        min_length=5,
        max_length=128
    )

    full_name: constr(
        min_length=2,
        max_length=100,
        strip_whitespace=True
    )
    
    role: Role = Role.customer

    @field_validator("password")
    def clean_password(cls, v):
        if not isinstance(v, str):
            raise ValueError("Password must be a string")
        return v.strip()
    
    @field_validator("full_name")
    def clean_name(cls, v):
        if not isinstance(v, str):
           raise ValueError("Full name must be a string")
        return " ".join(v.split())


class UserLogin(BaseModel):
    email: EmailStr
    password: str

    @field_validator("password")
    def clean_password(cls, v):
        return v.strip()


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: Role


class UserOut(BaseModel):
    full_name: str
    email: EmailStr
    role: Role

    class Config:
        from_attributes = True


class GoogleAuthSchema(BaseModel):
    email: EmailStr
    full_name: str
    role: str


