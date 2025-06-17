# shared_architecture/connections/rabbitmq_client.py

import aio_pika
import logging
from shared_architecture.config.config_loader import config_loader
from shared_architecture.connections.service_discovery import service_discovery, ServiceType

logger = logging.getLogger(__name__)

async def get_rabbitmq_connection():
    """Create RabbitMQ connection with service discovery"""
    try:
        rabbitmq_host_config = config_loader.get("RABBITMQ_HOST", "localhost", scope="common")
        rabbitmq_port = int(config_loader.get("RABBITMQ_PORT", 5672, scope="common"))
        rabbitmq_user = config_loader.get("RABBITMQ_USER", "guest", scope="common")
        rabbitmq_password = config_loader.get("RABBITMQ_PASSWORD", "guest", scope="common")

        # Resolve the actual host to use
        rabbitmq_host = service_discovery.resolve_service_host(rabbitmq_host_config, ServiceType.RABBITMQ)
        
        # Log connection info
        connection_info = service_discovery.get_connection_info(rabbitmq_host_config, ServiceType.RABBITMQ)
        logger.info(f"RabbitMQ connection info: {connection_info}")

        url = f"amqp://{rabbitmq_user}:{rabbitmq_password}@{rabbitmq_host}:{rabbitmq_port}/"
        
        logger.info(f"✅ RabbitMQ connection created for {rabbitmq_host}:{rabbitmq_port}")
        return await aio_pika.connect_robust(url)
        
    except Exception as e:
        logger.error(f"❌ Failed to create RabbitMQ connection: {e}")
        raise