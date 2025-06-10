# shared_architecture/connections/connection_manager.py

import logging
from sqlalchemy import text
from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession

from shared_architecture.connections.redis_client import get_redis_client
from shared_architecture.connections.mongodb_client import get_mongo_client
from shared_architecture.connections.timescaledb_client import (
    get_timescaledb_session,
    get_sync_timescaledb_session,
)
from shared_architecture.connections.rabbitmq_client import get_rabbitmq_connection

logger = logging.getLogger(__name__)


class ConnectionManager:
    def __init__(self):
        self.redis = None
        self.mongodb = None
        self.timescaledb = None  # async session factory
        self.timescaledb_sync = None  # sync session factory
        self.rabbitmq = None

    async def initialize(self):
        self.redis = get_redis_client()
        self.mongodb = get_mongo_client()
        self.timescaledb = get_timescaledb_session()
        self.timescaledb_sync = get_sync_timescaledb_session()
        self.rabbitmq = await get_rabbitmq_connection()

        failed = []

        try:
            await self.redis.ping()
        except Exception as e:
            logger.error("❌ Redis connection failed: %s", e)
            failed.append("Redis")

        try:
            async with self.timescaledb() as session:  # type: AsyncSession
                await session.execute(text("SELECT 1"))
        except Exception as e:
            logger.error("❌ TimescaleDB (async) connection failed: %s", e)
            failed.append("TimescaleDB (async)")

        try:
            sync_session: Session = self.timescaledb_sync()
            sync_session.execute(text("SELECT 1"))
            sync_session.close()
        except Exception as e:
            logger.error("❌ TimescaleDB (sync) connection failed: %s", e)
            failed.append("TimescaleDB (sync)")

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

    def get_sync_timescaledb_session(self) -> Session:
        if not self.timescaledb_sync:
            raise RuntimeError("Sync TimescaleDB session not initialized")
        return self.timescaledb_sync()

    def get_redis_connection(self):
        if not self.redis:
            raise RuntimeError("Redis client not initialized")
        return self.redis

    def get_rabbitmq_connection(self):
        if not self.rabbitmq:
            raise RuntimeError("RabbitMQ connection not initialized")
        return self.rabbitmq

    def get_mongo_connection(self):
        if not self.mongodb:
            raise RuntimeError("MongoDB connection not initialized")
        return self.mongodb

    def close(self):
        # Optional cleanup logic
        pass


# Singleton instance
connection_manager = ConnectionManager()
