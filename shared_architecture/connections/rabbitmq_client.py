
import pika
from shared_architecture.config.config_loader import config_loader

env = config_loader.get("ENVIRONMENT", "dev").lower()
rabbitmq_host = "localhost" if env == "dev" else config_loader.get("RABBITMQ_HOST", "rabbitmq")
rabbitmq_port = int(config_loader.get("RABBITMQ_PORT", 5672))
rabbitmq_user = config_loader.get("RABBITMQ_USER", "admin")
rabbitmq_pass = config_loader.get("RABBITMQ_PASSWORD", "admin")

def get_rabbitmq_client():
    credentials = pika.PlainCredentials(rabbitmq_user, rabbitmq_pass)
    parameters = pika.ConnectionParameters(host=rabbitmq_host, port=rabbitmq_port, credentials=credentials)
    return pika.BlockingConnection(parameters)
