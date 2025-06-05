from datetime import datetime, timezone
import pytz
from shared_architecture.config.global_settings import DEFAULT_TIMEZONE

def utc_now() -> datetime:
    """
    Returns the current UTC time with timezone info.
    """
    return datetime.now(timezone.utc)
class TimezoneAwareDateTime:
    """
    Provides utilities to ensure datetime objects are timezone-aware,
    based on the configured default timezone (e.g., Asia/Kolkata).
    """

    def __init__(self, timezone: str = DEFAULT_TIMEZONE):
        self.tz = pytz.timezone(timezone)

    def now(self) -> datetime:
        """
        Returns the current datetime in the configured timezone.
        """
        return datetime.now(self.tz)

    def from_naive(self, dt: datetime) -> datetime:
        """
        Converts a naive datetime (no tzinfo) to the configured timezone.
        """
        if dt.tzinfo is not None:
            raise ValueError("Expected naive datetime object")
        return self.tz.localize(dt)

    def from_utc(self, dt: datetime) -> datetime:
        """
        Converts a UTC datetime to the configured timezone.
        """
        if dt.tzinfo is None:
            dt = pytz.utc.localize(dt)
        return dt.astimezone(self.tz)

    def to_utc(self, dt: datetime) -> datetime:
        """
        Converts a timezone-aware datetime to UTC.
        """
        if dt.tzinfo is None:
            raise ValueError("Expected timezone-aware datetime")
        return dt.astimezone(pytz.utc)
