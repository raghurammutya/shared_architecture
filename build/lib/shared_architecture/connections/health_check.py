import asyncio
from shared_architecture.utils.service_helpers import connection_manager, initialize_service
from shared_architecture.connections.rabbitmq_connection import check_rabbitmq_health
from shared_architecture.connections.mongodb_connection import check_mongo_health
from shared_architecture.connections.timescaledb_connection import check_timescaledb_health


async def system_health_check(service_name="health_service"):
    # Ensure the shared connection manager is initialized
    await initialize_service(service_name)

    # Fetch Redis connection (used just for health check)
    redis = await connection_manager.get_redis_connection()

    # Perform health checks
    results = await asyncio.gather(
        redis.ping(),                  # Redis async ping
        check_rabbitmq_health(),      # RabbitMQ health
        asyncio.to_thread(check_mongo_health),  # MongoDB health
        check_timescaledb_health(),   # TimescaleDB health
    )

    return {
        "redis": results[0] == True,  # ping() returns True
        "rabbitmq": results[1],
        "mongodb": results[2],
        "timescaledb": results[3],
    }
