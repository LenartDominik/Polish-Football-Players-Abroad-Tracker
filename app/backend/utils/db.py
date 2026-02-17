"""
Common database utilities.

Provides context managers and helper functions for database operations.
Ensures proper session management for Supabase connection pooling.
"""
from contextlib import contextmanager
from typing import Generator
import logging

from app.backend.database import SessionLocal

logger = logging.getLogger(__name__)


@contextmanager
def get_db_session() -> Generator:
    """
    Context manager for database sessions.

    Ensures proper session handling for Supabase Port 6543 connection pooling.
    Automatically commits or rollbacks and closes the session.

    Usage:
        with get_db_session() as db:
            player = db.query(Player).first()
            player.name = "New Name"
            # Session automatically committed and closed

    Yields:
        Session: SQLAlchemy database session
    """
    db = SessionLocal()
    try:
        yield db
        db.commit()
        logger.debug("Database session committed successfully")
    except Exception as e:
        db.rollback()
        logger.error(f"Database session rolled back due to error: {e}")
        raise
    finally:
        db.close()
        logger.debug("Database session closed")


def get_db():
    """
    Dependency injection function for FastAPI endpoints.

    Compatible with FastAPI's Depends() for endpoint injection.

    Usage:
        @router.get("/players")
        def get_players(db: Session = Depends(get_db)):
            return db.query(Player).all()

    Yields:
        Session: SQLAlchemy database session
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
