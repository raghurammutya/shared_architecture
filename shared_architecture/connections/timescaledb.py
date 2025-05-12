import os
import logging
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.sql import text
from shared_architecture.config.config_loader import get_env
from shared_architecture.mocks.timescaledb_mock import get_mock_timescaledb_session

logger = logging.getLogger(__name__)

__all__ = [
    "get_timescaledb_session",
    "get_timescaledb_client",
    "close_timescaledb_client",
    "test_timescaledb_connection",
    "run_query"
]

# --- Singleton Containers ---
_engine = None
_SessionFactory = None
_timescaledb_client = None

def get_timescaledb_session() -> async_sessionmaker[AsyncSession]:
    global _engine, _SessionFactory

    if _SessionFactory:
        return _SessionFactory

    use_mocks = get_env("USE_MOCKS", default=False)
    if use_mocks:
        logger.warning("[TimescaleDB] Using TimescaleDBMock due to USE_MOCKS=true")
        _SessionFactory = get_mock_timescaledb_session()
        return _SessionFactory

    db_user = get_env("TIMESCALEDB_USER", default="tradmin")
    db_pass = get_env("TIMESCALEDB_PASSWORD", default="tradpass")
    db_host = get_env("TIMESCALEDB_HOST", default="localhost")
    db_port = get_env("TIMESCALEDB_PORT", default="5432")
    db_name = get_env("TIMESCALEDB_DB", default="tradingdb")

    db_url = f"postgresql+asyncpg://{db_user}:{db_pass}@{db_host}:{db_port}/{db_name}"
    logger.info(f"[TimescaleDB] Connecting to {db_url}")

    _engine = create_async_engine(db_url, echo=False, pool_pre_ping=True)
    _SessionFactory = async_sessionmaker(bind=_engine, class_=AsyncSession, expire_on_commit=False)
    return _SessionFactory

async def get_timescaledb_client() -> AsyncSession:
    global _timescaledb_client

    if _timescaledb_client:
        return _timescaledb_client

    session_factory = get_timescaledb_session()
    _timescaledb_client = session_factory()
    logger.info("[TimescaleDB] Created new AsyncSession")
    return _timescaledb_client

async def close_timescaledb_client():
    global _timescaledb_client
    if _timescaledb_client:
        await _timescaledb_client.close()
        logger.info("[TimescaleDB] AsyncSession closed")
        _timescaledb_client = None

async def test_timescaledb_connection(session: AsyncSession):
    try:
        result = await session.execute(text("SELECT 1"))
        row = result.fetchone()
        if row:
            logger.info(f"✅ TimescaleDB connection OK: {row[0]}")
        else:
            logger.error("❌ TimescaleDB connected but no result from SELECT 1")
    except Exception as e:
        logger.error(f"❌ TimescaleDB connection test failed: {e}")

async def run_query(query: str) -> list:
    """
    Utility to run raw SQL for debugging or scripting.
    """
    async with get_timescaledb_session()() as session:
        result = await session.execute(text(query))
        return result.fetchall()
