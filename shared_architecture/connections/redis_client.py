# shared_architecture/connections/redis_client.py

import redis.asyncio as redis
import logging
from typing import Optional
from shared_architecture.config.config_loader import config_loader
from shared_architecture.connections.service_discovery import service_discovery, ServiceType

logger = logging.getLogger(__name__)

def get_redis_client():
    """Create a Redis client with connection pooling and service discovery"""
    try:
        redis_host_config = config_loader.get("REDIS_HOST", "localhost", scope="all")
        redis_port = int(config_loader.get("REDIS_PORT", 6379, scope="all"))

        # Resolve the actual host to use
        redis_host = service_discovery.resolve_service_host(redis_host_config, ServiceType.REDIS)
        
        # Log connection info
        connection_info = service_discovery.get_connection_info(redis_host_config, ServiceType.REDIS)
        logger.info(f"Redis connection info: {connection_info}")
        
        # Create Redis client with connection pooling
        client = redis.Redis(
            host=redis_host,
            port=redis_port,
            decode_responses=True,
            socket_connect_timeout=5,
            socket_timeout=5,
            retry_on_timeout=True,
            health_check_interval=30,
            max_connections=20  # Connection pool size
        )
        
        logger.info(f"✅ Redis client created for {redis_host}:{redis_port}")
        return client
        
    except Exception as e:
        logger.error(f"❌ Failed to create Redis client: {e}")
        return None