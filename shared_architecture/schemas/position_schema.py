# trade_service/app/schemas/position_schema.py
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from decimal import Decimal

class PositionSchema(BaseModel):
    id: Optional[int] = None
    account_id: Optional[str] = None
    atPnl: Optional[float] = None
    buy_avg_price: Optional[float] = None
    buy_quantity: Optional[int] = None
    buy_value: Optional[float] = None
    category: Optional[str] = None
    direction: Optional[str] = None
    exchange: Optional[str] = None
    independent_exchange: Optional[str] = None
    independent_symbol: Optional[str] = None
    ltp: Optional[float] = None
    mtm: Optional[float] = None
    multiplier: Optional[int] = None
    net_quantity: Optional[int] = None
    net_value: Optional[float] = None
    overnight_quantity: Optional[int] = None
    platform: Optional[str] = None
    pnl: Optional[float] = None
    pseudo_account: Optional[str] = None
    realised_pnl: Optional[float] = None
    sell_avg_price: Optional[float] = None
    sell_quantity: Optional[int] = None
    sell_value: Optional[float] = None
    state: Optional[str] = None
    stock_broker: Optional[str] = None
    symbol: Optional[str] = None
    trading_account: Optional[str] = None
    type: Optional[str] = None
    unrealised_pnl: Optional[float] = None
    timestamp: Optional[datetime] = None
    instrument_key: Optional[str] = None
    strategy_id: Optional[str] = None
    source_strategy_id: Optional[str] = None

    class Config:
        from_attributes = True


class PositionResponseSchema(BaseModel):
    """Schema for position response."""
    id: int = Field(..., description="Position ID")
    user_id: str = Field(..., description="User ID")
    organization_id: str = Field(..., description="Organization ID")
    strategy_id: str = Field(..., description="Strategy ID")
    exchange: str = Field(..., description="Exchange")
    symbol: str = Field(..., description="Symbol")
    product_type: str = Field(..., description="Product type")
    quantity: int = Field(..., description="Position quantity")
    average_price: Decimal = Field(..., description="Average price")
    ltp: Optional[Decimal] = Field(None, description="Last traded price")
    pnl: Optional[Decimal] = Field(None, description="P&L")
    realised_pnl: Optional[Decimal] = Field(None, description="Realised P&L")
    unrealised_pnl: Optional[Decimal] = Field(None, description="Unrealised P&L")
    platform: Optional[str] = Field(None, description="Trading platform")
    created_at: datetime = Field(..., description="Created timestamp")
    updated_at: datetime = Field(..., description="Updated timestamp")

    class Config:
        from_attributes = True
        json_encoders = {
            Decimal: lambda v: float(v),
            datetime: lambda v: v.isoformat()
        }

class PositionListResponseSchema(BaseModel):
    """Schema for list of positions."""
    positions: List[PositionResponseSchema]
    total_count: int
    page: Optional[int] = None
    page_size: Optional[int] = None