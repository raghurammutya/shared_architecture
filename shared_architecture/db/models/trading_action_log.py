# shared_architecture/db/models/trading_action_log.py

from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Boolean, Text, Numeric, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from shared_architecture.db.base import Base
import enum

class ActionType(enum.Enum):
    """Types of trading actions that can be performed"""
    
    # Order Actions
    PLACE_ORDER = "place_order"
    MODIFY_ORDER = "modify_order"
    CANCEL_ORDER = "cancel_order"
    
    # Position Actions
    SQUARE_OFF_POSITION = "square_off_position"
    
    # Strategy Actions
    CREATE_STRATEGY = "create_strategy"
    MODIFY_STRATEGY = "modify_strategy"
    ADJUST_STRATEGY = "adjust_strategy"
    SQUARE_OFF_STRATEGY = "square_off_strategy"
    DELETE_STRATEGY = "delete_strategy"
    
    # Portfolio Actions
    SQUARE_OFF_PORTFOLIO = "square_off_portfolio"
    
    # Risk Management Actions
    SET_RISK_LIMIT = "set_risk_limit"
    OVERRIDE_RISK_LIMIT = "override_risk_limit"
    
    # Bulk Actions
    BULK_SQUARE_OFF = "bulk_square_off"
    BULK_CANCEL = "bulk_cancel"

class ActionStatus(enum.Enum):
    """Status of trading actions"""
    PENDING = "pending"
    EXECUTED = "executed"
    FAILED = "failed"
    REJECTED = "rejected"
    CANCELLED = "cancelled"

class TradingActionLog(Base):
    """
    Comprehensive audit log for all trading actions
    Tracks who did what, when, and with what result
    """
    __tablename__ = "trading_action_logs"
    __table_args__ = {'schema': 'tradingdb'}
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Action details
    action_type = Column(Enum(ActionType), nullable=False, index=True)
    action_status = Column(Enum(ActionStatus), default=ActionStatus.PENDING, nullable=False)
    
    # User and context
    user_id = Column(Integer, ForeignKey("tradingdb.users.id"), nullable=False, index=True)
    trading_account_id = Column(Integer, ForeignKey("tradingdb.trading_accounts.id"), nullable=False, index=True)
    organization_id = Column(Integer, ForeignKey("tradingdb.organizations.id"), nullable=False, index=True)
    
    # Action metadata
    instrument_symbol = Column(String, nullable=True, index=True)  # Stock/option symbol
    quantity = Column(Numeric(precision=15, scale=2), nullable=True)
    price = Column(Numeric(precision=15, scale=4), nullable=True)
    order_type = Column(String, nullable=True)  # MARKET, LIMIT, etc.
    
    # References to external systems
    broker_order_id = Column(String, nullable=True, index=True)  # Order ID from broker
    strategy_id = Column(String, nullable=True, index=True)      # Strategy identifier
    parent_order_id = Column(String, nullable=True)             # For modifications
    
    # Detailed action data (JSON)
    action_data = Column(Text, nullable=True)  # Full request/response JSON
    
    # Risk management
    risk_amount = Column(Numeric(precision=15, scale=2), nullable=True)  # Risk amount
    risk_percentage = Column(Numeric(precision=5, scale=2), nullable=True)  # Risk as % of portfolio
    
    # Timestamps and execution details
    requested_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    executed_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    
    # Error details
    error_message = Column(Text, nullable=True)
    error_code = Column(String, nullable=True)
    
    # Approval workflow (for high-risk actions)
    requires_approval = Column(Boolean, default=False, nullable=False)
    approved_by_id = Column(Integer, ForeignKey("tradingdb.users.id"), nullable=True)
    approved_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    user = relationship("User", foreign_keys=[user_id])
    trading_account = relationship("TradingAccount")
    organization = relationship("Organization")
    approved_by = relationship("User", foreign_keys=[approved_by_id])
    
    @property
    def execution_time_seconds(self):
        """Calculate execution time in seconds"""
        if self.executed_at and self.requested_at:
            return (self.executed_at - self.requested_at).total_seconds()
        return None
    
    @property
    def is_high_risk(self):
        """Determine if this is a high-risk action"""
        if self.risk_percentage and self.risk_percentage > 10:  # >10% of portfolio
            return True
        if self.action_type in [ActionType.SQUARE_OFF_PORTFOLIO, ActionType.OVERRIDE_RISK_LIMIT]:
            return True
        return False