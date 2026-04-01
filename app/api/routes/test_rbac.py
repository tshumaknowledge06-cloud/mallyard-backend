from fastapi import APIRouter, Depends

from app.api.deps import get_current_user, require_role
from app.db.models.user import User

router = APIRouter(
    prefix="/rbac",
    tags=["RBAC Test"],
)


@router.get("/me")
def read_current_user(current_user: User = Depends(get_current_user)):
    return {
        "email": current_user.email,
        "role": current_user.role,
    }


@router.get("/admin-only")
def admin_only(
    current_user: User = Depends(require_role("admin")),
):
    return {
        "message": "Welcome Admin. RBAC is working.",
        "email": current_user.email,
    }
