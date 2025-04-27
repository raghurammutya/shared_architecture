import logging
import os

# Generic helper for validating environment variables
def validate_env_variable(var_name: str):
    """
    Validate the presence of an environment variable.
    Args:
        var_name (str): Name of the environment variable to validate.
    Returns:
        str: Value of the environment variable if valid.
    Raises:
        ValueError: If the environment variable is not set.
    """
    value = os.getenv(var_name)
    if not value:
        logging.error(f"Environment variable {var_name} is not set.")
        raise ValueError(f"Missing environment variable: {var_name}")
    return value

# Helper for safely converting strings to integers
def safe_int_conversion(value: str, default: int = 0):
    """
    Convert a string value to an integer, with a fallback default.
    Args:
        value (str): Value to convert.
        default (int): Default value if conversion fails.
    Returns:
        int: Converted integer or default value.
    """
    try:
        return int(value)
    except (ValueError, TypeError):
        logging.warning(f"Failed to convert '{value}' to integer. Using default: {default}")
        return default

# Helper for formatting dates
def format_date(date, format_string="%Y-%m-%d"):
    """
    Format a date object into a string.
    Args:
        date (datetime.date or datetime.datetime): Date object to format.
        format_string (str): Desired string format.
    Returns:
        str: Formatted date string.
    """
    try:
        return date.strftime(format_string)
    except Exception as e:
        logging.error(f"Error formatting date: {e}")
        return ""

# General error logging utility
def log_error(exception, context=""):
    """
    Log an error with additional context information.
    Args:
        exception (Exception): The exception to log.
        context (str): Additional context about where the error occurred.
    """
    logging.error(f"Error in {context}: {exception}")