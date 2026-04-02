from fastapi import APIRouter
from app.db.session import SessionLocal
from app.db.seed.seed_data import seed_users

router = APIRouter()

@router.post("/seed-initial-data")
def seed_initial_data():
    db = SessionLocal()
    try:
        seed_users(db)
        return {"message": "✅ Database seeded successfully"}
    finally:
        db.close()