import logging

from shared_architecture.connections.mongodb_client import get_mongo_client
from shared_architecture.connections.redis_client import get_redis_client
from shared_architecture.connections.rabbitmq_client import get_rabbitmq_connection
from shared_architecture.connections.timescaledb_client import get_timescaledb_session

async def check_redis():
    try:
        redis = await get_redis_client()
        pong = await redis.ping()
        return True, f"Redis ping response: {pong}"
    except Exception as e:
        logging.exception("Redis health check failed.")
        return False, str(e)

async def check_mongo():
    try:
        db = get_mongo_client()
        collections = db.list_collection_names()
        return True, f"MongoDB collections: {collections}"
    except Exception as e:
        logging.exception("MongoDB health check failed.")
        return False, str(e)

async def check_rabbitmq():
    try:
        connection = await get_rabbitmq_connection()
        await connection.close()
        return True, "RabbitMQ connection successful"
    except Exception as e:
        logging.exception("RabbitMQ health check failed.")
        return False, str(e)

async def check_timescaledb():
    try:
        session = get_timescaledb_session()
        await session.execute("SELECT 1;")
        await session.close()
        return True, "TimescaleDB connection successful"
    except Exception as e:
        logging.exception("TimescaleDB health check failed.")
        return False, str(e)

async def health_check_all():
    checks = {
        "redis": await check_redis(),
        "mongo": await check_mongo(),
        "rabbitmq": await check_rabbitmq(),
        "timescaledb": await check_timescaledb()
    }
    return checks
