import logging
import os
import sys

def get_logger(service_name: str = "shared_architecture") -> logging.Logger:
    """
    Provides a pre-configured logger instance.
    LOG_LEVEL and LOG_FORMAT are environment configurable.

    LOG_FORMAT:
    - "json": outputs structured JSON logs
    - "default": outputs human-readable logs
    """
    log_level = os.getenv("LOG_LEVEL", "INFO").upper()
    log_format = os.getenv("LOG_FORMAT", "default").lower()

    logger = logging.getLogger(service_name)
    logger.setLevel(log_level)

    # Prevent duplicate handlers
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)

        if log_format == "json":
            import json
            class JsonFormatter(logging.Formatter):
                def format(self, record):
                    log_record = {
                        "level": record.levelname,
                        "message": record.getMessage(),
                        "name": record.name,
                    }
                    return json.dumps(log_record)
            formatter = JsonFormatter()
        else:
            formatter = logging.Formatter("[%(asctime)s] %(levelname)s in %(name)s: %(message)s")

        handler.setFormatter(formatter)
        logger.addHandler(handler)

    return logger
