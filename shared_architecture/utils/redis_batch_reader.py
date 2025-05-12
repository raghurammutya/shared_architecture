# shared_architecture/redis/redis_batch_reader.py

from typing import Optional, List
from redis.asyncio import Redis
import logging

logger = logging.getLogger(__name__)

class RedisBatchReader:
    def __init__(self, redis: Redis):
        self.redis = redis

    async def read_latest(self, key: str, count: int = 1) -> Optional[List[str]]:
        try:
            result = await self.redis.lrange(key, -count, -1)
            logger.info(f"📖 Read {len(result)} entries from {key}")
            return [r.decode("utf-8") if isinstance(r, bytes) else r for r in result]
        except Exception as e:
            logger.exception(f"❌ Error reading from Redis key: {key}")
            return None

    async def read_all(self, key: str) -> Optional[List[str]]:
        try:
            result = await self.redis.lrange(key, 0, -1)
            logger.info(f"📖 Read all {len(result)} entries from {key}")
            return [r.decode("utf-8") if isinstance(r, bytes) else r for r in result]
        except Exception as e:
            logger.exception(f"❌ Error reading all from Redis key: {key}")
            return None
