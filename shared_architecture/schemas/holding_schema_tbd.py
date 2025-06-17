# trade_service/app/schemas/holding_schema.py
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from decimal import Decimal

class HoldingSchema(BaseModel):
    id: Optional[int] = None
    pseudo_account: Optional[str] = None
    trading_account: Optional[str] = None
    exchange: Optional[str] = None
    symbol: Optional[str] = None
    quantity: Optional[int] = None
    product: Optional[str] = None
    isin: Optional[str] = None
    collateral_qty: Optional[int] = None
    t1_qty: Optional[int] = None
    collateral_type: Optional[str] = None
    pnl: Optional[float] = None
    haircut: Optional[float] = None
    avg_price: Optional[float] = None
    instrument_token: Optional[int] = None
    stock_broker: Optional[str] = None
    platform: Optional[str] = None
    ltp: Optional[float] = None
    currentValue: Optional[float] = None
    totalQty: Optional[int] = None
    timestamp: Optional[datetime] = None
    instrument_key: Optional[str] = None
    strategy_id: Optional[str] = None
    source_strategy_id: Optional[str] = None

    class Config:
        from_attributes = True

class HoldingResponseSchema(BaseModel):
    """Schema for holding response."""
    id: int = Field(..., description="Holding ID")
    user_id: str = Field(..., description="User ID")
    organization_id: str = Field(..., description="Organization ID")
    strategy_id: str = Field(..., description="Strategy ID")
    exchange: str = Field(..., description="Exchange")
    symbol: str = Field(..., description="Symbol")
    quantity: int = Field(..., description="Holding quantity")
    average_price: Decimal = Field(..., description="Average price")
    ltp: Optional[Decimal] = Field(None, description="Last traded price")
    pnl: Optional[Decimal] = Field(None, description="P&L")
    stock_broker: Optional[str] = Field(None, description="Stock broker")
    trading_account: Optional[str] = Field(None, description="Trading account")
    platform: Optional[str] = Field(None, description="Trading platform")
    created_at: datetime = Field(..., description="Created timestamp")
    updated_at: datetime = Field(..., description="Updated timestamp")

    class Config:
        from_attributes = True
        json_encoders = {
            Decimal: lambda v: float(v),
            datetime: lambda v: v.isoformat()
        }

class HoldingListResponseSchema(BaseModel):
    """Schema for list of holdings."""
    holdings: List[HoldingResponseSchema]
    total_count: int
    page: Optional[int] = None
    page_size: Optional[int] = None