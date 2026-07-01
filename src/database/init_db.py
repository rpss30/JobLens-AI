# src/database/init_db.py

from src.database.db import get_engine
from src.database.models import Base


def init_db() -> None:
    """
    Create database tables directly from SQLAlchemy models.

    Prefer Alembic migrations for local, Docker, and cloud setup. This helper is
    kept for lightweight development resets and backwards compatibility.
    """
    engine = get_engine()
    Base.metadata.create_all(bind=engine)
    print("Database tables created successfully.")


if __name__ == "__main__":
    init_db()
