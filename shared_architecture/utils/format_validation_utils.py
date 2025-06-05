from typing import Any, Dict
import json

def parse_config(config_path: str) -> Dict[str, Any]:
    """
    Parses a JSON configuration file.

    Args:
        config_path (str): Path to the configuration file.

    Returns:
        dict: Parsed configuration as a dictionary.
    """
    with open(config_path, 'r') as file:
        return json.load(file)


def validate_input(input_data: Dict[str, Any], required_keys: list) -> bool:
    """
    Validates that all required keys are present in the input data.

    Args:
        input_data (dict): Input data to validate.
        required_keys (list): List of required keys.

    Returns:
        bool: True if all keys are present, False otherwise.
    """
    return all(key in input_data for key in required_keys)


def format_output(output_data: Dict[str, Any]) -> str:
    """
    Formats output data as a JSON string.

    Args:
        output_data (dict): Output data to format.

    Returns:
        str: JSON-formatted string of the output data.
    """
    return json.dumps(output_data, indent=2)
