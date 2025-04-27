# Import necessary classes
from .rabbitmq import RabbitMQConnection
from .redis import AsyncRedisConnectionPool
from .timescaledb import TimescaleDBConnection
from .mongodb import MongoDBConnection  # Import the new class

# Define the module's public API
__all__ = [
    "RabbitMQConnection",
    "AsyncRedisConnectionPool",  # Updated name to align with your async Redis class
    "TimescaleDBConnection",
    "MongoDBConnection",  # Add MongoDBConnection to __all__
]