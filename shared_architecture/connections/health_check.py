import asyncio
from shared_architecture.connections.redis_connection import RedisConnectionFactory
from shared_architecture.connections.rabbitmq_connection import check_rabbitmq_health
from shared_architecture.connections.mongodb_connection import check_mongo_health
from shared_architecture.connections.timescaledb_connection import check_timescaledb_health

async def system_health_check():
    redis_factory = RedisConnectionFactory()
    await redis_factory.connect()

    results = await asyncio.gather(
        redis_factory.health_check(),
        check_rabbitmq_health(),
        asyncio.to_thread(check_mongo_health),
        check_timescaledb_health(),
    )

    return {
        "redis": results[0],
        "rabbitmq": results[1],
        "mongodb": results[2],
        "timescaledb": results[3],
    }
