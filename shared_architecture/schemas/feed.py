from pydantic import BaseModel
from typing import Optional
from shared_architecture.schemas.base import BaseSchema, CurrencyAmount
class FeedBase(BaseModel):
    instrument_key: str
    open: Optional[CurrencyAmount]
    high: Optional[CurrencyAmount]
    low: Optional[CurrencyAmount]
    close: Optional[CurrencyAmount]
    volume: int
    oi: Optional[int] = None
    expirydate: Optional[str] = None
    option_type: Optional[str] = None
    strikeprice: Optional[float] = None

class FeedCreate(FeedBase):
    pass

class Feed(FeedBase):
    time: str

    class Config:
        from_attributes = True