import os
import yaml
from typing import Any, Optional


class ConfigLoader:
    def __init__(self):
        self.common_config = {}
        self.shared_config = {}
        self.private_config = {}
        self.env_config = dict(os.environ)

    def load(self, service_name: str):
        base_path = "/app/configmaps" if os.path.exists("/app/configmaps") else "/home/stocksadmin/stocksblitz/configmaps"

        paths = {
            "common": f"{base_path}/common-config.yaml",
            "shared": f"{base_path}/shared-config.yaml",
            "private": f"{base_path}/{service_name}-config.yaml",
        }

        for name, path in paths.items():
            if os.path.exists(path):
                with open(path, "r") as f:
                    data = yaml.safe_load(f) or {}
                    if name == "common":
                        self.common_config.update(data)
                    elif name == "shared":
                        self.shared_config.update(data)
                    elif name == "private":
                        self.private_config.update(data)

    def get(self, key: str, default: Optional[Any] = None, scope: str = "private") -> Any:
        if scope == "private":
            return self.private_config.get(key, self.env_config.get(key, default))
        elif scope == "shared":
            return self.shared_config.get(key, self.env_config.get(key, default))
        elif scope == "common":
            return self.common_config.get(key, self.env_config.get(key, default))
        elif scope == "all":
            return (
                self.private_config.get(key)
                or self.shared_config.get(key)
                or self.common_config.get(key)
                or self.env_config.get(key, default)
            )
        else:
            return default


# Global singleton – should be used only *after* .load(service_name) is called
config_loader = ConfigLoader()
