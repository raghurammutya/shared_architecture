# shared_architecture/db/models/risk_limits.py

from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Boolean, Numeric, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from shared_architecture.db.base import Base
import enum

class RiskLimitType(enum.Enum):
    """Types of risk limits that can be set"""
    DAILY_LOSS_LIMIT = "daily_loss_limit"           # Max loss per day
    POSITION_SIZE_LIMIT = "position_size_limit"     # Max position size
    PORTFOLIO_EXPOSURE = "portfolio_exposure"       # Max portfolio exposure
    SINGLE_TRADE_RISK = "single_trade_risk"         # Max risk per trade
    STRATEGY_ALLOCATION = "strategy_allocation"     # Max allocation to strategy
    LEVERAGE_LIMIT = "leverage_limit"               # Max leverage allowed
    DRAWDOWN_LIMIT = "drawdown_limit"               # Max drawdown from peak

class RiskLimit(Base):
    """
    Risk management limits for trading accounts
    Allows fine-grained control over trading exposure
    """
    __tablename__ = "risk_limits"
    __table_args__ = {'schema': 'tradingdb'}
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Scope
    trading_account_id = Column(Integer, ForeignKey("tradingdb.trading_accounts.id"), nullable=False, index=True)
    organization_id = Column(Integer, ForeignKey("tradingdb.organizations.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("tradingdb.users.id"), nullable=True, index=True)  # User-specific limits
    
    # Limit details
    limit_type = Column(Enum(RiskLimitType), nullable=False)
    limit_value = Column(Numeric(precision=15, scale=2), nullable=False)  # Limit amount/percentage
    currency = Column(String, default="INR", nullable=False)
    
    # Context (optional filters)
    instrument_symbol = Column(String, nullable=True)  # Limit for specific instrument
    strategy_name = Column(String, nullable=True)      # Limit for specific strategy
    
    # Status and lifecycle
    is_active = Column(Boolean, default=True, nullable=False)
    is_hard_limit = Column(Boolean, default=True, nullable=False)  # Hard vs soft limit
    
    # Management
    set_by_id = Column(Integer, ForeignKey("tradingdb.users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Monitoring
    current_usage = Column(Numeric(precision=15, scale=2), default=0, nullable=False)
    last_checked_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Breach handling
    breach_count = Column(Integer, default=0, nullable=False)
    last_breach_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    trading_account = relationship("TradingAccount")
    organization = relationship("Organization")
    user = relationship("User", foreign_keys=[user_id])
    set_by = relationship("User", foreign_keys=[set_by_id])
    
    @property
    def usage_percentage(self):
        """Calculate current usage as percentage of limit"""
        if self.limit_value == 0:
            return 0
        return (self.current_usage / self.limit_value) * 100
    
    @property
    def is_breached(self):
        """Check if limit is currently breached"""
        return self.current_usage > self.limit_value
    
    @property
    def remaining_capacity(self):
        """Calculate remaining capacity before limit is hit"""
        return max(0, self.limit_value - self.current_usage)