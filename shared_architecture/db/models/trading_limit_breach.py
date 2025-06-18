# shared_architecture/db/models/trading_limit_breach.py

from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Boolean, Text, Numeric, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from shared_architecture.db.base import Base
import enum

class BreachSeverity(enum.Enum):
    """Severity levels for limit breaches"""
    LOW = "low"                    # Minor breach, continue with warning
    MEDIUM = "medium"              # Moderate breach, requires attention
    HIGH = "high"                  # Serious breach, restrict actions
    CRITICAL = "critical"          # Severe breach, suspend trading

class BreachAction(enum.Enum):
    """Actions taken when breach occurs"""
    WARNING = "warning"            # Send warning notification
    RESTRICT = "restrict"          # Restrict further trading
    SUSPEND = "suspend"            # Suspend user trading
    NOTIFY_ADMIN = "notify_admin"  # Alert organization admin
    AUTO_SQUARE_OFF = "auto_square_off"  # Auto close positions

class BreachStatus(enum.Enum):
    """Status of breach handling"""
    DETECTED = "detected"          # Breach detected
    NOTIFIED = "notified"          # Notifications sent
    RESOLVED = "resolved"          # Breach resolved
    ACKNOWLEDGED = "acknowledged"  # User acknowledged
    ESCALATED = "escalated"        # Escalated to admin

class TradingLimitBreach(Base):
    """
    Records and tracks trading limit breaches
    Enables monitoring, alerting, and automated responses
    """
    __tablename__ = "trading_limit_breaches"
    __table_args__ = {'schema': 'tradingdb'}
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Context
    user_id = Column(Integer, ForeignKey("tradingdb.users.id"), nullable=False, index=True)
    trading_account_id = Column(Integer, ForeignKey("tradingdb.trading_accounts.id"), nullable=False, index=True)
    organization_id = Column(Integer, ForeignKey("tradingdb.organizations.id"), nullable=False, index=True)
    limit_id = Column(Integer, ForeignKey("tradingdb.user_trading_limits.id"), nullable=False, index=True)
    
    # Breach details
    breach_type = Column(String, nullable=False)           # Type of limit breached
    severity = Column(Enum(BreachSeverity), default=BreachSeverity.MEDIUM, nullable=False)
    status = Column(Enum(BreachStatus), default=BreachStatus.DETECTED, nullable=False)
    
    # Breach values
    limit_value = Column(Numeric(precision=15, scale=2), nullable=True)      # Original limit
    attempted_value = Column(Numeric(precision=15, scale=2), nullable=True)  # Value that caused breach
    current_usage = Column(Numeric(precision=15, scale=2), nullable=True)    # Usage at time of breach
    breach_amount = Column(Numeric(precision=15, scale=2), nullable=True)    # Amount over limit
    
    # Action context
    action_attempted = Column(String, nullable=True)       # What user was trying to do
    instrument_symbol = Column(String, nullable=True)      # Instrument involved
    order_details = Column(Text, nullable=True)            # Order details (JSON)
    
    # Response
    actions_taken = Column(String, nullable=True)          # Comma-separated actions
    auto_resolved = Column(Boolean, default=False)         # Was automatically resolved
    override_granted = Column(Boolean, default=False)      # Was override granted
    override_granted_by = Column(Integer, ForeignKey("tradingdb.users.id"), nullable=True)
    
    # Timestamps
    breach_time = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    resolved_time = Column(DateTime(timezone=True), nullable=True)
    acknowledged_time = Column(DateTime(timezone=True), nullable=True)
    
    # Communication
    notifications_sent = Column(String, nullable=True)     # Who was notified
    user_notified = Column(Boolean, default=False)
    admin_notified = Column(Boolean, default=False)
    
    # Notes and resolution
    breach_reason = Column(Text, nullable=True)            # Why breach occurred
    resolution_notes = Column(Text, nullable=True)         # How it was resolved
    prevention_notes = Column(Text, nullable=True)         # How to prevent in future
    
    # Relationships
    user = relationship("User", foreign_keys=[user_id])
    trading_account = relationship("TradingAccount")
    organization = relationship("Organization")
    limit = relationship("UserTradingLimit")
    override_granted_by_user = relationship("User", foreign_keys=[override_granted_by])
    
    @property
    def breach_percentage(self):
        """Calculate breach as percentage over limit"""
        if self.limit_value and self.limit_value > 0:
            return ((self.attempted_value or 0) / self.limit_value) * 100
        return 0
    
    @property
    def is_resolved(self):
        """Check if breach is resolved"""
        return self.status == BreachStatus.RESOLVED
    
    @property
    def resolution_time_minutes(self):
        """Calculate time to resolution in minutes"""
        if self.resolved_time and self.breach_time:
            return (self.resolved_time - self.breach_time).total_seconds() / 60
        return None
    
    def add_action_taken(self, action: BreachAction):
        """Add an action to the actions_taken list"""
        if self.actions_taken:
            actions = self.actions_taken.split(',')
            if action.value not in actions:
                actions.append(action.value)
                self.actions_taken = ','.join(actions)
        else:
            self.actions_taken = action.value
    
    def get_actions_taken(self) -> list:
        """Get list of actions taken"""
        if self.actions_taken:
            return self.actions_taken.split(',')
        return []