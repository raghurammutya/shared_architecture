import pika
import logging
from pika.exceptions import AMQPConnectionError
import aio_pika
import os
from shared_architecture.config.config_loader import get_env

logger = logging.getLogger(__name__)

class RabbitMQConnection:
    def __init__(self, config: dict):
        """
        Initialize the RabbitMQ connection.
        Args:
            config (dict): RabbitMQ settings.
        """
        self.host = config.get("rabbitmq_host", "localhost")
        self.port = int(config.get("rabbitmq_port", 5672))
        self.username = config.get("rabbitmq_user", "guest")
        self.password = config.get("rabbitmq_password", "guest")
        self.credentials = pika.PlainCredentials(self.username, self.password)
        self.connection = None
        self.connected = False
        logging.info(f"RabbitMQConnection initialized with config: {config}")

    def connect(self):
        """
        Establish a connection to RabbitMQ.
        """
        try:
            connection_params = pika.ConnectionParameters(
                host=self.host,
                port=self.port,
                credentials=self.credentials,
            )
            self.connection = pika.BlockingConnection(connection_params)
            self.connected = True
            logging.info("RabbitMQ connection established.")
            return self.connection
        except AMQPConnectionError as e:
            logging.error(f"Error connecting to RabbitMQ: {e}")
            self.connection = None
            self.connected = False
            return None

    def get_connection(self):
        """
        Return the existing connection or reconnect if needed.
        """
        if not self.connected or self.connection is None or self.connection.is_closed:
            logging.error("RabbitMQ connection is unavailable. Attempting to reconnect.")
            self.connect()
            if self.connection is None:
                return None
        return self.connection

    def is_connected(self):
        """
        Check if the connection is alive.
        """
        return self.connected

    def close(self):
        """
        Close the RabbitMQ connection.
        """
        try:
            if self.connection:
                self.connection.close()
                self.connected = False
                logging.info("RabbitMQ connection closed.")
        except Exception as e:
            logging.error(f"Error closing RabbitMQ connection: {e}")

async def check_rabbitmq_health():
    """
    Asynchronously checks the health of RabbitMQ using aio_pika.
    """
    try:
        url = f"amqp://{os.getenv('RABBITMQ_USER')}:{os.getenv('RABBITMQ_PASS')}@{os.getenv('RABBITMQ_HOST')}:{os.getenv('RABBITMQ_PORT')}/"
        connection = await aio_pika.connect_robust(url)
        await connection.close()
        return {"status": "healthy"}
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}

def get_rabbitmq_connection():
    """
    Connect to RabbitMQ using environment variables and return the channel.
    """
    host = get_env("RABBITMQ_HOST", "localhost")
    port = get_env("RABBITMQ_PORT", 5672, int)
    username = get_env("RABBITMQ_USER", "guest")
    password = get_env("RABBITMQ_PASSWORD", "guest")
    virtual_host = get_env("RABBITMQ_VHOST", "/")

    credentials = pika.PlainCredentials(username, password)
    parameters = pika.ConnectionParameters(
        host=host,
        port=port,
        virtual_host=virtual_host,
        credentials=credentials
    )

    try:
        connection = pika.BlockingConnection(parameters)
        channel = connection.channel()
        logger.info("Connected to RabbitMQ successfully.")
        return channel
    except Exception as e:
        logger.error(f"Failed to connect to RabbitMQ: {e}")
        raise RuntimeError("RabbitMQ connection failed.")
