
import pandas as pd
from datetime import datetime, date, timezone


def utc_now() -> datetime:
    """Returns current UTC time as a timezone-aware datetime object."""
    return datetime.now(timezone.utc)


def format_datetime_utc(dt: datetime) -> str:
    if dt is None:
        return ""
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")



