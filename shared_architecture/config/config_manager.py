import os
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

class ConfigManager:
    """
    Centralized configuration manager supporting:
    - Kubernetes ConfigMap overrides
    - Environment variable fallbacks
    - Hardcoded defaults
    """

    def __init__(self, service_name: str):
        self.service_name = service_name
        self.common_config = self._load_common_config()
        self.service_config = self._load_service_config()
        self.config = self._merge_configs()

    def _is_running_in_kubernetes(self) -> bool:
        """Detect if running inside a Kubernetes Pod."""
        return os.getenv("KUBERNETES_SERVICE_HOST") is not None

    def _load_common_config(self) -> Dict[str, Any]:
        """Load shared infrastructure configuration."""
        config = {
            "postgres_user": os.getenv("SHARED_POSTGRES_USER", "tradmin"),
            "postgres_password": os.getenv("SHARED_POSTGRES_PASSWORD", "tradpass"),
            "postgres_host": os.getenv("SHARED_POSTGRES_HOST", "localhost"),
            "postgres_port": int(os.getenv("SHARED_POSTGRES_PORT", "5432")),
            "postgres_database": os.getenv("SHARED_POSTGRES_DB", "tradingdb"),

            "rabbitmq_url": os.getenv("SHARED_RABBITMQ_URL", "amqp://guest:guest@localhost:5672/"),

            "redis_host": os.getenv("SHARED_REDIS_HOST", "localhost"),
            "redis_port": int(os.getenv("SHARED_REDIS_PORT", "6379")),

            "mongo_uri": os.getenv("SHARED_MONGO_URI", "mongodb://localhost:27017/mydatabase"),
            "mongo_user": os.getenv("SHARED_MONGO_USER", "tradmin"),
            "mongo_password": os.getenv("SHARED_MONGO_PASSWORD", "tradpass"),
            "mongo_host": os.getenv("SHARED_MONGO_HOST", "localhost"),
            "mongo_port": int(os.getenv("SHARED_MONGO_PORT", "27017")),
            "mongo_database": os.getenv("SHARED_MONGO_DATABASE", "tradingdb"),

            "rabbitmq_host": os.getenv("RABBITMQ_HOST", "localhost"),
            "rabbitmq_port": int(os.getenv("RABBITMQ_PORT", 5672)),
            "rabbitmq_user": os.getenv("RABBITMQ_USER", "guest"),
            "rabbitmq_password": os.getenv("RABBITMQ_PASSWORD", "guest"),

            "BROKER_NAME": os.getenv("BROKER_NAME", "Breeze"),
            "USER_NAME": os.getenv("USER_NAME", "DSINHA"),
        }

        # Override with ConfigMap if running in Kubernetes
        if self._is_running_in_kubernetes():
            config.update(self._load_configmap_data())

        logger.info(f"Loaded common configuration for {self.service_name}: {config}")
        return config

    def _load_configmap_data(self) -> Dict[str, Any]:
        """Load ConfigMap values injected as environment variables."""
        configmap_data = {
            "postgres_host": os.getenv("DATABASE_HOST", "localhost"),
            "postgres_port": int(os.getenv("DATABASE_PORT", "5432")),
        }
        logger.info(f"Loaded ConfigMap overrides: {configmap_data}")
        return configmap_data

    def _load_service_config(self) -> Dict[str, Any]:
        """Load service-specific configuration."""
        # Extend this section with additional service-specific environment keys as needed.
        service_config_data = {}
        logger.info(f"Loaded {self.service_name} specific configurations: {service_config_data}")
        return service_config_data

    def _merge_configs(self) -> Dict[str, Any]:
        """Merge common and service-specific configurations."""
        merged_config = self.common_config.copy()
        merged_config.update(self.service_config)
        logger.info(f"Merged configuration for {self.service_name}: {merged_config}")
        return merged_config

    def get_service_configs(self) -> Dict[str, Any]:
        """Get service-specific configurations."""
        return self.config.get("services", {}).get(self.service_name, {})

    def get_all_configs(self) -> Dict[str, Any]:
        """Get the full merged configuration."""
        return self.config

    def handle_error(self, error: Exception):
        """Log any configuration-related errors."""
        logger.error(f"Configuration Error: {error}")
