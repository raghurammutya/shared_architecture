from datetime import datetime
from decimal import Decimal
from typing import Any, Generator, Optional

import pytz
from pydantic import BaseModel

from shared_architecture.config.global_settings import DEFAULT_TIMEZONE, DEFAULT_CURRENCY


class TimezoneAwareDatetime(datetime):
    """Custom datetime that ensures timezone awareness using DEFAULT_TIMEZONE."""

    @classmethod
    def __get_validators__(cls) -> Generator:
        yield cls.validate

    @classmethod
    def validate(cls, value: Any) -> datetime:
        if isinstance(value, datetime):
            dt = value
        elif isinstance(value, str):
            dt = datetime.fromisoformat(value)
        else:
            raise TypeError("Invalid datetime format")

        if dt.tzinfo is None:
            return dt.replace(tzinfo=pytz.timezone(DEFAULT_TIMEZONE))
        return dt.astimezone(pytz.timezone(DEFAULT_TIMEZONE))


class CurrencyAmount(Decimal):
    """Custom decimal for representing currency values with formatting."""

    @classmethod
    def __get_validators__(cls) -> Generator:
        yield cls.validate

    @classmethod
    def validate(cls, value: Any) -> Decimal:
        try:
            return Decimal(str(value))
        except Exception:
            raise ValueError("Invalid currency amount")

    def __str__(self) -> str:
        return f"{DEFAULT_CURRENCY} {self:.2f}"


class BaseSchema(BaseModel):
    """Base schema for all Pydantic models with ORM + enum support."""

    class Config:
        from_attributes = True
        use_enum_values = True
