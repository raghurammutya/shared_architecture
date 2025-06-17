# shared_architecture/connections/timescaledb_client.py

import logging
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from shared_architecture.config.config_loader import config_loader
from shared_architecture.connections.service_discovery import service_discovery, ServiceType

logger = logging.getLogger(__name__)

def get_timescaledb_session():
    """Create async TimescaleDB session with service discovery"""
    try:
        db_host_config = config_loader.get("TIMESCALEDB_HOST", "timescaledb", scope="common")
        db_port = config_loader.get("TIMESCALEDB_PORT", "5432", scope="common")
        db_user = config_loader.get("TIMESCALEDB_USER", "tradmin", scope="common")
        db_password = config_loader.get("TIMESCALEDB_PASSWORD", "tradpass", scope="common")
        db_name = config_loader.get("TIMESCALEDB_DB", "tradingdb", scope="common")

        # Resolve the actual host to use
        db_host = service_discovery.resolve_service_host(db_host_config, ServiceType.TIMESCALEDB)
        
        # Log connection info
        connection_info = service_discovery.get_connection_info(db_host_config, ServiceType.TIMESCALEDB)
        logger.info(f"TimescaleDB (async) connection info: {connection_info}")

        url = f"postgresql+asyncpg://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
        engine = create_async_engine(
            url, 
            echo=False, 
            future=True,
            pool_pre_ping=True,
            pool_recycle=3600,  # Recycle connections every hour
            pool_size=10,
            max_overflow=20
        )
        
        logger.info(f"✅ TimescaleDB async session factory created for {db_host}:{db_port}")
        return async_sessionmaker(engine, expire_on_commit=False)
        
    except Exception as e:
        logger.error(f"❌ Failed to create TimescaleDB async session: {e}")
        raise


def get_sync_timescaledb_session():
    """Create sync TimescaleDB session with service discovery"""
    try:
        db_host_config = config_loader.get("TIMESCALEDB_HOST", "timescaledb", scope="common")
        db_port = config_loader.get("TIMESCALEDB_PORT", "5432", scope="common")
        db_user = config_loader.get("TIMESCALEDB_USER", "tradmin", scope="common")
        db_password = config_loader.get("TIMESCALEDB_PASSWORD", "tradpass", scope="common")
        db_name = config_loader.get("TIMESCALEDB_DB", "tradingdb", scope="common")

        # Resolve the actual host to use
        db_host = service_discovery.resolve_service_host(db_host_config, ServiceType.TIMESCALEDB)
        
        # Log connection info
        connection_info = service_discovery.get_connection_info(db_host_config, ServiceType.TIMESCALEDB)
        logger.info(f"TimescaleDB (sync) connection info: {connection_info}")

        url = f"postgresql+psycopg2://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
        engine = create_engine(
            url, 
            echo=False, 
            future=True,
            pool_pre_ping=True,
            pool_recycle=3600,  # Recycle connections every hour
            pool_size=5,
            max_overflow=10
        )
        
        logger.info(f"✅ TimescaleDB sync session factory created for {db_host}:{db_port}")
        return sessionmaker(bind=engine, expire_on_commit=False)
        
    except Exception as e:
        logger.error(f"❌ Failed to create TimescaleDB sync session: {e}")
        raise