# shared_architecture/schemas/trading_limits.py

from pydantic import BaseModel, validator
from typing import List, Optional, Dict, Any
from datetime import datetime, time
from decimal import Decimal

from ..db.models.user_trading_limits import TradingLimitType, LimitScope, LimitEnforcement
from ..db.models.trading_limit_breach import BreachSeverity, BreachStatus, BreachAction

class TradingLimitCreateSchema(BaseModel):
    """Schema for creating new trading limits"""
    user_id: int
    trading_account_id: int
    limit_type: TradingLimitType
    limit_scope: LimitScope = LimitScope.ACCOUNT_WIDE
    enforcement_type: LimitEnforcement = LimitEnforcement.HARD_LIMIT
    
    # Limit values (one of these must be provided based on limit type)
    limit_value: Optional[Decimal] = None
    limit_percentage: Optional[Decimal] = None
    limit_count: Optional[int] = None
    limit_text: Optional[str] = None
    
    # Time-based limits
    start_time: Optional[time] = None
    end_time: Optional[time] = None
    allowed_days: Optional[str] = None
    
    # Strategy-specific limits
    strategy_id: Optional[int] = None
    
    # Configuration
    usage_reset_frequency: str = "daily"
    override_allowed: bool = False
    warning_threshold: Decimal = Decimal("80.0")
    notify_on_breach: bool = True
    
    @validator('limit_value')
    def validate_limit_value(cls, v, values):
        if v is not None and v <= 0:
            raise ValueError('Limit value must be positive')
        return v
    
    @validator('limit_percentage')
    def validate_limit_percentage(cls, v):
        if v is not None and (v <= 0 or v > 100):
            raise ValueError('Limit percentage must be between 0 and 100')
        return v
    
    @validator('limit_count')
    def validate_limit_count(cls, v):
        if v is not None and v <= 0:
            raise ValueError('Limit count must be positive')
        return v
    
    @validator('usage_reset_frequency')
    def validate_reset_frequency(cls, v):
        if v not in ['daily', 'weekly', 'monthly']:
            raise ValueError('Usage reset frequency must be daily, weekly, or monthly')
        return v
    
    @validator('warning_threshold')
    def validate_warning_threshold(cls, v):
        if v < 0 or v > 100:
            raise ValueError('Warning threshold must be between 0 and 100')
        return v

class TradingLimitUpdateSchema(BaseModel):
    """Schema for updating trading limits"""
    limit_value: Optional[Decimal] = None
    limit_percentage: Optional[Decimal] = None
    limit_count: Optional[int] = None
    limit_text: Optional[str] = None
    
    # Time-based limits
    start_time: Optional[time] = None
    end_time: Optional[time] = None
    allowed_days: Optional[str] = None
    
    # Configuration
    enforcement_type: Optional[LimitEnforcement] = None
    usage_reset_frequency: Optional[str] = None
    override_allowed: Optional[bool] = None
    warning_threshold: Optional[Decimal] = None
    notify_on_breach: Optional[bool] = None
    is_active: Optional[bool] = None
    
    @validator('limit_value')
    def validate_limit_value(cls, v):
        if v is not None and v <= 0:
            raise ValueError('Limit value must be positive')
        return v
    
    @validator('warning_threshold')
    def validate_warning_threshold(cls, v):
        if v is not None and (v < 0 or v > 100):
            raise ValueError('Warning threshold must be between 0 and 100')
        return v

class TradingLimitResponseSchema(BaseModel):
    """Schema for trading limit responses"""
    id: int
    user_id: int
    trading_account_id: int
    organization_id: int
    strategy_id: Optional[int]
    
    # Limit definition
    limit_type: TradingLimitType
    limit_scope: LimitScope
    enforcement_type: LimitEnforcement
    
    # Limit values
    limit_value: Optional[Decimal]
    limit_percentage: Optional[Decimal]
    limit_count: Optional[int]
    limit_text: Optional[str]
    
    # Time restrictions
    start_time: Optional[time]
    end_time: Optional[time]
    allowed_days: Optional[str]
    
    # Usage tracking
    current_usage_value: Decimal
    current_usage_count: int
    usage_percentage: float
    remaining_limit: Decimal
    usage_reset_frequency: str
    last_reset_at: Optional[datetime]
    
    # Status
    is_active: bool
    override_allowed: bool
    auto_reset: bool
    is_breached: bool
    should_warn: bool
    
    # Breach tracking
    breach_count: int
    last_breach_at: Optional[datetime]
    consecutive_breaches: int
    
    # Configuration
    warning_threshold: Decimal
    notify_on_breach: bool
    
    # Metadata
    set_by_id: int
    created_at: datetime
    updated_at: Optional[datetime]
    
    class Config:
        from_attributes = True

class TradingLimitListSchema(BaseModel):
    """Schema for listing trading limits"""
    limits: List[TradingLimitResponseSchema]
    total: int
    active_count: int
    breached_count: int
    warning_count: int

class TradingLimitUsageResetSchema(BaseModel):
    """Schema for resetting limit usage"""
    limit_ids: List[int]
    reason: Optional[str] = None
    
    @validator('limit_ids')
    def validate_limit_ids(cls, v):
        if not v:
            raise ValueError('At least one limit ID must be provided')
        return v

class TradingLimitBreachResponseSchema(BaseModel):
    """Schema for limit breach responses"""
    id: int
    user_id: int
    trading_account_id: int
    organization_id: int
    limit_id: int
    
    # Breach details
    breach_type: str
    severity: BreachSeverity
    status: BreachStatus
    
    # Values
    limit_value: Optional[Decimal]
    attempted_value: Optional[Decimal]
    current_usage: Optional[Decimal]
    breach_amount: Optional[Decimal]
    breach_percentage: float
    
    # Context
    action_attempted: Optional[str]
    instrument_symbol: Optional[str]
    breach_reason: Optional[str]
    
    # Response
    actions_taken: List[str]
    auto_resolved: bool
    override_granted: bool
    override_granted_by: Optional[int]
    
    # Timestamps
    breach_time: datetime
    resolved_time: Optional[datetime]
    acknowledged_time: Optional[datetime]
    resolution_time_minutes: Optional[float]
    
    # Status flags
    is_resolved: bool
    
    class Config:
        from_attributes = True

class TradingLimitValidationSchema(BaseModel):
    """Schema for validating trading actions"""
    action_type: str  # place_order, modify_order, square_off, etc.
    instrument: str
    quantity: int
    price: Decimal
    trade_value: Decimal
    order_type: str = "MARKET"
    strategy_id: Optional[int] = None
    
    @validator('quantity')
    def validate_quantity(cls, v):
        if v <= 0:
            raise ValueError('Quantity must be positive')
        return v
    
    @validator('price')
    def validate_price(cls, v):
        if v <= 0:
            raise ValueError('Price must be positive')
        return v
    
    @validator('trade_value')
    def validate_trade_value(cls, v):
        if v <= 0:
            raise ValueError('Trade value must be positive')
        return v

class TradingLimitValidationResultSchema(BaseModel):
    """Schema for validation results"""
    allowed: bool
    violations: List[Dict[str, Any]]
    warnings: List[Dict[str, Any]]
    actions_required: List[BreachAction]
    override_possible: bool
    error_message: Optional[str]
    
    # Breach information
    breaches_detected: List[TradingLimitBreachResponseSchema]

class BulkTradingLimitCreateSchema(BaseModel):
    """Schema for creating multiple trading limits"""
    limits: List[TradingLimitCreateSchema]
    apply_to_all_users: bool = False
    user_ids: Optional[List[int]] = None
    
    @validator('limits')
    def validate_limits(cls, v):
        if not v:
            raise ValueError('At least one limit must be provided')
        return v

class TradingLimitTemplateSchema(BaseModel):
    """Schema for trading limit templates"""
    name: str
    description: Optional[str]
    limit_type: TradingLimitType
    limit_scope: LimitScope = LimitScope.ACCOUNT_WIDE
    enforcement_type: LimitEnforcement = LimitEnforcement.HARD_LIMIT
    
    # Template values
    default_limit_value: Optional[Decimal] = None
    default_limit_count: Optional[int] = None
    default_warning_threshold: Decimal = Decimal("80.0")
    
    # Configuration
    usage_reset_frequency: str = "daily"
    override_allowed: bool = False
    notify_on_breach: bool = True
    
    @validator('name')
    def validate_name(cls, v):
        if not v or len(v.strip()) < 3:
            raise ValueError('Template name must be at least 3 characters')
        return v.strip()

class TradingLimitReportSchema(BaseModel):
    """Schema for trading limit reports"""
    organization_id: int
    report_period: str  # daily, weekly, monthly
    start_date: datetime
    end_date: datetime
    
    # Summary metrics
    total_limits: int
    active_limits: int
    breached_limits: int
    users_with_breaches: int
    total_breaches: int
    
    # Breach breakdown
    breach_by_severity: Dict[str, int]
    breach_by_type: Dict[str, int]
    
    # Usage statistics
    average_usage_percentage: float
    limits_near_breach: int
    
    # Top violators
    top_breach_users: List[Dict[str, Any]]
    most_breached_limits: List[Dict[str, Any]]