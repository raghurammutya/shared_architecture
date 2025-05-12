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

class Environment:
    def __init__(self):
        self.use_mocks = get_env("USE_MOCKS", "false", bool)
        self.env = get_env("ENV", "dev")
        self.service_name = get_env("SERVICE_NAME", "microservice")

ENV = Environment()
