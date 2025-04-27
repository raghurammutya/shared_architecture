class BaseConnection:
    def __init__(self, config_manager):
        """
        Initialize the base connection with the shared config manager.
        Args:
            config_manager: Instance of ConfigManager.
        """
        self.config = config_manager.get_service_configs()

    def get_config_value(self, key, default=None):
        """
        Retrieve a configuration value with an optional default.
        Args:
            key: The config key to retrieve.
            default: The default value if the key is not found.
        Returns:
            str: Config value or default.
        """
        return self.config.get(key, default)