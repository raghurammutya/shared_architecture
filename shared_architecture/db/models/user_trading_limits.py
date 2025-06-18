# shared_architecture/db/models/user_trading_limits.py

from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Boolean, Numeric, Enum, Time
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from shared_architecture.db.base import Base
import enum
from datetime import datetime, time

class TradingLimitType(enum.Enum):
    """Types of trading limits that can be set for users"""
    
    # FINANCIAL LIMITS
    DAILY_TRADING_LIMIT = "daily_trading_limit"           # Max trading value per day
    SINGLE_TRADE_LIMIT = "single_trade_limit"             # Max value per trade
    DAILY_LOSS_LIMIT = "daily_loss_limit"                 # Max loss per day
    MONTHLY_TRADING_LIMIT = "monthly_trading_limit"       # Max trading value per month
    POSITION_VALUE_LIMIT = "position_value_limit"         # Max total position value
    
    # QUANTITY LIMITS
    DAILY_ORDER_COUNT = "daily_order_count"               # Max orders per day
    SINGLE_ORDER_QUANTITY = "single_order_quantity"       # Max quantity per order
    MAX_OPEN_POSITIONS = "max_open_positions"             # Max open positions
    
    # INSTRUMENT LIMITS
    ALLOWED_INSTRUMENTS = "allowed_instruments"           # Whitelist of instruments
    BLOCKED_INSTRUMENTS = "blocked_instruments"           # Blacklist of instruments
    ALLOWED_SEGMENTS = "allowed_segments"                 # Cash, F&O, Currency, Commodity
    
    # TIME-BASED LIMITS
    TRADING_HOURS = "trading_hours"                       # Allowed trading hours
    ALLOWED_DAYS = "allowed_days"                         # Allowed trading days
    
    # LEVERAGE LIMITS
    MAX_LEVERAGE = "max_leverage"                         # Maximum leverage allowed
    MARGIN_UTILIZATION = "margin_utilization"            # Max margin utilization %
    
    # STRATEGY LIMITS
    STRATEGY_ALLOCATION = "strategy_allocation"           # Max allocation per strategy
    MAX_STRATEGIES = "max_strategies"                     # Max number of strategies

class LimitScope(enum.Enum):
    """Scope of the trading limit"""
    ACCOUNT_WIDE = "account_wide"                         # Applies to entire trading account
    STRATEGY_SPECIFIC = "strategy_specific"               # Applies to specific strategy
    INSTRUMENT_SPECIFIC = "instrument_specific"           # Applies to specific instrument

class LimitEnforcement(enum.Enum):
    """How strictly the limit is enforced"""
    HARD_LIMIT = "hard_limit"                            # Blocks action if exceeded
    SOFT_LIMIT = "soft_limit"                            # Warns but allows action
    ADVISORY = "advisory"                                # Only logs for monitoring

class UserTradingLimit(Base):
    """
    User-specific trading limits within trading accounts
    Allows granular control over what users can do within each trading account
    """
    __tablename__ = "user_trading_limits"
    __table_args__ = {'schema': 'tradingdb'}
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Scope and relationships
    user_id = Column(Integer, ForeignKey("tradingdb.users.id"), nullable=False, index=True)
    trading_account_id = Column(Integer, ForeignKey("tradingdb.trading_accounts.id"), nullable=False, index=True)
    organization_id = Column(Integer, ForeignKey("tradingdb.organizations.id"), nullable=False, index=True)
    strategy_id = Column(Integer, ForeignKey("tradingdb.strategies.id"), nullable=True, index=True)  # Optional
    
    # Limit definition
    limit_type = Column(Enum(TradingLimitType), nullable=False, index=True)
    limit_scope = Column(Enum(LimitScope), default=LimitScope.ACCOUNT_WIDE, nullable=False)
    enforcement_type = Column(Enum(LimitEnforcement), default=LimitEnforcement.HARD_LIMIT, nullable=False)
    
    # Limit values
    limit_value = Column(Numeric(precision=15, scale=2), nullable=True)      # Numeric limits
    limit_percentage = Column(Numeric(precision=5, scale=2), nullable=True)  # Percentage limits
    limit_count = Column(Integer, nullable=True)                             # Count limits
    limit_text = Column(String, nullable=True)                               # Text limits (instruments, etc.)
    
    # Time-based limits
    start_time = Column(Time, nullable=True)                                 # Daily start time
    end_time = Column(Time, nullable=True)                                   # Daily end time
    allowed_days = Column(String, nullable=True)                             # Comma-separated days
    
    # Current usage tracking
    current_usage_value = Column(Numeric(precision=15, scale=2), default=0, nullable=False)
    current_usage_count = Column(Integer, default=0, nullable=False)
    usage_reset_frequency = Column(String, default="daily", nullable=False)  # daily, weekly, monthly
    last_reset_at = Column(DateTime(timezone=True), nullable=True)
    
    # Management
    set_by_id = Column(Integer, ForeignKey("tradingdb.users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Status
    is_active = Column(Boolean, default=True, nullable=False)
    override_allowed = Column(Boolean, default=False, nullable=False)        # Can user request override
    auto_reset = Column(Boolean, default=True, nullable=False)               # Auto-reset usage
    
    # Breach tracking
    breach_count = Column(Integer, default=0, nullable=False)
    last_breach_at = Column(DateTime(timezone=True), nullable=True)
    consecutive_breaches = Column(Integer, default=0, nullable=False)
    
    # Notifications
    warning_threshold = Column(Numeric(precision=5, scale=2), default=80.0)  # Warn at 80% usage
    notify_on_breach = Column(Boolean, default=True, nullable=False)
    
    # Relationships
    user = relationship("User", foreign_keys=[user_id])
    trading_account = relationship("TradingAccount")
    organization = relationship("Organization")
    strategy = relationship("Strategy")
    set_by = relationship("User", foreign_keys=[set_by_id])
    
    @property
    def usage_percentage(self):
        """Calculate current usage as percentage of limit"""
        if self.limit_value and self.limit_value > 0:
            return (self.current_usage_value / self.limit_value) * 100
        elif self.limit_count and self.limit_count > 0:
            return (self.current_usage_count / self.limit_count) * 100
        return 0
    
    @property
    def is_breached(self):
        """Check if limit is currently breached"""
        if self.limit_value:
            return self.current_usage_value > self.limit_value
        elif self.limit_count:
            return self.current_usage_count > self.limit_count
        return False
    
    @property
    def should_warn(self):
        """Check if warning threshold is reached"""
        return self.usage_percentage >= self.warning_threshold
    
    @property
    def remaining_limit(self):
        """Calculate remaining limit capacity"""
        if self.limit_value:
            return max(0, self.limit_value - self.current_usage_value)
        elif self.limit_count:
            return max(0, self.limit_count - self.current_usage_count)
        return 0
    
    def reset_usage(self):
        """Reset usage counters"""
        self.current_usage_value = 0
        self.current_usage_count = 0
        self.last_reset_at = datetime.utcnow()
        self.consecutive_breaches = 0
    
    def check_time_restriction(self, check_time: datetime = None) -> bool:
        """Check if current time is within allowed trading hours"""
        if not check_time:
            check_time = datetime.now()
        
        # Check time of day
        if self.start_time and self.end_time:
            current_time = check_time.time()
            if not (self.start_time <= current_time <= self.end_time):
                return False
        
        # Check day of week
        if self.allowed_days:
            allowed_days_list = [day.strip().upper() for day in self.allowed_days.split(',')]
            current_day = check_time.strftime('%A').upper()
            if current_day not in allowed_days_list:
                return False
        
        return True
    
    def check_instrument_restriction(self, instrument: str) -> bool:
        """Check if instrument is allowed for trading"""
        if self.limit_type == TradingLimitType.ALLOWED_INSTRUMENTS:
            if self.limit_text:
                allowed_instruments = [inst.strip().upper() for inst in self.limit_text.split(',')]
                return instrument.upper() in allowed_instruments
            return False
        
        elif self.limit_type == TradingLimitType.BLOCKED_INSTRUMENTS:
            if self.limit_text:
                blocked_instruments = [inst.strip().upper() for inst in self.limit_text.split(',')]
                return instrument.upper() not in blocked_instruments
            return True
        
        return True