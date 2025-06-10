# trade_service/app/schemas/margin_schema.py
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from decimal import Decimal

class MarginSchema(BaseModel):
    id: Optional[int] = None
    user_id: Optional[int] = None
    adhoc: Optional[float] = None
    available: Optional[float] = None
    category: Optional[str] = None
    collateral: Optional[float] = None
    exposure: Optional[float] = None
    funds: Optional[float] = None
    net: Optional[float] = None
    payin: Optional[float] = None
    payout: Optional[float] = None
    pseudo_account: Optional[str] = None
    realised_mtm: Optional[float] = None
    span: Optional[float] = None
    stock_broker: Optional[str] = None
    total: Optional[float] = None
    trading_account: Optional[str] = None
    unrealised_mtm: Optional[float] = None
    utilized: Optional[float] = None
    active: Optional[bool] = True
    margin_date: Optional[datetime] = None
    instrument_key: Optional[str] = None

    class Config:
        from_attributes = True


class MarginResponseSchema(BaseModel):
    """Schema for margin response."""
    id: int = Field(..., description="Margin ID")
    user_id: str = Field(..., description="User ID")
    organization_id: str = Field(..., description="Organization ID")
    pseudo_account: str = Field(..., description="Pseudo account")
    available_margin: Decimal = Field(..., description="Available margin")
    used_margin: Decimal = Field(..., description="Used margin")
    total_margin: Decimal = Field(..., description="Total margin")
    adhoc_margin: Optional[Decimal] = Field(None, description="Adhoc margin")
    collateral: Optional[Decimal] = Field(None, description="Collateral")
    credit_for_sale: Optional[Decimal] = Field(None, description="Credit for sale")
    option_premium: Optional[Decimal] = Field(None, description="Option premium")
    hold_sale: Optional[Decimal] = Field(None, description="Hold sale")
    exposure: Optional[Decimal] = Field(None, description="Exposure")
    span: Optional[Decimal] = Field(None, description="SPAN margin")
    elm: Optional[Decimal] = Field(None, description="ELM margin")
    var_margin: Optional[Decimal] = Field(None, description="VAR margin")
    platform: Optional[str] = Field(None, description="Trading platform")
    created_at: datetime = Field(..., description="Created timestamp")
    updated_at: datetime = Field(..., description="Updated timestamp")

    class Config:
        from_attributes = True
        json_encoders = {
            Decimal: lambda v: float(v),
            datetime: lambda v: v.isoformat()
        }