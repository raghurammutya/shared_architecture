import os
import socket
import logging
from redis.asyncio import RedisCluster
from shared_architecture.config.config_loader import get_env, ENV
from shared_architecture.connections import (
    get_redis_connection,
    get_timescaledb_session,
    get_rabbitmq_connection,
    get_mongo_connection,
    close_all_connections,
)


logger = logging.getLogger(__name__)

__all__ = [
    "get_redis",
    "get_timescaledb_session",
    "get_mongo",
    "get_rabbitmq_channel",
    "initialize_service",
    "RedisClient"
]

def initialize_service():
    logger.info("Initializing service...")
    logger.info(f"ENV: {get_env('ENV', 'dev')}")
    logger.info(f"USE_MOCKS: {get_env('USE_MOCKS', False, cast_type=bool)}")
    # Additional startup checks or health logging can go here

# Optional advanced Redis client
if ENV.use_mocks:
    from shared_architecture.mocks.redis_mock import RedisMock

class RedisClient:
    def __init__(self, config: dict):
        self.config = config
        self.client = None

    async def connect(self):
        if ENV.use_mocks:
            logger.warning("Using RedisMock (USE_MOCKS=true)")
            self.client = RedisMock()
            return

        startup_nodes = self._discover_redis_cluster_nodes()
        if not startup_nodes:
            raise RuntimeError("No Redis cluster nodes found.")

        self.client = RedisCluster(
            startup_nodes=startup_nodes,
            decode_responses=True,
            max_connections=int(self.config.get("redis_max_connections", 10))
        )
        await self.client.ping()
        logger.info("Connected to Redis Cluster successfully.")

    def _discover_redis_cluster_nodes(self):
        full_host = self.config.get("REDIS_HOST", "redis-cluster.stocksblitz.svc.cluster.local")
        port = int(self.config.get("REDIS_PORT", 6379))

        if ENV.use_mocks or not os.getenv("KUBERNETES_SERVICE_HOST"):
            logger.warning("Local/dev environment detected – using fallback localhost Redis.")
            return [{"host": "localhost", "port": port}]

        try:
            hosts = socket.gethostbyname_ex(full_host)[2]
            return [{"host": ip, "port": port} for ip in hosts]
        except Exception as e:
            logger.error(f"Failed to discover Redis Cluster nodes: {e}")
            return []

    async def get_connection(self):
        if not self.client:
            raise RuntimeError("Redis client is not initialized. Call `connect()` first.")
        return self.client

    async def health_check(self):
        try:
            if self.client and await self.client.ping():
                return {"status": "ok", "message": "Redis reachable"}
        except Exception as e:
            return {"status": "error", "message": str(e)}
        return {"status": "error", "message": "Redis not initialized or unreachable"}
