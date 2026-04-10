from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.core.config import settings

print("Using DB:", settings.DATABASE_URL)

# Create engine
engine = create_engine(
    settings.DATABASE_URL,
    connect_args={"sslmode": "require"}
)

# Session factory
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)

# Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


