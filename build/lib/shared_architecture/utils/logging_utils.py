import logging
import os
import sys
import logging.config
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

def log_info(message):
    logger.info(message)

def log_error(message):
    logger.error(message)

def log_warning(message):
    logger.warning(message)

def log_debug(message):
    logger.debug(message)

def log_exception(message):
    logger.exception(message, exc_info=True) # Log with traceback

def configure_logging(service_name: str = "microservice", log_level: str = "INFO"):
    """
    Configures logging for the microservice.

    Args:
        service_name: The name of the microservice (used in log messages).
        log_level: The desired logging level (e.g., "DEBUG", "INFO", "WARNING", "ERROR").
    """

    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)  # Create the 'logs' directory if it doesn't exist
    log_file = log_dir / f"{service_name}.log"

    # Basic configuration (can be extended)
    logging.basicConfig(
        level=getattr(logging, log_level.upper(), logging.INFO),  # Default to INFO
        format=f"%(asctime)s - %(levelname)s - {service_name} - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[
            logging.StreamHandler(),  # Output to console
            logging.FileHandler(log_file),  # Output to file
        ],
    )
    logging.info(f"Logging configured for {service_name} at level {log_level}")

def init_logging(service_name: str = "shared_service"):
    """
    Initializes a global logger with consistent formatting and level control.
    Logs to stdout by default.

    Example:
        from shared_architecture.utils.logging_utils import init_logging
        init_logging("ticker_service")
    """
    logging_level = os.getenv("LOG_LEVEL", "INFO").upper()
    log_format = f"%(asctime)s - {service_name} - %(levelname)s - %(message)s"

    logging.basicConfig(
        level=logging_level,
        format=log_format,
        handlers=[logging.StreamHandler(sys.stdout)]
    )

    logging.info(f"✅ Logging initialized for {service_name} at level {logging_level}")
if __name__ == "__main__":
    configure_logging("test_service", "DEBUG")
    logging.debug("This is a debug message.")
    logging.info("This is an info message.")
    logging.warning("This is a warning message.")
    logging.error("This is an error message.")
    logging.critical("This is a critical message.")