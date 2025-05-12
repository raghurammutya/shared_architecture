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
import logging
logger = logging.getLogger(__name__)
# This will be filled dynamically by each connector
OPEN_CONNECTIONS = []   
def register_connection(conn):
    """Optional: Track open connections (live or mock) for shutdown."""
    OPEN_CONNECTIONS.append(conn)
def close_all_connections():
    """
    Gracefully close all tracked connections that have a `.close()` or `.disconnect()` method.
    """
    for conn in OPEN_CONNECTIONS:
        try:
            if hasattr(conn, "close") and callable(conn.close):
                conn.close()
            elif hasattr(conn, "disconnect") and callable(conn.disconnect):
                conn.disconnect()
        except Exception as e:
            logger.warning(f"Failed to close connection {conn}: {e}")