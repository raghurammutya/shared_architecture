import os
import base64
import json
import logging

logger = logging.getLogger(__name__)

def decode_secret(encoded_value: str) -> str:
    """
    Decode a base64-encoded secret value.
    """
    try:
        return base64.b64decode(encoded_value).decode("utf-8")
    except Exception as e:
        logger.error(f"Error decoding secret: {e}")
        raise ValueError("Failed to decode secret.")

def get_secret(secret_name: str, key: str) -> str:
    """
    Retrieve a specific secret from an environment variable.
    """
    try:
        secret_data = os.getenv(secret_name, "{}")
        secrets = json.loads(secret_data)
        encoded_value = secrets.get(key, None)
        if not encoded_value:
            logger.warning(f"Secret key '{key}' not found in '{secret_name}'.")
            return None
        return decode_secret(encoded_value)
    except Exception as e:
        logger.error(f"Error retrieving secret '{key}' from '{secret_name}': {e}")
        raise ValueError("Failed to retrieve secret.")

def validate_secrets(required_keys: list, secret_name: str) -> None:
    """
    Validate if all required secret keys are present.
    """
    try:
        secret_data = os.getenv(secret_name, "{}")
        secrets = json.loads(secret_data)
        for key in required_keys:
            if key not in secrets:
                logger.error(f"Missing required secret key: {key} in {secret_name}")
                raise RuntimeError(f"Required secret key '{key}' is missing.")
        logger.info(f"All required keys validated successfully in {secret_name}.")
    except Exception as e:
        logger.error(f"Error validating secrets in {secret_name}: {e}")
        raise RuntimeError("Failed to validate secrets.")

def get_k8s_secret(key: str, default: str = None) -> str:
    """
    Retrieve a Kubernetes Secret mounted as a file.
    """
    try:
        path = f"/var/run/secrets/{key}"
        if os.path.exists(path):
            with open(path, "r") as f:
                return f.read().strip()
        return os.getenv(key, default)
    except Exception as e:
        logger.error(f"Failed to read Kubernetes Secret {key}: {e}")
        return default
