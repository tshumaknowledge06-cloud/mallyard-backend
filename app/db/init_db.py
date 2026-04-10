from app.db.base import Base
from app.db.session import engine

# 👇 This ensures all models are registered
from app.db import models

def init_db():
    try:
        Base.metadata.create_all(bind=engine)
        print("✅ DB initialized")
    except Exception as e:
        print("❌ DB connection failed:", e)

