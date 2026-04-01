from app.db.session import SessionLocal
from app.db.seed.seed_data import seed_users


def run():
    db = SessionLocal()
    try:
        seed_users(db)
        print("✅ Database seeded successfully")
    finally:
        db.close()


if __name__ == "__main__":
    run()