# src/database/init_db.py

from src.database.db import get_engine
from src.database.models import Base


def init_db() -> None:
    """
    Create all database tables defined in src/database/models.py.
    """
    engine = get_engine()
    Base.metadata.create_all(bind=engine)
    print("Database tables created successfully.")


if __name__ == "__main__":
    init_db()