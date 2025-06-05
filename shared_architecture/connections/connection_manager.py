# shared_architecture/connections/connection_manager.py

from shared_architecture.connections import (
    get_redis_client,
    get_timescaledb_session,
    get_rabbitmq_connection,
    get_mongo_client
)
import logging
from sqlalchemy import text
logger = logging.getLogger(__name__)


class ConnectionManager:
    def __init__(self):
        self.redis = None
        self.mongodb = None
        self.timescaledb = None
        self.rabbitmq = None

    async def initialize(self):
        from .redis_client import get_redis_client
        from .mongodb_client import get_mongo_client
        from .timescaledb_client import get_timescaledb_session
        from .rabbitmq_client import get_rabbitmq_connection

        self.redis = get_redis_client()
        self.mongodb = get_mongo_client()
        self.timescaledb = get_timescaledb_session()
        self.rabbitmq = await get_rabbitmq_connection()

        failed = []

        try:
            await self.redis.ping()
        except Exception as e:
            logger.error("❌ Redis connection failed: %s", e)
            failed.append("Redis")

        try:
            async with self.timescaledb() as session:
                await session.execute(text("SELECT 1"))
        except Exception as e:
            logger.error("❌ TimescaleDB connection failed: %s", e)
            failed.append("TimescaleDB")

        try:
            await self.mongodb.admin.command("ping")
        except Exception as e:
            logger.error("❌ MongoDB connection failed: %s", e)
            failed.append("MongoDB")

        try:
            channel = await self.rabbitmq.channel()
            await channel.close()
        except Exception as e:
            logger.error("❌ RabbitMQ connection failed: %s", e)
            failed.append("RabbitMQ")

        if failed:
            raise RuntimeError(f"🚨 Startup failed: Could not connect to: {', '.join(failed)}")

    def close(self):
        # Add cleanup logic if needed for each connection
        pass

# Singleton instance
connection_manager = ConnectionManager()
