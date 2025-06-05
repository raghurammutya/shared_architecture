import aio_pika
from shared_architecture.config.config_loader import config_loader


async def get_rabbitmq_connection():
    rabbitmq_host = config_loader.get("RABBITMQ_HOST", "localhost", scope="common")
    rabbitmq_port = int(config_loader.get("RABBITMQ_PORT", 5672, scope="common"))
    rabbitmq_user = config_loader.get("RABBITMQ_USER", "guest", scope="common")
    rabbitmq_password = config_loader.get("RABBITMQ_PASSWORD", "guest", scope="common")

    url = f"amqp://{rabbitmq_user}:{rabbitmq_password}@{rabbitmq_host}:{rabbitmq_port}/"
    return await aio_pika.connect_robust(url)
