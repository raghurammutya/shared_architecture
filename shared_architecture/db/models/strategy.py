# shared_architecture/db/models/strategy.py

from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Boolean, Text, Numeric, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from shared_architecture.db.base import Base
import enum
import json

class StrategyStatus(enum.Enum):
    """Status of a trading strategy"""
    DRAFT = "draft"                 # Strategy created but not activated
    ACTIVE = "active"               # Strategy is running
    PAUSED = "paused"               # Strategy temporarily stopped
    COMPLETED = "completed"         # Strategy finished successfully
    STOPPED = "stopped"             # Strategy manually stopped
    ERROR = "error"                 # Strategy stopped due to error
    SQUARED_OFF = "squared_off"     # All positions closed

class StrategyType(enum.Enum):
    """Types of trading strategies"""
    MOMENTUM = "momentum"
    MEAN_REVERSION = "mean_reversion"
    ARBITRAGE = "arbitrage"
    BREAKOUT = "breakout"
    SCALPING = "scalping"
    SWING = "swing"
    MANUAL = "manual"              # Manual trading grouped as strategy
    BASKET = "basket"              # Basket trading
    PAIRS = "pairs"                # Pairs trading
    CUSTOM = "custom"              # Custom algorithm

class Strategy(Base):
    """
    Trading Strategy model - represents a cohesive trading strategy within a trading account
    Strategies group related positions, orders, holdings and margins from trade_service
    """
    __tablename__ = "strategies"
    __table_args__ = {'schema': 'tradingdb'}
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Basic strategy information
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    strategy_type = Column(Enum(StrategyType), nullable=False, index=True)
    status = Column(Enum(StrategyStatus), default=StrategyStatus.DRAFT, nullable=False, index=True)
    
    # Ownership and organization
    trading_account_id = Column(Integer, ForeignKey("tradingdb.trading_accounts.id"), nullable=False, index=True)
    organization_id = Column(Integer, ForeignKey("tradingdb.organizations.id"), nullable=False, index=True)
    created_by_id = Column(Integer, ForeignKey("tradingdb.users.id"), nullable=False)
    assigned_to_id = Column(Integer, ForeignKey("tradingdb.users.id"), nullable=True)  # Who manages this strategy
    
    # Strategy identification in trade_service
    trade_service_strategy_id = Column(String, nullable=True, unique=True, index=True)  # ID from trade_service
    
    # Strategy parameters (stored as JSON)
    parameters = Column(Text, nullable=True)  # Strategy-specific parameters
    risk_parameters = Column(Text, nullable=True)  # Risk management parameters
    
    # Financial tracking
    initial_capital = Column(Numeric(precision=15, scale=2), nullable=True)
    current_value = Column(Numeric(precision=15, scale=2), default=0)
    realized_pnl = Column(Numeric(precision=15, scale=2), default=0)
    unrealized_pnl = Column(Numeric(precision=15, scale=2), default=0)
    
    # Position and order counts
    active_positions_count = Column(Integer, default=0)
    total_orders_count = Column(Integer, default=0)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    started_at = Column(DateTime(timezone=True), nullable=True)  # When strategy was activated
    completed_at = Column(DateTime(timezone=True), nullable=True)  # When strategy finished
    
    # Strategy lifecycle
    is_active = Column(Boolean, default=True, nullable=False)
    auto_square_off = Column(Boolean, default=False)  # Auto square-off at end of day
    max_loss_limit = Column(Numeric(precision=15, scale=2), nullable=True)
    max_profit_target = Column(Numeric(precision=15, scale=2), nullable=True)
    
    # Relationships
    trading_account = relationship("TradingAccount", back_populates="strategies")
    organization = relationship("Organization")
    created_by = relationship("User", foreign_keys=[created_by_id])
    assigned_to = relationship("User", foreign_keys=[assigned_to_id])
    
    permissions = relationship("StrategyPermission", back_populates="strategy", cascade="all, delete-orphan")
    action_logs = relationship("StrategyActionLog", back_populates="strategy", cascade="all, delete-orphan")
    
    @property
    def total_pnl(self):
        """Calculate total P&L (realized + unrealized)"""
        return (self.realized_pnl or 0) + (self.unrealized_pnl or 0)
    
    @property
    def pnl_percentage(self):
        """Calculate P&L as percentage of initial capital"""
        if not self.initial_capital or self.initial_capital == 0:
            return 0
        return (self.total_pnl / self.initial_capital) * 100
    
    @property
    def parameters_dict(self):
        """Get parameters as dictionary"""
        if not self.parameters:
            return {}
        try:
            return json.loads(self.parameters)
        except:
            return {}
    
    @property
    def risk_parameters_dict(self):
        """Get risk parameters as dictionary"""
        if not self.risk_parameters:
            return {}
        try:
            return json.loads(self.risk_parameters)
        except:
            return {}
    
    def set_parameters(self, params_dict):
        """Set parameters from dictionary"""
        self.parameters = json.dumps(params_dict) if params_dict else None
    
    def set_risk_parameters(self, risk_dict):
        """Set risk parameters from dictionary"""
        self.risk_parameters = json.dumps(risk_dict) if risk_dict else None
    
    @property
    def is_running(self):
        """Check if strategy is currently running"""
        return self.status == StrategyStatus.ACTIVE
    
    @property
    def can_be_modified(self):
        """Check if strategy can be modified"""
        return self.status in [StrategyStatus.DRAFT, StrategyStatus.PAUSED]
    
    @property
    def can_be_started(self):
        """Check if strategy can be started"""
        return self.status in [StrategyStatus.DRAFT, StrategyStatus.PAUSED]
    
    @property
    def can_be_stopped(self):
        """Check if strategy can be stopped"""
        return self.status == StrategyStatus.ACTIVE