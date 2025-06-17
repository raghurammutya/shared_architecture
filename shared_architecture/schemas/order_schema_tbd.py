# trade_service/app/schemas/order_schema.py
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from decimal import Decimal

class OrderSchema(BaseModel):
    id: Optional[int] = None
    amo: Optional[bool] = None
    average_price: Optional[float] = None
    client_id: Optional[str] = None
    disclosed_quantity: Optional[int] = None
    exchange: Optional[str] = None
    exchange_order_id: Optional[str] = None
    exchange_time: Optional[datetime] = None
    filled_quantity: Optional[int] = None
    independent_exchange: Optional[str] = None
    independent_symbol: Optional[str] = None
    modified_time: Optional[datetime] = None
    nest_request_id: Optional[str] = None
    order_type: Optional[str] = None
    parent_order_id: Optional[int] = None
    pending_quantity: Optional[int] = None
    platform: Optional[str] = None
    platform_time: Optional[datetime] = None
    price: Optional[float] = None
    pseudo_account: Optional[str] = None
    publisher_id: Optional[str] = None
    status: Optional[str] = None
    status_message: Optional[str] = None
    stock_broker: Optional[str] = None
    symbol: Optional[str] = None
    trade_type: Optional[str] = None
    trading_account: Optional[str] = None
    trigger_price: Optional[float] = None
    validity: Optional[str] = None
    variety: Optional[str] = None
    timestamp: Optional[datetime] = None
    instrument_key: Optional[str] = None
    strategy_id: Optional[str] = None
    transition_type: Optional[str] = None

    class Config:
        from_attributes = True

class OrderCreateSchema(BaseModel):
    """Schema for creating a new order."""
    user_id: str = Field(..., description="User ID")
    organization_id: str = Field(..., description="Organization ID")
    strategy_id: str = Field(..., description="Strategy ID")
    exchange: str = Field(..., description="Exchange (NSE, BSE, etc.)")
    symbol: str = Field(..., description="Symbol name")
    transaction_type: str = Field(..., description="BUY or SELL")
    order_type: str = Field(..., description="LIMIT, MARKET, SL, SL-M")
    product_type: str = Field(..., description="INTRADAY, DELIVERY, CO, BO")
    quantity: int = Field(..., gt=0, description="Quantity to trade")
    price: Optional[Decimal] = Field(None, description="Price (required for LIMIT orders)")
    trigger_price: Optional[Decimal] = Field(None, description="Trigger price (for SL orders)")
    validity: Optional[str] = Field("DAY", description="Order validity (DAY, IOC, GTT)")
    disclosed_quantity: Optional[int] = Field(None, description="Disclosed quantity")

    class Config:
        json_encoders = {
            Decimal: lambda v: float(v)
        }

class OrderResponseSchema(BaseModel):
    """Schema for order response."""
    id: int = Field(..., description="Order ID")
    user_id: str = Field(..., description="User ID")
    organization_id: str = Field(..., description="Organization ID")
    strategy_id: str = Field(..., description="Strategy ID")
    exchange: str = Field(..., description="Exchange")
    symbol: str = Field(..., description="Symbol")
    transaction_type: str = Field(..., description="Transaction type")
    order_type: str = Field(..., description="Order type")
    product_type: str = Field(..., description="Product type")
    quantity: int = Field(..., description="Quantity")
    price: Optional[Decimal] = Field(None, description="Price")
    trigger_price: Optional[Decimal] = Field(None, description="Trigger price")
    status: str = Field(..., description="Order status")
    filled_quantity: int = Field(0, description="Filled quantity")
    pending_quantity: int = Field(0, description="Pending quantity")
    average_price: Optional[Decimal] = Field(None, description="Average filled price")
    platform_order_id: Optional[str] = Field(None, description="Platform order ID")
    created_at: datetime = Field(..., description="Created timestamp")
    updated_at: datetime = Field(..., description="Updated timestamp")

    class Config:
        from_attributes = True
        json_encoders = {
            Decimal: lambda v: float(v),
            datetime: lambda v: v.isoformat()
        }

class OrderListResponseSchema(BaseModel):
    """Schema for list of orders."""
    orders: List[OrderResponseSchema]
    total_count: int
    page: Optional[int] = None
    page_size: Optional[int] = None