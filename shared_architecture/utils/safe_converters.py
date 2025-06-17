from typing import Dict, Any, Optional,Type,Union
import pandas as pd
from datetime import datetime,date
import math

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
    """
    Safely converts a value to an integer, handling None and potential errors.

    Args:
        value: The value to convert.
        default: The value to return if conversion fails or if value is None.

    Returns:
        The converted integer, or the default if conversion fails or value is None.
    """
    if value is None:
        return default
    try:
        return int(value)
    except (ValueError, TypeError):
        return default
    except Exception as e:
        print(f"Unexpected error converting to int: {e}")  # Log unexpected errors
        return default
def safe_convert_float(value: Any, default: Optional[float] = None) -> Optional[float]:
    """
    Safely converts a value to a float, handling None and potential errors.

    Args:
        value: The value to convert.
        default: The value to return if conversion fails or if value is None.

    Returns:
        The converted float, or the default if conversion fails or value is None.
    """
    if value is None:
        return default
    try:
        return float(value)
    except (ValueError, TypeError):
        return default
    except Exception as e:
        print(f"Unexpected error converting to float: {e}")  # Log unexpected errors
        return default
def safe_convert_bool(value: Any, default: Optional[bool] = None) -> Optional[bool]:
    """
    Safely converts a value to a boolean, handling None and various representations.

    Args:
        value: The value to convert.
        default: The value to return if conversion fails or if value is None.

    Returns:
        The converted boolean, or the default if conversion fails or value is None.
    """
    if value is None:
        return default
    if isinstance(value, (int, float)):
        return bool(value)  # 0 -> False, non-zero -> True
    elif isinstance(value, str):
        if value.lower() in ("true", "1", "yes"):
            return True
        elif value.lower() in ("false", "0", "no"):
            return False
        else:
            return default  # Return default for invalid strings
    else:
        try:
            return bool(value)  # General boolean conversion
        except (ValueError, TypeError):
            return default
        except Exception as e:
            print(f"Unexpected error converting to bool: {e}")
            return default
def safe_parse_datetime(date_input: Union[str, datetime, date, pd.Timestamp, int, float, None]) -> Optional[datetime]:
    """
    Safely parses a string, datetime-like object, or Unix timestamp into a datetime object.
    Handles pd.NaT, None values, and Unix timestamps.
    """
    if date_input is None or date_input == '' or pd.isna(date_input):
        return None
    
    if isinstance(date_input, datetime):
        return date_input
    
    if isinstance(date_input, date):
        return datetime(date_input.year, date_input.month, date_input.day)
    
    # Handle Unix timestamps (int or float)
    if isinstance(date_input, (int, float)):
        try:
            # Check if it's likely a Unix timestamp (reasonable range)
            if 1000000000 <= date_input <= 9999999999:  # Year 2001 to 2286 (seconds)
                return datetime.fromtimestamp(date_input)
            elif 1000000000000 <= date_input <= 9999999999999:  # Milliseconds
                return datetime.fromtimestamp(date_input / 1000)
            else:
                return None
        except (ValueError, TypeError, OSError):
            return None
    
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
            '%d%m%Y',
            '%Y-%m-%dT%H:%M:%S',
            '%Y-%m-%dT%H:%M:%SZ',
            '%Y-%m-%dT%H:%M:%S.%f',
            '%Y-%m-%dT%H:%M:%S.%fZ'
        ]
        for fmt in formats:
            try:
                return datetime.strptime(date_input, fmt)
            except ValueError:
                pass  # Try the next format
        
        # Try ISO format parsing as fallback
        try:
            return datetime.fromisoformat(date_input.replace('Z', '+00:00'))
        except ValueError:
            pass
    
    return None
def safe_parse_str(value: Any, default: str = '', strip_whitespace: bool = True, max_length: Optional[int] = None) -> str:
    """
    Safely converts any value to a string, handling None and various edge cases.
    
    Args:
        value: The value to convert to string
        default: The default string to return if conversion fails or value is None
        strip_whitespace: Whether to strip leading/trailing whitespace
        max_length: Maximum length of the returned string (truncates if longer)
    
    Returns:
        The converted string, or the default if conversion fails or value is None.
    
    Examples:
        safe_parse_str(None) -> ''
        safe_parse_str(123) -> '123'
        safe_parse_str('  hello  ') -> 'hello'
        safe_parse_str('long text', max_length=5) -> 'long '
        safe_parse_str([], 'fallback') -> 'fallback'
    """
    if value is None:
        return default
    
    # Handle pandas NaN/NaT
    if pd.isna(value):
        return default
    
    try:
        # Convert to string
        if isinstance(value, str):
            result = value
        elif isinstance(value, (int, float)):
            # Handle special float cases
            if isinstance(value, float):
                if math.isnan(value) or math.isinf(value):
                    return default
            result = str(value)
        elif isinstance(value, bool):
            result = str(value)
        elif isinstance(value, (datetime, date)):
            result = value.isoformat()
        elif hasattr(value, '__str__'):
            result = str(value)
        else:
            result = repr(value)
        
        # Strip whitespace if requested
        if strip_whitespace and isinstance(result, str):
            result = result.strip()
        
        # Truncate if max_length is specified
        if max_length is not None and len(result) > max_length:
            result = result[:max_length]
        
        return result
        
    except Exception as e:
        print(f"Unexpected error converting to string: {e}")
        return default