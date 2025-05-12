import logging
import os
from typing import Dict, Any, Optional, Type, Union
from datetime import datetime,date
import pandas as pd
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

def safe_convert(value: Any, target_type: Type, default: Optional[Any] = None):
    """
    Safely converts a value to the target type, handling None and potential conversion errors.
    """
    if value is None:
        return default
    try:
        return target_type(value)
    except (ValueError, TypeError):
        return default
    except Exception as e:
        print(f"Unexpected error during conversion: {e}")
        return default


def safe_convert_int(value: Any, default: Optional[int] = None) -> Optional[int]:
    if value is None:
        return default
    try:
        return int(value)
    except (ValueError, TypeError):
        return default
    except Exception as e:
        print(f"Unexpected error converting to int: {e}")
        return default


def safe_convert_float(value: Any, default: Optional[float] = None) -> Optional[float]:
    if value is None:
        return default
    try:
        return float(value)
    except (ValueError, TypeError):
        return default
    except Exception as e:
        print(f"Unexpected error converting to float: {e}")
        return default


def safe_convert_bool(value: Any, default: Optional[bool] = None) -> Optional[bool]:
    if value is None:
        return default
    if isinstance(value, (int, float)):
        return bool(value)
    elif isinstance(value, str):
        if value.lower() in ("true", "1", "yes"):
            return True
        elif value.lower() in ("false", "0", "no"):
            return False
        else:
            return default
    else:
        try:
            return bool(value)
        except (ValueError, TypeError):
            return default
        except Exception as e:
            print(f"Unexpected error converting to bool: {e}")
            return default


def safe_parse_datetime(date_input: Union[str, datetime, date, pd.Timestamp]) -> Optional[datetime]:
    if date_input is None or pd.isna(date_input):
        return None
    if isinstance(date_input, datetime):
        return date_input
    if isinstance(date_input, date):
        return datetime(date_input.year, date_input.month, date_input.day)
    if isinstance(date_input, str):
        formats = [
            '%Y-%m-%d %H:%M:%S.%f',
            '%Y-%m-%d %H:%M:%S',
            '%Y-%m-%d',
            '%d-%b-%Y',
            '%d-%m-%Y %H:%M:%S',
            '%d/%m/%Y',
            '%m/%d/%Y',
            '%Y/%m/%d',
            '%Y%m%d',
            '%d%m%Y'
        ]
        for fmt in formats:
            try:
                return datetime.strptime(date_input, fmt)
            except ValueError:
                pass
    return None

def safe_parse_date(date_input: Union[str, date, pd.Timestamp]) -> Optional[date]:
    if date_input is None or pd.isna(date_input):
        return None
    
    if isinstance(date_input, date):
        return date_input  # Already a date object
    
    if isinstance(date_input, str):
        formats = [
            '%Y-%m-%d',
            '%d-%b-%Y',
            '%d-%m-%Y',
            '%d/%m/%Y',
            '%m/%d/%Y',
            '%Y/%m/%d',
            '%Y%m%d',
            '%d%m%Y'
        ]
        for fmt in formats:
            try:
                return datetime.strptime(date_input, fmt).date()  # Convert to date, NOT datetime
            except ValueError:
                pass
    
    return None  # If parsing fails
