# shared_architecture/config/config_loader.py

import os

def get_env(key: str, default=None, cast_type=str):
    value = os.getenv(key, default)
    if value is None:
        raise EnvironmentError(f"Missing required environment variable: {key}")
    try:
        if cast_type == bool:
            return value.lower() in ("1", "true", "yes")
        return cast_type(value)
    except Exception as e:
        raise ValueError(f"Environment variable '{key}' must be castable to {cast_type}: {e}")