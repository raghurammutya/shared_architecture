import os
from shared_architecture.connections.redis import get_redis_connection
from shared_architecture.connections.timescaledb import get_timescaledb_session
from shared_architecture.connections.rabbitmq import get_rabbitmq_connection
from shared_architecture.connections.mongodb import get_mongo_connection

class ConnectionManager:
    """
    Centralized manager for all service connections.
    Provides access to Redis, TimescaleDB, RabbitMQ, and MongoDB.
    Supports mock switching based on USE_MOCKS env variable.
    """

    def __init__(self, service_name: str):
        self.service_name = service_name
        self.env = os.getenv("ENV", "local")
        self.use_mocks = os.getenv("USE_MOCKS", "false").lower() == "true"
        self._redis = None
        self._timescaledb = None
        self._rabbitmq = None
        self._mongo = None

    async def get_redis(self):
        if not self._redis:
            self._redis = await get_redis_connection(self.use_mocks)
        return self._redis

    async def get_timescaledb(self):
        if not self._timescaledb:
            self._timescaledb = await get_timescaledb_session(self.use_mocks)
        return self._timescaledb

    async def get_rabbitmq(self):
        if not self._rabbitmq:
            self._rabbitmq = await get_rabbitmq_connection(self.use_mocks)
        return self._rabbitmq

    async def get_mongo(self):
        if not self._mongo:
            self._mongo = await get_mongo_connection(self.use_mocks)
        return self._mongo
