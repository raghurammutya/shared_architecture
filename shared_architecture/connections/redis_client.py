
import redis.asyncio as redis
from shared_architecture.config.config_loader import config_loader

env = config_loader.get("ENVIRONMENT", "dev").lower()
redis_host = "localhost" if env == "dev" else config_loader.get("REDIS_HOST", "redis-service")
redis_port = int(config_loader.get("REDIS_PORT", 6379))
redis_db = int(config_loader.get("REDIS_DB", 0))
redis_password = config_loader.get("REDIS_PASSWORD", None)

def get_redis_client():
    return redis.Redis(
        host=redis_host,
        port=redis_port,
        db=redis_db,
        password=redis_password,
        decode_responses=True,
    )
