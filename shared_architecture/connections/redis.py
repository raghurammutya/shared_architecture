import os
import logging
import socket
from shared_architecture.config.config_loader import get_env
from typing import Optional
from redis.asyncio import Redis, RedisCluster
from redis.cluster import ClusterNode

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)


redis_client_instance=None  
async def get_redis_connection():
    global redis_client_instance

    if redis_client_instance is None:
        redis_client_instance = RedisClient()
        await redis_client_instance.connect()

    if await redis_client_instance.is_connected():
        return await redis_client_instance.get_connection()

    raise RuntimeError("❌ Redis connection not available.")
def discover_redis_nodes(service="redis-cluster", namespace="stocksblitz", port=6379):
    """
    Resolves Redis cluster startup nodes for both LOCAL and PROD environments.
    """
    environment = get_env("ENV", "local").lower()
    nodes = []

    if environment == "local":
        # Match your port-forwards here: 6370-6375 on localhost
        ports = [6370, 6371, 6372, 6373, 6374, 6375]
        nodes = [{"host": "localhost", "port": p} for p in ports]
        logging.info(f"🔍 Resolved LOCAL Redis nodes: {nodes}")
        return nodes

    try:
        # For Kubernetes internal resolution in production
        hosts = socket.gethostbyname_ex(f"{service}.{namespace}.svc.cluster.local")[2]
        nodes = [{"host": ip, "port": port} for ip in hosts]
        logging.info(f"🔍 Resolved PROD Redis nodes: {nodes}")
        return nodes
    except Exception as e:
        logging.error(f"❌ Failed to discover Redis Cluster nodes: {e}")
        return []

def get_local_cluster_nodes():
    # Example with port-forwarded nodes
    return [
        ClusterNode("localhost", 6370),
        ClusterNode("localhost", 6371),
        ClusterNode("localhost", 6372),
        ClusterNode("localhost", 6373),
        ClusterNode("localhost", 6374),
        ClusterNode("localhost", 6375),
    ]

def connect_to_redis_cluster():
    try:
        startup_nodes = get_local_cluster_nodes()
        client = RedisCluster(
            startup_nodes=startup_nodes,
            decode_responses=True,
            skip_full_coverage_check=True,
        )
        client.ping()
        logging.info("✅ Connected to Redis Cluster successfully.")
        return client
    except Exception as e:
        logging.error(f"❌ Redis Cluster connection failed: {e}")
        return None
def is_local_environment() -> bool:
    """
    Determine if running in local dev environment.
    """
    return os.getenv("ENV", "local").lower() == "local"


async def connect_to_redis():
    """
    Connect to Redis based on environment (Local or Production).
    Returns a Redis or RedisCluster instance.
    """
    if is_local_environment():
        logging.info("🔍 Using single-node Redis on localhost (port-forwarded).")
        redis_url = f"redis://localhost:{os.getenv('REDIS_PORT', 6379)}"
        client = Redis.from_url(redis_url, decode_responses=True)
    else:
        logging.info("🔍 Discovering Redis Cluster nodes in production.")
        startup_nodes = discover_redis_nodes()
        if not startup_nodes:
            raise RuntimeError("❌ No Redis cluster nodes found.")
        client = RedisCluster(
            startup_nodes=startup_nodes,
            decode_responses=True,
            max_connections=int(os.getenv("REDIS_MAX_CONNECTIONS", 10))
        )
    try:
        await client.ping()
        logging.info("✅ Connected to Redis successfully.")
        return client
    except Exception as e:
        logging.error(f"❌ Failed to connect to Redis: {e}")
        return None
class RedisClient:
    def __init__(self):
        self.redis = None
        self.max_connections = int(get_env("REDIS_MAX_CONNECTIONS", 10))
        self.startup_nodes = self._discover_nodes()

    def _discover_nodes(self):
        """
        Discover nodes based on ENV context.
        Local => localhost with forwarded ports
        Prod  => K8s DNS-based service discovery
        """
        env = get_env("ENV", "local").lower()
        if env == "local":
            logging.info("🔍 Resolving Redis nodes for LOCAL environment.")
            return [
                ClusterNode("localhost", 6370),
                ClusterNode("localhost", 6371),
                ClusterNode("localhost", 6372),
                ClusterNode("localhost", 6373),
                ClusterNode("localhost", 6374),
                ClusterNode("localhost", 6375),
            ]
        else:
            logging.info("🔍 Resolving Redis nodes for K8s PRODUCTION environment.")
            service = get_env("REDIS_SERVICE_NAME", "redis-cluster")
            namespace = get_env("REDIS_NAMESPACE", "default")
            try:
                import socket
                hosts = socket.gethostbyname_ex(f"{service}.{namespace}.svc.cluster.local")[2]
                return [ClusterNode(host, 6379) for host in hosts]
            except Exception as e:
                logging.error(f"❌ Failed to resolve Redis nodes: {e}")
                return []

    def connect(self):
        try:
            if not self.startup_nodes:
                raise RuntimeError("❌ RedisCluster requires at least one startup node.")
            self.redis = RedisCluster(
                startup_nodes=self.startup_nodes,
                decode_responses=True,
                skip_full_coverage_check=True,
            )
            self.redis.ping()  # sync ping
            logging.info("✅ Connected to Redis Cluster successfully.")
        except Exception as e:
            logging.error(f"❌ Redis Cluster connection failed: {e}")
            self.redis = None

    def get_connection(self):
        if not self.redis:
            raise RuntimeError("❌ Redis connection not initialized.")
        return self.redis
    
    async def is_connected(self):
        """
        Check if the Redis Cluster client is connected and responsive.
        """
        if not self.redis:
            return False
        try:
            await self.redis.ping()
            return True
        except Exception:
            return False