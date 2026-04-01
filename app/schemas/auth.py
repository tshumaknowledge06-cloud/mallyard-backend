from pydantic import BaseModel, EmailStr, constr
from app.db.models.user import Role


class UserCreate(BaseModel):
    email: EmailStr

    password: constr(
        min_length=8,
        max_length=128
    )

    full_name: constr(
        min_length=2,
        max_length=100,
        strip_whitespace=True
    )
    
    role: Role = Role.customer


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: Role


class UserOut(BaseModel):
    full_name: str
    email: EmailStr
    role: Role

    class Config:
        orm_mode = True


class GoogleAuthSchema(BaseModel):
    email: EmailStr
    full_name: str
    role: str