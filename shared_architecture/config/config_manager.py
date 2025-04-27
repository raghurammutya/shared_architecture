import os
import logging
from typing import Dict, Any

logging.basicConfig(
level=logging.INFO,
format="%(asctime)s - %(levelname)s - %(message)s",
)
DEFAULT_POSTGRES_HOST = "localhost"
DEFAULT_POSTGRES_PORT = 5432
DEFAULT_RABBITMQ_URL = "amqp://guest:guest@localhost:5672/"
DEFAULT_REDIS_HOST = "localhost"
DEFAULT_REDIS_PORT = 6379
DEFAULT_MONGO_URI = "mongodb://mongo:27017/mydatabase"
DEFAULT_TICKER_SERVICE_API_KEY = "dummy_api_key"
DEFAULT_ADMIN_API_PAGE_SIZE = 20
class ConfigManager:
    """
    Manages service-specific configuration retrieval.

    This class dynamically loads configurations using environment variables,
    ConfigMaps, or Secrets, providing a centralized interface for configuration
    management across services.
    """

    def __init__(self, service_name: str):
        """
        Initialize ConfigManager with the service name.

        Args:
        service_name (str): The name of the service.
        """
        self.service_name = service_name
        #self.config = self._load_config()
        self.common_config = self._load_common_config() # Load common config
        print(f"common config: {self.common_config}")
        self.service_config = self._load_service_config() # Load service-specific config
        print(f"service_config: {self.service_config}")
        self.config = self._merge_configs() # Merge them

    def get_service_configs(self) -> dict:
        """
        Retrieve service-specific configurations.

        Returns:
        dict: A dictionary of service configurations.
        """
        service_configs = self.config.get("services", {}).get(self.service_name, {})
        if not service_configs:
            logging.warning(f"No specific configurations found for service '{self.service_name}'")
        return service_configs

    def _is_running_in_kubernetes(self) -> bool:
        """
        Detects if the code is running inside a Kubernetes pod.
        """
        return os.getenv("KUBERNETES_SERVICE_HOST") is not None

    def _load_common_config(self) -> dict:
        """
        Loads the common configuration.
        

        Returns:
        dict: Common configuration data.
        """
        config = {
        "postgres_user": os.getenv("SHARED_POSTGRES_USER", "tradmin"),
        "postgres_password": os.getenv("SHARED_POSTGRES_PASSWORD", "tradpass"),
        "postgres_host": os.getenv("SHARED_POSTGRES_HOST", "localhost"),
        "postgres_port": int(os.getenv("SHARED_POSTGRES_PORT", "5432")),
        "postgres_database": os.getenv("SHARED_POSTGRES_PORT", "tradingdb"),
        "rabbitmq_url": os.getenv("SHARED_RABBITMQ_URL", "amqp://guest:guest@localhost:5672/"),
        "redis_host": os.getenv("SHARED_REDIS_HOST", "localhost"),
        "redis_port": int(os.getenv("SHARED_REDIS_PORT", "6379")),
        "mongo_uri": os.getenv(
        "SHARED_MONGO_URI",
        f"mongodb://{os.getenv('SHARED_MONGO_HOST', 'localhost')}:"
        f"{int(os.getenv('SHARED_MONGO_PORT', '27017'))}/"
        f"{os.getenv('SHARED_MONGO_DATABASE', 'mydatabase')}"
        ),
        "mongo_user": os.getenv("SHARED_MONGO_USER", "tradmin"),
        "mongo_password": os.getenv("SHARED_MONGO_PASSWORD", "tradpass"),
        "mongo_host": os.getenv("SHARED_MONGO_HOST", "localhost"),
        "mongo_port": int(os.getenv("SHARED_MONGO_PORT", "27017")),
        "mongo_database": os.getenv("SHARED_MONGO_DATABASE", "tradingdb"),
        "rabbitmq_host": os.getenv("rabbitmq_host", "localhost"),
        "rabbitmq_port": int(os.getenv("rabbitmq_port", 5672)),
        "rabbitmq_user": os.getenv("rabbitmq_user", "guest"),
        "rabbitmq_password": os.getenv("rabbitmq_password", "guest"),
        "BROKER_NAME": os.getenv("BROKER_NAME", "Breeze"),
        "USER_NAME":os.getenv("USER_NAME", "DSINHA"),
        }

        if self._is_running_in_kubernetes():
            config.update(self._load_configmap_data()) # Override with ConfigMap data

        logging.info(f"Loaded configurations for {self.service_name}:")
        for key, value in config.items():
            logging.info(f" {key}: {value} (Source: ConfigMap, env, or default)")

        return config

    def _load_configmap_data(self) -> dict:
        """
        Loads configuration data from environment variables that are injected
        by Kubernetes from a ConfigMap.
        """
        configmap_data = {
        "postgres_host": os.getenv("DATABASE_HOST", "localhost"), # From ConfigMap
        "postgres_port": int(os.getenv("DATABASE_PORT", "5432")), # From ConfigMap
        }
        return configmap_data
    def get_all_configs(self) -> Dict[str, Any]:
        """
        Retrieve all configurations (common and service-specific).


        Returns:
        dict: A dictionary of all configurations.
        """
        return self.config
    def _load_service_config(self) -> Dict[str, Any]:
        """
        Loads the service-specific configuration.


        Returns:
        dict: Service-specific configuration data.
        """
        service_config_data = {}
#        "api_key": os.getenv(f"{self.service_name.upper()}_API_KEY", None),
#        "page_size": int(os.getenv(f"{self.service_name.upper()}_PAGE_SIZE", "10")),
        # ... other service-specific settings ...
#        }
        logging.info(f"Loaded {self.service_name} configurations: {service_config_data}")
        return service_config_data
    def _merge_configs(self) -> Dict[str, Any]:
        """
        Merges the common and service-specific configurations.


        Returns:
        dict: A single dictionary containing all configurations.
        """
        merged_config = self.common_config.copy() # Start with a copy of common config
        logging.info(f"step 1 Merged configurations for {self.service_name}: {merged_config}")
        merged_config.update(self.service_config) # Add/override with service-specific config
        logging.info(f"step 2 Merged configurations for {self.service_name}: {merged_config}")
        logging.info(f"Merged configurations for {self.service_name}: {merged_config}")
        return merged_config
 

    def handle_error(self, error: Exception):
        """
        Handle errors gracefully.


        Args:
        error (Exception): The exception to log.
        """
        logging.error(f"Error: {error}")    