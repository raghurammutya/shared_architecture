
import os
import yaml
from typing import Any, Optional


class ConfigLoader:
    """
    Loads merged configuration from Kubernetes-mounted ConfigMaps or environment variables as fallback.

    Order of precedence:
    1. /etc/config/common-config.yaml
    2. /etc/config/{service_name}-config.yaml
    3. /etc/config/private-config.yaml
    4. Environment variables

    Later files override earlier ones.
    """

    def __init__(self, service_name: Optional[str] = None, config_dir: Optional[str] = "/etc/config"):
        self.config = {}

        filenames = [
            "common-config.yaml",
            f"{service_name}-config.yaml" if service_name else None,
            "private-config.yaml"
        ]

        for filename in filter(None, filenames):
            file_path = os.path.join(config_dir, filename)
            if os.path.exists(file_path):
                with open(file_path, "r") as file:
                    loaded = yaml.safe_load(file) or {}
                    self.config.update(loaded)

        # Fallback to env if key not found in config file
        self._env_fallback = dict(os.environ)

    def get(self, key: str, default: Optional[Any] = None) -> Any:
        return self.config.get(key, self._env_fallback.get(key, default))


# Global Singleton Loader, service_name must be set before use
config_loader = ConfigLoader(service_name=os.getenv("SERVICE_NAME", "default"))
