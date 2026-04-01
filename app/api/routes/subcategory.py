from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.db.models.subcategory import SubCategory
from app.db.models.user import User
from app.schemas.subcategory import SubCategoryCreate, SubCategoryOut
from app.api.deps import get_current_user


router = APIRouter(
    prefix="/subcategories",
    tags=["Subcategories"]
)


@router.post("/", response_model=SubCategoryOut)
def create_subcategory(
    subcategory: SubCategoryCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):

    if current_user.role != "admin":
        raise HTTPException(
            status_code=403,
            detail="Only admins can create subcategories"
        )

    db_subcategory = SubCategory(**subcategory.dict())

    db.add(db_subcategory)
    db.commit()
    db.refresh(db_subcategory)

    return db_subcategory


@router.get("/", response_model=list[SubCategoryOut])
def get_subcategories(db: Session = Depends(get_db)):
    return db.query(SubCategory).all()