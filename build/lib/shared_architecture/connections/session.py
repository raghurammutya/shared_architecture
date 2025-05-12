from sqlalchemy.ext.asyncio import create_async_engine

from shared_architecture.utils.env_config import get_env_var

# Dynamically build DB URL
POSTGRES_USER = get_env_var("POSTGRES_USER", "tradmin")
POSTGRES_PASSWORD = get_env_var("POSTGRES_PASSWORD", "tradpass")
POSTGRES_DB = get_env_var("POSTGRES_DB", "tradingdb")
POSTGRES_HOST = get_env_var("POSTGRES_HOST", "localhost")
POSTGRES_PORT = get_env_var("POSTGRES_PORT", "5432")

DATABASE_URL = f"postgresql+asyncpg://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"

# Shared async engine for TimescaleDB
async_engine = create_async_engine(
    DATABASE_URL,
    echo=False,
    pool_size=20,
    max_overflow=10,
    pool_timeout=30,
    future=True
)