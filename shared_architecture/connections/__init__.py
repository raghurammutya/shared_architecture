from shared_architecture.config.config_loader import ENV

# === Live Imports ===
from .redis import get_redis_connection as _get_live_redis,connect_to_redis
from .timescaledb import get_timescaledb_session as _get_live_timescaledb_session, test_timescaledb_connection
from .mongodb import get_live_mongo
from .rabbitmq import get_rabbitmq_connection as _get_live_rabbitmq_channel
from .base_connection import close_all_connections

# === Mock Imports (only when needed) ===
if ENV.use_mocks:
    from shared_architecture.mocks.redis_mock import RedisMock
    from shared_architecture.mocks.timescaledb_mock import get_mock_timescaledb_session
    from shared_architecture.mocks.mongo_mock import MongoMock
    from shared_architecture.mocks.rabbitmq_mock import get_mock_rabbitmq_channel

# === Dynamic Client Factories ===
async def get_redis_connection():
    """
    Returns Redis connection (mocked or real depending on ENV).
    """
    if ENV.use_mocks:
        return RedisMock()
    return await _get_live_redis()

def get_timescaledb_session():
    """
    Returns TimescaleDB session (mocked or real depending on ENV).
    """
    return get_mock_timescaledb_session() if ENV.use_mocks else _get_live_timescaledb_session()

def get_mongo_connection():
    """
    Returns Mongo connection (mocked or real depending on ENV).
    """
    return MongoMock() if ENV.use_mocks else get_live_mongo()

def get_rabbitmq_connection():
    """
    Returns RabbitMQ connection (mocked or real depending on ENV).
    """
    return get_mock_rabbitmq_channel() if ENV.use_mocks else _get_live_rabbitmq_channel()

# === Exported Interface ===
__all__ = [
    "get_redis_connection",
    "get_timescaledb_session",
    "get_mongo_connection",
    "get_rabbitmq_connection",
    "close_all_connections",
    "test_timescaledb_connection",
    "connect_to_redis"
]
