import os
import logging
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy import create_engine

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