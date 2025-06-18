# shared_architecture/schemas/trading_operations.py

from pydantic import BaseModel, validator
from typing import List, Optional, Dict, Any
from datetime import datetime
from decimal import Decimal
from enum import Enum

from ..db.models.trading_action_log import ActionType, ActionStatus

class OrderType(str, Enum):
    MARKET = "MARKET"
    LIMIT = "LIMIT"
    STOP_LOSS = "STOP_LOSS"
    STOP_LOSS_MARKET = "STOP_LOSS_MARKET"
    BRACKET = "BRACKET"
    COVER = "COVER"

class OrderSide(str, Enum):
    BUY = "BUY"
    SELL = "SELL"

class ProductType(str, Enum):
    INTRADAY = "INTRADAY"
    DELIVERY = "DELIVERY"
    MARGIN = "MARGIN"

# Order Management Schemas
class PlaceOrderSchema(BaseModel):
    symbol: str
    quantity: int
    price: Optional[Decimal] = None
    order_type: OrderType
    side: OrderSide
    product_type: ProductType
    stop_loss: Optional[Decimal] = None
    target: Optional[Decimal] = None
    trailing_stop_loss: Optional[Decimal] = None
    
    @validator('quantity')
    def validate_quantity(cls, v):
        if v <= 0:
            raise ValueError('Quantity must be positive')
        return v
    
    @validator('price')
    def validate_price(cls, v, values):
        if v is not None and v <= 0:
            raise ValueError('Price must be positive')
        
        # Require price for LIMIT orders
        if values.get('order_type') == OrderType.LIMIT and v is None:
            raise ValueError('Price required for LIMIT orders')
        
        return v

class ModifyOrderSchema(BaseModel):
    broker_order_id: str
    quantity: Optional[int] = None
    price: Optional[Decimal] = None
    order_type: Optional[OrderType] = None
    stop_loss: Optional[Decimal] = None
    target: Optional[Decimal] = None
    
    @validator('quantity')
    def validate_quantity(cls, v):
        if v is not None and v <= 0:
            raise ValueError('Quantity must be positive')
        return v

class CancelOrderSchema(BaseModel):
    broker_order_id: str
    reason: Optional[str] = None

# Position Management Schemas
class SquareOffPositionSchema(BaseModel):
    symbol: str
    quantity: Optional[int] = None  # If None, square off entire position
    price: Optional[Decimal] = None  # Market price if None
    
    @validator('quantity')
    def validate_quantity(cls, v):
        if v is not None and v <= 0:
            raise ValueError('Quantity must be positive')
        return v

# Strategy Management Schemas
class CreateStrategySchema(BaseModel):
    name: str
    description: Optional[str] = None
    strategy_type: str  # MOMENTUM, MEAN_REVERSION, ARBITRAGE, etc.
    instruments: List[str]
    parameters: Dict[str, Any]
    risk_parameters: Dict[str, Any]
    is_active: bool = True
    
    @validator('name')
    def validate_name(cls, v):
        if not v or len(v.strip()) < 3:
            raise ValueError('Strategy name must be at least 3 characters')
        return v.strip()

class ModifyStrategySchema(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    parameters: Optional[Dict[str, Any]] = None
    risk_parameters: Optional[Dict[str, Any]] = None
    is_active: Optional[bool] = None

class AdjustStrategySchema(BaseModel):
    strategy_id: str
    adjustment_type: str  # SCALE_UP, SCALE_DOWN, CHANGE_PARAMS, etc.
    adjustment_parameters: Dict[str, Any]
    reason: Optional[str] = None

class SquareOffStrategySchema(BaseModel):
    strategy_id: str
    reason: Optional[str] = None
    force_exit: bool = False  # Force exit even with losses

# Portfolio Management Schemas
class SquareOffPortfolioSchema(BaseModel):
    reason: str
    confirm_action: bool = False  # Double confirmation required
    exclude_strategies: List[str] = []  # Strategy IDs to exclude
    
    @validator('confirm_action')
    def validate_confirmation(cls, v):
        if not v:
            raise ValueError('Portfolio square-off requires explicit confirmation')
        return v

# Risk Management Schemas
class SetRiskLimitSchema(BaseModel):
    limit_type: str  # From RiskLimitType enum
    limit_value: Decimal
    currency: str = "INR"
    instrument_symbol: Optional[str] = None
    strategy_name: Optional[str] = None
    is_hard_limit: bool = True
    
    @validator('limit_value')
    def validate_limit_value(cls, v):
        if v <= 0:
            raise ValueError('Limit value must be positive')
        return v

# Bulk Operations Schemas
class BulkSquareOffSchema(BaseModel):
    positions: List[str]  # List of symbols or position IDs
    reason: str
    force_exit: bool = False
    
    @validator('positions')
    def validate_positions(cls, v):
        if not v:
            raise ValueError('At least one position must be specified')
        return v

class BulkCancelOrdersSchema(BaseModel):
    order_ids: List[str]
    reason: Optional[str] = None
    
    @validator('order_ids')
    def validate_orders(cls, v):
        if not v:
            raise ValueError('At least one order must be specified')
        return v

# Response Schemas
class TradingActionResponseSchema(BaseModel):
    action_id: int
    action_type: ActionType
    status: ActionStatus
    message: str
    broker_order_id: Optional[str] = None
    executed_at: Optional[datetime] = None
    requires_approval: bool = False
    approval_id: Optional[str] = None
    
    class Config:
        from_attributes = True

class PermissionValidationResponseSchema(BaseModel):
    allowed: bool
    permission_level: str
    required_permission: Optional[str]
    missing_permissions: List[str]
    risk_violations: List[str]
    requires_approval: bool
    error_message: Optional[str]

class RiskLimitStatusSchema(BaseModel):
    limit_type: str
    limit_value: Decimal
    current_usage: Decimal
    usage_percentage: float
    is_breached: bool
    remaining_capacity: Decimal
    
    class Config:
        from_attributes = True

# Approval Workflow Schemas
class ApprovalRequestSchema(BaseModel):
    action_id: int
    approver_notes: Optional[str] = None

class ApprovalResponseSchema(BaseModel):
    action_id: int
    approved: bool
    approver_id: int
    approved_at: datetime
    notes: Optional[str] = None
    
    class Config:
        from_attributes = True