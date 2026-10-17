import os
from typing import Generator
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from app.config import get_settings
from app.utils.logging import logger

Base = declarative_base()

_engine = None
_SessionFactory = None


def normalize_database_url(db_url: str) -> str:
    """Select the installed PostgreSQL driver for standard provider URLs."""
    if db_url.startswith("postgres://"):
        return f"postgresql+psycopg://{db_url[len('postgres://'):]}"
    if db_url.startswith("postgresql://"):
        return f"postgresql+psycopg://{db_url[len('postgresql://'):]}"
    return db_url


def get_engine():
    global _engine
    if _engine is None:
        settings = get_settings()
        db_url = normalize_database_url(settings.database_url)

        # Ensure sqlite directory exists if file-based sqlite
        if db_url.startswith("sqlite:///"):
            db_path = db_url.replace("sqlite:///", "")
            if db_path != ":memory:":
                db_dir = os.path.dirname(db_path)
                if db_dir and not os.path.exists(db_dir):
                    os.makedirs(db_dir, exist_ok=True)

        connect_args = {"check_same_thread": False} if "sqlite" in db_url else {}
        _engine = create_engine(db_url, connect_args=connect_args, pool_pre_ping=True)
        logger.info("Initialized database engine: %s", _engine.url.drivername)
    return _engine


_db_initialized = False


def init_db():
    """Create all tables defined in models metadata."""
    global _db_initialized
    engine = get_engine()
    # Import models so Base.metadata knows about them
    import app.models.search  # noqa: F401
    Base.metadata.create_all(bind=engine)
    _db_initialized = True
    logger.info("Database schema initialized successfully.")


def get_session_factory():
    global _SessionFactory, _db_initialized
    if not _db_initialized:
        init_db()
    if _SessionFactory is None:
        _SessionFactory = sessionmaker(autocommit=False, autoflush=False, bind=get_engine())
    return _SessionFactory


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency yielding a database session."""
    factory = get_session_factory()
    db = factory()
    try:
        yield db
    finally:
        db.close()
