import redis.asyncio as redis
from shared_architecture.config.config_loader import config_loader

def get_redis_client():
    env = config_loader.get("ENVIRONMENT", "dev", scope="private").lower()

    # Only allow fallback to hardcoded host in 'dev'
    if env == "dev":
        redis_host = "redis"
    else:
        redis_host = config_loader.get("REDIS_HOST", "redis-service", scope="common")

    redis_port = int(config_loader.get("REDIS_PORT", 6379, scope="common"))
    redis_db = int(config_loader.get("REDIS_DB", 0, scope="common"))
    redis_password = config_loader.get("REDIS_PASSWORD", None, scope="common")

    return redis.Redis(
        host=redis_host,
        port=redis_port,
        db=redis_db,
        password=redis_password,
        decode_responses=True,
    )