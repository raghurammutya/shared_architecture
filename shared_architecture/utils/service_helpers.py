import os
import logging
from redis.asyncio import RedisCluster
import socket
from shared_architecture.connections.timescaledb import TimescaleDBConnection
from shared_architecture.connections.rabbitmq import RabbitMQConnection
from shared_architecture.connections.mongodb import MongoDBConnection
from shared_architecture.connections.redis_connection import RedisConnectionFactory
# Setup logging
logging.basicConfig(
    level=os.getenv("LOGGING_LEVEL", "INFO"),
    format="%(asctime)s - %(levelname)s - %(message)s"
)

class AsyncConnectionManager:
    def __init__(self, config: dict):
        self.config = config
        self._timescaledb_conn = None
        self._redis_pool = None
        self._rabbitmq_conn = None
        self._mongodb_conn = None

    async def initialize(self):
        logging.info("Initializing connection pools and shared services...")
        await self._initialize_timescaledb()
        await self._initialize_redis()
        self._initialize_rabbitmq()
        await self._initialize_mongodb()
        logging.info("All connections initialized.")
    async def _initialize_redis(self):
        try:
            redis_factory = RedisConnectionFactory()
            await redis_factory.connect()
            self._redis_pool = await redis_factory.get_connection()
            logger.info("Redis (standalone or cluster) initialized.")
        except Exception as e:
            logger.error(f"Failed to initialize Redis: {e}")
    def _discover_redis_cluster_nodes(self):
        service = self.config.get("redis_cluster_service", "redis-cluster")
        namespace = self.config.get("redis_namespace", "default")
        port = int(self.config.get("redis_port", 6379))
        try:
            hosts = socket.gethostbyname_ex(f"{service}.{namespace}.svc.cluster.local")[2]
            return [{"host": ip, "port": port} for ip in hosts]
        except Exception as e:
            logging.error(f"Failed to discover Redis Cluster nodes: {e}")
            return []

    async def _initialize_redis(self):
        try:
            startup_nodes = self._discover_redis_cluster_nodes()
            if not startup_nodes:
                raise RuntimeError("No Redis cluster nodes found.")

            self._redis_pool = RedisCluster(
                startup_nodes=startup_nodes,
                decode_responses=True,
                max_connections=int(self.config.get("redis_max_connections", 10)),
            )
            await self._redis_pool.ping()
            logging.info("Connected to Redis Cluster successfully.")
        except Exception as e:
            logging.error(f"Redis Cluster connection failed during initialization: {e}")
            self._redis_pool = None

    async def get_redis_connection(self):
        if not self._redis_pool:
            logging.error("Redis cluster connection is not initialized.")
            return None
        try:
            if not await self._redis_pool.ping():
                logging.error("Redis cluster is unreachable.")
                return None
            return self._redis_pool
        except Exception as e:
            logging.error(f"Redis cluster ping failed: {e}")
            return None

    async def _initialize_timescaledb(self):
        """
        Initialize TimescaleDB connection pool.
        """
        try:
            self._timescaledb_conn = TimescaleDBConnection(config=self.config)
            if not self._timescaledb_conn.is_connected():
                logging.warning("TimescaleDB connection failed during initialization.")
        except Exception as e:
            logging.error(f"Error initializing TimescaleDB connection: {e}")



    def _initialize_rabbitmq(self):
        """
        Initialize RabbitMQ connection.
        """
        try:
            self._rabbitmq_conn = RabbitMQConnection(config=self.config)
            self._rabbitmq_conn.connect()
            if not self._rabbitmq_conn.is_connected():
                logging.warning("RabbitMQ connection failed during initialization.")
        except Exception as e:
            logging.error(f"Error initializing RabbitMQ connection: {e}")

    async def _initialize_mongodb(self):
        """
        Initialize MongoDB connection.
        """
        try:
            self._mongodb_conn = MongoDBConnection(config=self.config)
            if not self._mongodb_conn.is_connected():
                logging.warning("MongoDB connection failed during initialization.")
        except Exception as e:
            logging.error(f"MongoDB connection error: {e}")



    def get_timescaledb_session(self):
        """
        Provides a database session from the TimescaleDB pool.
        """
        if not self._timescaledb_conn or not self._timescaledb_conn.is_connected():
            logging.error("TimescaleDB connection is unavailable.")
            return None
        return self._timescaledb_conn.get_session()

    def get_rabbitmq_connection(self):
        """
        Provides the RabbitMQ connection.
        """
        if not self._rabbitmq_conn or not self._rabbitmq_conn.is_connected():
            logging.error("RabbitMQ connection is unavailable.")
            return None
        return self._rabbitmq_conn.get_connection()

    def get_mongodb_connection(self):
        """
        Provides the MongoDB connection.
        """
        if not self._mongodb_conn or not self._mongodb_conn.is_connected():
            logging.error("MongoDB connection is unavailable.")
            return None
        return self._mongodb_conn.get_database()

    async def close_connections(self):
        """
        Closes all connections gracefully.
        """
        try:
            if self._redis_pool:
                await self._redis_pool.close()
                logging.info("Redis connection pool closed.")

            logging.info("All connections closed successfully.")
        except Exception as e:
            logging.error(f"Error closing connections: {e}")


# Singleton instance of ConnectionManager
connection_manager = None


async def initialize_service(service_name: str, config: dict):
    """
    Initializes the ConnectionManager for shared resources.

    Args:
        service_name (str): The name of the microservice.
        config (dict): The configuration for the service.
    """
    global connection_manager
    if connection_manager is None:
        connection_manager = AsyncConnectionManager(config=config)
        await connection_manager.initialize()
        logging.info(f"Service '{service_name}' initialized.")