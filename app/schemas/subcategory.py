from pydantic import BaseModel
from typing import Optional


# 🔹 Used when creating a subcategory (POST)
class SubCategoryCreate(BaseModel):
    name: str
    description: Optional[str] = None
    category_id: int


# 🔹 Used when returning subcategory data (GET)
class SubCategoryOut(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    category_id: int

    class Config:
        from_attributes = True
