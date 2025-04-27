import os
import logging
from redis.asyncio import Redis
from redis.asyncio.cluster import RedisCluster
from typing import Optional

logger = logging.getLogger(__name__)

class RedisConnectionFactory:
    def __init__(self):
        self.redis = None

    async def connect(self):
        redis_mode = os.getenv("REDIS_MODE", "standalone").lower()

        if redis_mode == "cluster":
            self.redis = await self._connect_cluster()
        else:
            self.redis = await self._connect_standalone()

    async def _connect_standalone(self) -> Optional[Redis]:
        try:
            host = os.getenv("REDIS_HOST", "localhost")
            port = int(os.getenv("REDIS_PORT", "6379"))
            db = int(os.getenv("REDIS_DB", "0"))

            redis = Redis(
                host=host,
                port=port,
                db=db,
                decode_responses=True
            )
            await redis.ping()
            logger.info("Connected to standalone Redis.")
            return redis
        except Exception as e:
            logger.error(f"Failed to connect to standalone Redis: {e}")
            return None

    async def _connect_cluster(self) -> Optional[RedisCluster]:
        try:
            nodes_raw = os.getenv("REDIS_CLUSTER_NODES", "")
            if not nodes_raw:
                raise ValueError("REDIS_CLUSTER_NODES is not set.")

            startup_nodes = []
            for node in nodes_raw.split(","):
                host, port = node.strip().split(":")
                startup_nodes.append({"host": host, "port": int(port)})

            redis = RedisCluster(
                startup_nodes=startup_nodes,
                decode_responses=True,
                skip_full_coverage_check=True,
            )
            await redis.ping()
            logger.info("Connected to Redis Cluster.")
            return redis
        except Exception as e:
            logger.error(f"Failed to connect to Redis Cluster: {e}")
            return None

    async def get_connection(self):
        if not self.redis:
            logger.warning("Redis connection not established yet.")
        return self.redis
    async def health_check(self):
        try:
            if self.redis and await self.redis.ping():
                return {"status": "healthy", "mode": os.getenv("REDIS_MODE", "standalone")}
            return {"status": "unhealthy", "error": "No response to ping"}
        except Exception as e:
            return {"status": "unhealthy", "error": str(e)}
