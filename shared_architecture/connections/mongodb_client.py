# shared_architecture/connections/mongodb_client.py

import logging
from motor.motor_asyncio import AsyncIOMotorClient
from shared_architecture.config.config_loader import config_loader
from shared_architecture.connections.service_discovery import service_discovery, ServiceType

logger = logging.getLogger(__name__)

def get_mongo_client() -> AsyncIOMotorClient:
    """Create MongoDB client with service discovery"""
    try:
        mongo_host_config = config_loader.get("MONGODB_HOST", "localhost", scope="common")
        mongo_port = config_loader.get("MONGODB_PORT", 27017, scope="common")
        mongo_user = config_loader.get("MONGODB_USER", None, scope="common")
        mongo_password = config_loader.get("MONGODB_PASSWORD", None, scope="common")
        mongo_auth_source = config_loader.get("MONGODB_AUTH_SOURCE", "admin", scope="common")

        # Resolve the actual host to use
        mongo_host = service_discovery.resolve_service_host(mongo_host_config, ServiceType.MONGODB)
        
        # Log connection info
        connection_info = service_discovery.get_connection_info(mongo_host_config, ServiceType.MONGODB)
        logger.info(f"MongoDB connection info: {connection_info}")

        # Build MongoDB URI
        if mongo_user and mongo_password:
            uri = f"mongodb://{mongo_user}:{mongo_password}@{mongo_host}:{mongo_port}/?authSource={mongo_auth_source}"
        else:
            uri = f"mongodb://{mongo_host}:{mongo_port}"

        logger.info(f"✅ MongoDB client created for {mongo_host}:{mongo_port}")
        return AsyncIOMotorClient(uri)
        
    except Exception as e:
        logger.error(f"❌ Failed to create MongoDB client: {e}")
        raise