from shared_architecture.config.config_loader import config_loader

DEFAULT_CURRENCY = config_loader.get("DEFAULT_CURRENCY", "INR")
DEFAULT_TIMEZONE = config_loader.get("DEFAULT_TIMEZONE", "Asia/Kolkata")
DEFAULT_LOCALE = config_loader.get("DEFAULT_LOCALE", "en_IN")
