from fastapi import APIRouter, Depends
from app.api.deps_auth import get_current_user
from app.schemas.auth import UserOut
from app.db.models.user import User

router = APIRouter(
    prefix="/users",
    tags=["Users"],
)

@router.get("/me", response_model=UserOut)
def read_current_user(current_user: User = Depends(get_current_user)):
    return current_user
