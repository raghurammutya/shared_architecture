import pika
import logging
from pika.exceptions import AMQPConnectionError
import aio_pika
import os

logging.basicConfig(
level=logging.INFO,
format="%(asctime)s - %(levelname)s - %(message)s",
)

class RabbitMQConnection:
    def __init__(self, config: dict):
        """
        Initialize the RabbitMQ connection.

        Args:
        config (dict): Configuration dictionary containing RabbitMQ settings.
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
        Return the existing connection.
        """
        if not self.connected or self.connection is None or self.connection.is_closed:
            logging.error("RabbitMQ connection is unavailable. Attempting to reconnect.")
            self.connect() # Attempt to reconnect
            if self.connection is None:
                return None # Return None if reconnect also fails
        return self.connection

    def is_connected(self):
        """
        Returns True if the connection is established, False otherwise.
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
        try:
            url = f"amqp://{os.getenv('RABBITMQ_USER')}:{os.getenv('RABBITMQ_PASS')}@{os.getenv('RABBITMQ_HOST')}:{os.getenv('RABBITMQ_PORT')}/"
            connection = await aio_pika.connect_robust(url)
            await connection.close()
            return {"status": "healthy"}
        except Exception as e:
            return {"status": "unhealthy", "error": str(e)}
