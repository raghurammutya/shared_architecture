# shared_architecture/schemas/strategy.py

from pydantic import BaseModel, validator
from typing import List, Optional, Dict, Any
from datetime import datetime
from decimal import Decimal

from ..db.models.strategy import StrategyStatus, StrategyType
from ..db.models.strategy_permission import StrategyPermissionType

class StrategyCreateSchema(BaseModel):
    name: str
    description: Optional[str] = None
    strategy_type: StrategyType
    assigned_to_id: Optional[int] = None
    initial_capital: Optional[Decimal] = None
    parameters: Optional[Dict[str, Any]] = None
    risk_parameters: Optional[Dict[str, Any]] = None
    auto_square_off: bool = False
    max_loss_limit: Optional[Decimal] = None
    max_profit_target: Optional[Decimal] = None
    
    @validator('name')
    def validate_name(cls, v):
        if not v or len(v.strip()) < 3:
            raise ValueError('Strategy name must be at least 3 characters')
        return v.strip()
    
    @validator('initial_capital')
    def validate_initial_capital(cls, v):
        if v is not None and v <= 0:
            raise ValueError('Initial capital must be positive')
        return v

class StrategyUpdateSchema(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    parameters: Optional[Dict[str, Any]] = None
    risk_parameters: Optional[Dict[str, Any]] = None
    assigned_to_id: Optional[int] = None
    max_loss_limit: Optional[Decimal] = None
    max_profit_target: Optional[Decimal] = None
    auto_square_off: Optional[bool] = None
    
    @validator('name')
    def validate_name(cls, v):
        if v is not None and len(v.strip()) < 3:
            raise ValueError('Strategy name must be at least 3 characters')
        return v.strip() if v else None

class StrategyResponseSchema(BaseModel):
    id: int
    name: str
    description: Optional[str]
    strategy_type: StrategyType
    status: StrategyStatus
    trading_account_id: int
    organization_id: int
    created_by_id: int
    assigned_to_id: Optional[int]
    trade_service_strategy_id: Optional[str]
    
    # Financial data
    initial_capital: Optional[Decimal]
    current_value: Decimal
    realized_pnl: Decimal
    unrealized_pnl: Decimal
    total_pnl: Decimal
    pnl_percentage: float
    
    # Counts
    active_positions_count: int
    total_orders_count: int
    
    # Parameters
    parameters_dict: Dict[str, Any]
    risk_parameters_dict: Dict[str, Any]
    
    # Risk limits
    max_loss_limit: Optional[Decimal]
    max_profit_target: Optional[Decimal]
    auto_square_off: bool
    
    # Timestamps
    created_at: datetime
    updated_at: Optional[datetime]
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    
    # Status flags
    is_active: bool
    is_running: bool
    can_be_modified: bool
    can_be_started: bool
    can_be_stopped: bool
    
    class Config:
        from_attributes = True

class StrategyListSchema(BaseModel):
    strategies: List[StrategyResponseSchema]
    total: int
    active_count: int
    total_pnl: Decimal
    
class StrategyActionSchema(BaseModel):
    reason: Optional[str] = None
    force_exit: bool = False
    
    @validator('reason')
    def validate_reason(cls, v):
        if v and len(v) > 500:
            raise ValueError('Reason cannot exceed 500 characters')
        return v

class StrategySquareOffSchema(StrategyActionSchema):
    confirm_action: bool = False
    
    @validator('confirm_action')
    def validate_confirmation(cls, v):
        if not v:
            raise ValueError('Strategy square-off requires explicit confirmation')
        return v

class StrategyPermissionCreateSchema(BaseModel):
    user_id: int
    permission_type: StrategyPermissionType
    expires_at: Optional[datetime] = None
    notes: Optional[str] = None
    
    @validator('notes')
    def validate_notes(cls, v):
        if v and len(v) > 500:
            raise ValueError('Notes cannot exceed 500 characters')
        return v

class StrategyPermissionResponseSchema(BaseModel):
    id: int
    user_id: int
    strategy_id: int
    permission_type: StrategyPermissionType
    granted_by_id: int
    granted_at: datetime
    expires_at: Optional[datetime]
    is_active: bool
    notes: Optional[str]
    is_valid: bool
    
    class Config:
        from_attributes = True

class StrategyDetailsSchema(BaseModel):
    """Comprehensive strategy details from trade_service"""
    strategy: StrategyResponseSchema
    positions: List[Dict[str, Any]]
    orders: List[Dict[str, Any]]
    holdings: List[Dict[str, Any]]
    margins: Dict[str, Any]
    analytics: Dict[str, Any]
    
class BulkStrategyActionSchema(BaseModel):
    strategy_ids: List[int]
    action_type: str  # start, stop, square_off
    reason: Optional[str] = None
    force_exit: bool = False
    
    @validator('strategy_ids')
    def validate_strategies(cls, v):
        if not v:
            raise ValueError('At least one strategy must be specified')
        return v
    
    @validator('action_type')
    def validate_action_type(cls, v):
        if v not in ['start', 'stop', 'square_off']:
            raise ValueError('Invalid action type')
        return v

class StrategyAnalyticsSchema(BaseModel):
    """Strategy performance analytics"""
    strategy_id: int
    period: str  # daily, weekly, monthly
    metrics: Dict[str, Any]
    
    class Config:
        from_attributes = True

class StrategyComparisonSchema(BaseModel):
    """Compare multiple strategies"""
    strategy_ids: List[int]
    comparison_metrics: List[str]
    period: str = "monthly"
    
    @validator('strategy_ids')
    def validate_strategies(cls, v):
        if len(v) < 2:
            raise ValueError('At least two strategies required for comparison')
        return v