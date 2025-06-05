import os
import logging
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy import create_engine

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from shared_architecture.config.config_loader import get_env

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Dynamically construct the database URL from environment variables
def get_database_url() -> str:
    try:
        db_user = os.getenv("POSTGRES_USER", "traduser")
        db_password = os.getenv("POSTGRES_PASSWORD", "tradpass")
        db_host = os.getenv("POSTGRES_HOST", "localhost")
        db_port = os.getenv("POSTGRES_PORT", "5432")
        db_name = os.getenv("POSTGRES_DATABASE", "timescaledb")

        database_url = f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
        logger.info(f"DATABASE_URL: {database_url}")  # Debugging log
        return database_url

    except Exception as e:
        logger.error(f"Failed to construct database URL: {e}")
        raise RuntimeError(f"Failed to construct database URL: {e}") from e

DATABASE_URL = get_database_url()
engine = create_engine(DATABASE_URL)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
logger.info(f"SessionLocal initialized with engine: {engine}")  # Debugging log

# Dependency to provide database session
def get_db() -> Session:
    db: Session = SessionLocal()
    try:
        logger.info(f"Database session created: {db.bind.url}")  # Debugging log
        yield db
    finally:
        logger.info("Closing database session")  # Debugging log
        db.close()

DB_URL_ASYNC = get_env("TIMESCALEDB_URL_ASYNC", "postgresql+asyncpg://postgres:postgres@localhost:5432/stocksblitz")
DB_URL_SYNC = get_env("TIMESCALEDB_URL", "postgresql://postgres:postgres@localhost:5432/stocksblitz")

# === Async Engine (used for FastAPI + async ORM operations) ===
async_engine = create_async_engine(
    DB_URL_ASYNC,
    echo=False,
    pool_pre_ping=True,
    future=True,
)

# Async session maker for FastAPI
AsyncSessionLocal: async_sessionmaker[AsyncSession] = async_sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

# === Sync Engine (used for Alembic migrations or blocking operations) ===
sync_engine = create_engine(
    DB_URL_SYNC,
    pool_pre_ping=True,
    future=True,
)

# Sync session maker
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=sync_engine)