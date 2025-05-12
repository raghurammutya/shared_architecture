from sqlalchemy.types import TypeDecorator, DateTime
import pytz
import datetime
from dateutil.parser import parse as parse_datetime

class TimezoneAwareDateTime(TypeDecorator):
    impl = DateTime(timezone=True)

    def __init__(self, timezone=None, **kwargs):
        super().__init__(**kwargs)
        self.timezone = pytz.timezone(timezone or "Asia/Kolkata")

    def process_bind_param(self, value, dialect):
        """
        Convert input value to timezone-aware datetime before storing in DB.
        Handles:
        - None or empty
        - String inputs (with dateutil parsing)
        - datetime.date (converted to datetime)
        - naive datetime (assumes UTC)
        """
        if not value:
            return None

        if isinstance(value, str):
            try:
                value = parse_datetime(value)
            except Exception as e:
                raise ValueError(f"Invalid datetime string: {value}") from e

        if isinstance(value, datetime.date) and not isinstance(value, datetime.datetime):
            value = datetime.datetime.combine(value, datetime.time.min)

        if not isinstance(value, datetime.datetime):
            raise TypeError(f"Unsupported type for DateTime: {type(value)}")

        if value.tzinfo is None:
            value = value.replace(tzinfo=datetime.timezone.utc)

        return value.astimezone(self.timezone)

    def process_result_value(self, value, dialect):
        """Convert stored UTC datetime to configured timezone on read."""
        if value:
            if isinstance(value, datetime.date) and not isinstance(value, datetime.datetime):
                value = datetime.datetime(value.year, value.month, value.day)  # Convert `date` to `datetime`
                value = value.replace(tzinfo=datetime.timezone.utc)  # Explicitly set UTC timezone

            return value.astimezone(self.timezone)  # Convert to the desired timezone
        
        return value
