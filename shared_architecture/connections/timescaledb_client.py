from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
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
