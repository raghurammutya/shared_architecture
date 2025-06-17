from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from shared_architecture.enums import StrategyStatus, StrategyType

class StrategyBase(BaseModel):
    strategy_name: str = Field(..., min_length=1, max_length=200, description="Strategy display name")
    pseudo_account: str = Field(..., min_length=1, max_length=100, description="Trading account identifier")
    organization_id: str = Field(..., min_length=1, max_length=100, description="Organization identifier")
    strategy_type: StrategyType = Field(default=StrategyType.MANUAL, description="Type of strategy")
    description: Optional[str] = Field(None, max_length=1000, description="Strategy description")
    
    # Risk Management
    max_loss_amount: Optional[float] = Field(default=0.0, ge=0, description="Maximum loss limit")
    max_profit_amount: Optional[float] = Field(default=0.0, ge=0, description="Maximum profit target")
    max_positions: Optional[int] = Field(default=10, ge=1, le=100, description="Maximum number of positions")
    
    # Metadata
    tags: Optional[List[str]] = Field(default_factory=list, description="Strategy tags for categorization")
    configuration: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Strategy-specific configuration")
    
    # Auto Square-off
    auto_square_off_enabled: Optional[bool] = Field(default=False, description="Enable automatic square-off")
    square_off_time: Optional[str] = Field(None, pattern=r"^([0-1]?[0-9]|2[0-3]):[0-5][0-9]:[0-5][0-9]$", description="Auto square-off time (HH:MM:SS)")

class StrategyCreate(StrategyBase):
    strategy_id: Optional[str] = Field(None, min_length=1, max_length=50, pattern=r"^[a-zA-Z0-9_-]+$", description="Custom strategy ID (auto-generated if not provided)")
    
    @validator('strategy_id')
    def validate_strategy_id(cls, v):
        if v is not None:
            if not v.replace('_', '').replace('-', '').isalnum():
                raise ValueError('Strategy ID must contain only alphanumeric characters, underscores, and hyphens')
        return v

class StrategyUpdate(BaseModel):
    strategy_name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=1000)
    status: Optional[StrategyStatus] = None
    max_loss_amount: Optional[float] = Field(None, ge=0)
    max_profit_amount: Optional[float] = Field(None, ge=0)
    max_positions: Optional[int] = Field(None, ge=1, le=100)
    tags: Optional[List[str]] = None
    configuration: Optional[Dict[str, Any]] = None
    auto_square_off_enabled: Optional[bool] = None
    square_off_time: Optional[str] = Field(None, pattern=r"^([0-1]?[0-9]|2[0-3]):[0-5][0-9]:[0-5][0-9]$")

class StrategyResponse(StrategyBase):
    strategy_id: str
    status: StrategyStatus
    
    # Performance Metrics
    total_pnl: float = 0.0
    realized_pnl: float = 0.0
    unrealized_pnl: float = 0.0
    total_margin_used: float = 0.0
    
    # Counts
    active_positions_count: int = 0
    total_orders_count: int = 0
    active_orders_count: int = 0
    holdings_count: int = 0
    
    # Timestamps
    created_at: datetime
    updated_at: datetime
    started_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None
    squared_off_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True

class StrategyTaggingRequest(BaseModel):
    entity_ids: List[str] = Field(..., min_items=1, description="List of entity IDs to tag")
    overwrite_existing: bool = Field(default=False, description="Whether to overwrite existing strategy tags")

class StrategyTaggingResponse(BaseModel):
    strategy_id: str
    entity_type: str  # "positions", "orders", "holdings"
    tagged_count: int
    skipped_count: int
    error_count: int
    details: List[Dict[str, Any]] = Field(default_factory=list)

class PositionTaggingRequest(StrategyTaggingRequest):
    pass

class OrderTaggingRequest(StrategyTaggingRequest):
    pass

class HoldingTaggingRequest(StrategyTaggingRequest):
    pass

class StrategySquareOffPreview(BaseModel):
    strategy_id: str
    estimated_orders: List[Dict[str, Any]]
    total_positions: int
    total_holdings: int
    estimated_pnl_impact: float
    margin_release_estimate: float
    warnings: List[str] = Field(default_factory=list)

class StrategySquareOffRequest(BaseModel):
    confirm: bool = Field(..., description="Confirmation flag - must be True to proceed")
    force_market_orders: bool = Field(default=True, description="Use market orders for immediate execution")
    batch_size: int = Field(default=10, ge=1, le=50, description="Number of orders to place per batch")
    dry_run: bool = Field(default=False, description="Preview mode - don't place actual orders")

class StrategySquareOffResponse(BaseModel):
    strategy_id: str
    total_orders_placed: int
    successful_orders: int
    failed_orders: int
    batch_count: int
    estimated_completion_time: str
    order_details: List[Dict[str, Any]]
    errors: List[str] = Field(default_factory=list)

class StrategySummary(BaseModel):
    strategy_id: str
    strategy_name: str
    status: StrategyStatus
    total_pnl: float
    unrealized_pnl: float
    total_margin_used: float
    active_positions_count: int
    active_orders_count: int
    holdings_count: int
    
    # Top positions by PnL
    top_positions: List[Dict[str, Any]] = Field(default_factory=list)
    # Recent orders
    recent_orders: List[Dict[str, Any]] = Field(default_factory=list)
    # Holdings summary
    holdings_summary: Dict[str, Any] = Field(default_factory=dict)

class StrategyListResponse(BaseModel):
    strategies: List[StrategySummary]
    total_count: int
    active_count: int
    total_pnl: float
    total_margin_used: float