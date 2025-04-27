import logging
from redis.asyncio import RedisCluster
from fastapi import FastAPI
import socket
# Logging Configuration
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)

class AsyncRedisConnectionPool:
    def __init__(self, config: dict):
        """
        Initialize Redis connection pool using redis.asyncio.

        Args:
            config (dict): Configuration dictionary with Redis parameters.
        """
        self.config = config
        self.redis = None  # Redis async connection instance
        logging.info(f"AsyncRedisConnectionPool initialized with config: {self.config}")
    def discover_redis_nodes(service="redis-cluster", namespace="default", port=6379):
        try:
            hosts = socket.gethostbyname_ex(f"{service}.{namespace}.svc.cluster.local")[2]
            return [{"host": ip, "port": port} for ip in hosts]
        except Exception as e:
            logging.error(f"Failed to discover Redis Cluster nodes: {e}")
            return []
    def connect(self):
        startup_nodes = self.discover_redis_nodes()
        self.redis = RedisCluster(
            startup_nodes=startup_nodes,
            decode_responses=True,
            max_connections=10,
        )
class RedisConnectionPool:
    async def connect(self):
        """
        Establish an async connection to Redis.
        """
        try:
            startup_nodes = discover_redis_nodes()
            self.redis = RedisCluster(
                startup_nodes=startup_nodes,
                decode_responses=True,
                max_connections=int(self.config.get("redis_max_connections", 10)),
            )
            # redis_url = f"redis://{self.config.get('redis_host', 'localhost')}:{self.config.get('redis_port', 6379)}"
            # self.redis = Redis.from_url(
            #     redis_url,
            #     db=int(self.config.get("redis_db", 0)),
            #     decode_responses=True,  # Ensures responses are returned as strings
            #     max_connections=int(self.config.get("redis_max_connections", 10)),
            # )

            # Test Redis connection with ping
            await self.redis.ping()
            logging.info("Connected to Redis successfully.")
        except Exception as e:
            logging.error(f"Error connecting to Redis: {e}")
            self.redis = None

    async def get_connection(self):
        """
        Retrieve the Redis connection.

        Returns:
            redis.asyncio.Redis | None: Redis connection instance or None if not connected.
        """
        if not self.redis:
            logging.error("Redis connection is unavailable.")
            return None
        return self.redis

    async def is_connected(self):
        """
        Check if Redis connection is available.

        Returns:
            bool: True if connected, False otherwise.
        """
        try:
            if not self.redis:
                return False
            return await self.redis.ping()
        except Exception:
            return False

    async def close(self):
        """
        Closes the Redis connection pool gracefully.
        """
        if self.redis:
            try:
                await self.redis.close()
                logging.info("Redis connection pool closed successfully.")
            except Exception as e:
                logging.error(f"Error closing Redis connection pool: {e}")