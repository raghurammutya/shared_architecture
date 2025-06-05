import os


def get_secret(key: str, default: str = None) -> str:
    """
    Retrieve a secret from environment variables or fallback default.
    Raises ValueError if the secret is missing and no default is provided.
    """
    value = os.getenv(key, default)
    if value is None:
        raise ValueError(f"Missing required secret: {key}")
    return value
