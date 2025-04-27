import os
import base64
import json
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

def decode_secret(encoded_value):
    """
    Decode a base64-encoded secret value.
    Args:
        encoded_value (str): Base64 encoded string.
    Returns:
        str: Decoded secret value.
    """
    try:
        return base64.b64decode(encoded_value).decode("utf-8")
    except Exception as e:
        logging.error(f"Error decoding secret: {e}")
        raise ValueError("Failed to decode secret.")

def get_secret(secret_name: str, key: str) -> str:
    """
    Retrieve a specific secret from an environment variable or external source.
    Args:
        secret_name (str): The environment variable containing the secrets.
        key (str): The specific key inside the secret to retrieve.
    Returns:
        str: Decoded secret value.
    """
    try:
        secret_data = os.getenv(secret_name, "{}")  # Default to empty JSON object
        secrets = json.loads(secret_data)          # Parse JSON data
        encoded_value = secrets.get(key, None)     # Retrieve the specific key
        if not encoded_value:
            logging.warning(f"Secret key '{key}' not found in '{secret_name}'.")
            return None
        return decode_secret(encoded_value)        # Decode the base64-encoded secret
    except Exception as e:
        logging.error(f"Error retrieving secret '{key}' from '{secret_name}': {e}")
        raise ValueError("Failed to retrieve secret.")

def validate_secrets(required_keys: list, secret_name: str) -> None:
    """
    Validate if all required secret keys are available in the environment.
    Args:
        required_keys (list): List of keys to validate.
        secret_name (str): The environment variable containing the secrets.
    Raises:
        RuntimeError: If any required key is missing.
    """
    try:
        secret_data = os.getenv(secret_name, "{}")
        secrets = json.loads(secret_data)
        for key in required_keys:
            if key not in secrets:
                logging.error(f"Missing required secret key: {key} in {secret_name}")
                raise RuntimeError(f"Required secret key '{key}' is missing.")
        logging.info(f"All required keys validated successfully in {secret_name}.")
    except Exception as e:
        logging.error(f"Error validating secrets in {secret_name}: {e}")
        raise RuntimeError("Failed to validate secrets.")