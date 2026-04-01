from pydantic import BaseModel
from datetime import datetime

class ReviewCreate(BaseModel):
    listing_id: int
    content: str

class ReviewOut(BaseModel):
    id: int
    content: str
    created_at: datetime
    user_name: str

    class Config:
        from_attributes = True