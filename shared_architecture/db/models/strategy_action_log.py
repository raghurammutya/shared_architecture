# shared_architecture/db/models/strategy_action_log.py

from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Boolean, Text, Numeric, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from shared_architecture.db.base import Base
import enum

class StrategyActionType(enum.Enum):
    """Types of strategy actions"""
    
    # Strategy lifecycle actions
    CREATE_STRATEGY = "create_strategy"
    MODIFY_STRATEGY = "modify_strategy"
    START_STRATEGY = "start_strategy"
    PAUSE_STRATEGY = "pause_strategy"
    STOP_STRATEGY = "stop_strategy"
    SQUARE_OFF_STRATEGY = "square_off_strategy"
    DELETE_STRATEGY = "delete_strategy"
    
    # Trading actions within strategy
    PLACE_ORDER = "place_order"
    MODIFY_ORDER = "modify_order"
    CANCEL_ORDER = "cancel_order"
    SQUARE_OFF_POSITION = "square_off_position"
    
    # Risk management actions
    SET_RISK_LIMIT = "set_risk_limit"
    OVERRIDE_RISK_LIMIT = "override_risk_limit"
    
    # Permission management
    GRANT_PERMISSION = "grant_permission"
    REVOKE_PERMISSION = "revoke_permission"

class StrategyActionStatus(enum.Enum):
    """Status of strategy actions"""
    PENDING = "pending"
    EXECUTED = "executed"
    FAILED = "failed"
    REJECTED = "rejected"
    CANCELLED = "cancelled"
    APPROVED = "approved"     # For actions requiring approval

class StrategyActionLog(Base):
    """
    Audit log for all strategy-related actions
    Provides complete traceability for strategy operations
    """
    __tablename__ = "strategy_action_logs"
    __table_args__ = {'schema': 'tradingdb'}
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Action details
    action_type = Column(Enum(StrategyActionType), nullable=False, index=True)
    action_status = Column(Enum(StrategyActionStatus), default=StrategyActionStatus.PENDING, nullable=False)
    
    # Context
    user_id = Column(Integer, ForeignKey("tradingdb.users.id"), nullable=False, index=True)
    strategy_id = Column(Integer, ForeignKey("tradingdb.strategies.id"), nullable=False, index=True)
    trading_account_id = Column(Integer, ForeignKey("tradingdb.trading_accounts.id"), nullable=False, index=True)
    organization_id = Column(Integer, ForeignKey("tradingdb.organizations.id"), nullable=False, index=True)
    
    # Action metadata
    instrument_symbol = Column(String, nullable=True, index=True)
    quantity = Column(Numeric(precision=15, scale=2), nullable=True)
    price = Column(Numeric(precision=15, scale=4), nullable=True)
    order_type = Column(String, nullable=True)
    
    # External references
    broker_order_id = Column(String, nullable=True, index=True)
    trade_service_request_id = Column(String, nullable=True, index=True)
    
    # Detailed action data
    action_data = Column(Text, nullable=True)  # Full request/response JSON
    before_state = Column(Text, nullable=True)  # State before action
    after_state = Column(Text, nullable=True)   # State after action
    
    # Risk assessment
    risk_score = Column(String, nullable=True)  # LOW, MEDIUM, HIGH, CRITICAL
    risk_amount = Column(Numeric(precision=15, scale=2), nullable=True)
    
    # Timestamps
    requested_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    executed_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    
    # Error handling
    error_message = Column(Text, nullable=True)
    error_code = Column(String, nullable=True)
    retry_count = Column(Integer, default=0)
    
    # Approval workflow
    requires_approval = Column(Boolean, default=False, nullable=False)
    approved_by_id = Column(Integer, ForeignKey("tradingdb.users.id"), nullable=True)
    approved_at = Column(DateTime(timezone=True), nullable=True)
    approval_notes = Column(Text, nullable=True)
    
    # Client information
    ip_address = Column(String, nullable=True)
    user_agent = Column(String, nullable=True)
    
    # Relationships
    user = relationship("User", foreign_keys=[user_id])
    strategy = relationship("Strategy", back_populates="action_logs")
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
        """Check if this is a high-risk action"""
        if self.risk_score in ["HIGH", "CRITICAL"]:
            return True
        if self.action_type in [
            StrategyActionType.SQUARE_OFF_STRATEGY,
            StrategyActionType.DELETE_STRATEGY,
            StrategyActionType.OVERRIDE_RISK_LIMIT
        ]:
            return True
        return False