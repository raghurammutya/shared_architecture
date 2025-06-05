from typing import List
from shared_architecture.config.config_loader import config_loader


def validate_required_keys(required_keys: List[str]) -> None:
    """
    Validate that all required configuration keys are present.
    Raises ValueError if any key is missing.
    """
    missing_keys = [key for key in required_keys if config_loader.get(key) is None]
    if missing_keys:
        raise ValueError(f"Missing required configuration keys: {', '.join(missing_keys)}")
