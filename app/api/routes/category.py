from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app.db.session import get_db
from app.db.models.category import Category
from app.schemas.category import CategoryCreate, CategoryResponse
from app.api.deps import require_role
from app.db.models.user import User


router = APIRouter(
    prefix="/categories",
    tags=["Categories"]
)


# 🔒 Admin-only create
@router.post("/", response_model=CategoryResponse)
def create_category(
    category_in: CategoryCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin"))
):
    existing = db.query(Category).filter(Category.name == category_in.name).first()
    if existing:
        raise HTTPException(status_code=400, detail="Category already exists")

    category = Category(**category_in.model_dump())
    db.add(category)
    db.commit()
    db.refresh(category)

    return category


# 🌍 Public read
@router.get("/", response_model=List[CategoryResponse])
def get_categories(db: Session = Depends(get_db)):
    return db.query(Category).all()
