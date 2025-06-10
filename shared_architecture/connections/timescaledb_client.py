from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from shared_architecture.config.config_loader import config_loader


def get_timescaledb_session():
    db_host = config_loader.get("TIMESCALEDB_HOST", "localhost", scope="common")
    db_port = config_loader.get("TIMESCALEDB_PORT", "5432", scope="common")
    db_user = config_loader.get("TIMESCALEDB_USER", "postgres", scope="common")
    db_password = config_loader.get("TIMESCALEDB_PASSWORD", "postgres", scope="common")
    db_name = config_loader.get("TIMESCALEDB_DB", "stocksblitz", scope="common")

    url = f"postgresql+asyncpg://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
    engine = create_async_engine(url, echo=False, future=True)
    return async_sessionmaker(engine, expire_on_commit=False)


def get_sync_timescaledb_session():
    db_host = config_loader.get("TIMESCALEDB_HOST", "localhost", scope="common")
    db_port = config_loader.get("TIMESCALEDB_PORT", "5432", scope="common")
    db_user = config_loader.get("TIMESCALEDB_USER", "postgres", scope="common")
    db_password = config_loader.get("TIMESCALEDB_PASSWORD", "postgres", scope="common")
    db_name = config_loader.get("TIMESCALEDB_DB", "stocksblitz", scope="common")

    url = f"postgresql+psycopg2://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
    engine = create_engine(url, echo=False, future=True)
    return sessionmaker(bind=engine, expire_on_commit=False)
