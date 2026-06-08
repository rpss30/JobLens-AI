# src/database/db.py

import os
from contextlib import contextmanager
from typing import Generator

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

load_dotenv()


def get_database_url() -> str | None:
    """
    Get the PostgreSQL database URL from environment variables.
    """
    return os.getenv("DATABASE_URL")


def get_engine():
    """
    Create a SQLAlchemy engine using DATABASE_URL.
    """
    database_url = get_database_url()

    if not database_url:
        raise ValueError("DATABASE_URL is not set.")

    return create_engine(database_url, pool_pre_ping=True)


def get_session_factory():
    """
    Create a SQLAlchemy session factory.
    """
    engine = get_engine()
    return sessionmaker(bind=engine, autoflush=False, autocommit=False)


@contextmanager
def get_db_session() -> Generator[Session, None, None]:
    """
    Provide a database session with automatic commit/rollback handling.
    """
    SessionLocal = get_session_factory()
    session = SessionLocal()

    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()