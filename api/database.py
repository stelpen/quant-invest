"""Database setup and session management."""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from config.settings import settings

engine = create_engine(settings.DB_URL, echo=False, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


def get_db():
    """FastAPI dependency: yield a database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
