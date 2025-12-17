"""Database setup and session management.

Right now it's just SQLAlchemy + SQLite (unless DATABASE_URL is changed).
"""
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from app.config import settings

# Create engine - SQLite for now, easy to swap to Postgres later
engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False} if "sqlite" in settings.database_url else {}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    """Dependency for getting DB session (FastAPI Depends)."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Initialize database tables (create_all)."""
    Base.metadata.create_all(bind=engine)

