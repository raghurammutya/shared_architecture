from enum import Enum, IntEnum

class UserRole(str, Enum):
    ADMIN = "ADMIN"
    EDITOR = "EDITOR" 
    VIEWER = "VIEWER"

class Status(IntEnum):
    PENDING = 1
    ACTIVE = 2
    INACTIVE = 3
    DELETED = 4

class Currency(Enum):
    USD = "USD"
    EUR = "EUR"
    INR = "INR"

class Timezone(Enum):
    UTC = "UTC"
    IST = "Asia/Kolkata"
    PST = "America/Los_Angeles"

class Environment(Enum):
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"

class AccountStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    PENDING = "pending"
    SUSPENDED = "suspended"

class Exchange(str, Enum):
    NSE = "NSE"
    BSE = "BSE"
    MCX = "MCX"
    NFO = "NFO"
    CDS = "CDS"
    BFO = "BFO"

class TradeType(str, Enum):
    BUY = "BUY"
    SELL = "SELL"

class OrderType(str, Enum):
    MARKET = "MARKET"
    LIMIT = "LIMIT"
    STOP_LOSS_MARKET = "SL-M"
    STOP_LOSS_LIMIT = "SL"

class OrderStatus(str, Enum):
    """Order status following state machine pattern"""
    NEW = "NEW"                           # Order created but not sent to broker
    PENDING = "PENDING"                   # Order sent to broker, awaiting acceptance
    OPEN = "OPEN"                         # Order accepted and active in market
    PARTIALLY_FILLED = "PARTIALLY_FILLED" # Order partially executed
    COMPLETE = "COMPLETE"                 # Order fully executed
    CANCELLED = "CANCELLED"               # Order cancelled
    REJECTED = "REJECTED"                 # Order rejected by broker/exchange
    
    @classmethod
    def get_terminal_states(cls):
        """Get states that represent order completion"""
        return {cls.COMPLETE, cls.CANCELLED, cls.REJECTED}
    
    @classmethod
    def get_active_states(cls):
        """Get states where order is still active"""
        return {cls.PENDING, cls.OPEN, cls.PARTIALLY_FILLED}
    
    def is_terminal(self) -> bool:
        """Check if this status is terminal (order finished)"""
        return self in self.get_terminal_states()
    
    def is_active(self) -> bool:
        """Check if this status is active (order still processing)"""
        return self in self.get_active_states()

class OrderLifecycleAction(str, Enum):
    """Actions that can be performed on orders"""
    PLACE = "PLACE"
    MODIFY = "MODIFY"
    CANCEL = "CANCEL"
    FILL = "FILL"          # Partial or complete fill
    REJECT = "REJECT"
    SQUARE_OFF = "SQUARE_OFF"

class PollingFrequency(Enum):
    """Polling frequency based on order age"""
    IMMEDIATE = 1          # 1 second - first 10 seconds
    FREQUENT = 2           # 2 seconds - next 30 seconds  
    NORMAL = 5             # 5 seconds - after 40 seconds
    SLOW = 10              # 10 seconds - very old orders
    
    @classmethod
    def get_frequency_for_age(cls, age_seconds: int):
        """Get appropriate polling frequency based on order age"""
        if age_seconds <= 10:
            return cls.IMMEDIATE
        elif age_seconds <= 40:
            return cls.FREQUENT
        elif age_seconds <= 300:  # 5 minutes
            return cls.NORMAL
        else:
            return cls.SLOW

class ProductType(str, Enum):
    CNC = "CNC"  # Cash and Carry
    NRML = "NRML" # Normal
    MIS = "MIS"  # Margin Intraday Squareoff
    CO = "CO"   # Cover Order
    BO = "BO"   # Bracket Order

class Variety(str, Enum):
    REGULAR = "REGULAR"
    CO = "CO"
    BO = "BO"
    AMO = "AMO"

class Validity(str, Enum):
    DAY = "DAY"
    IOC = "IOC"

class OrderTransitionType(str, Enum):
    NONE = "NONE"
    HOLDING_TO_POSITION = "HOLDING_TO_POSITION"
    POSITION_TO_HOLDING = "POSITION_TO_HOLDING"

class OrderEvent(str, Enum):
    ORDER_PLACED = "ORDER_PLACED"
    ORDER_ACCEPTED = "ORDER_ACCEPTED"
    ORDER_PARTIALLY_FILLED = "ORDER_PARTIALLY_FILLED"
    ORDER_FILLED = "ORDER_FILLED"
    ORDER_REJECTED = "ORDER_REJECTED"
    ORDER_CANCELLED = "ORDER_CANCELLED"
    ORDER_MODIFIED = "ORDER_MODIFIED" 

class ChargeCategory(str, Enum):
    MARGIN = "MARGIN"
    SETTLEMENT = "SETTLEMENT" 
    BROKERAGE = "BROKERAGE"
    TAX = "TAX"
    REGULATORY = "REGULATORY"
    FUND = "FUND"
    OTHER = "OTHER"

class TransactionType(str, Enum):
    SPAN_MARGIN_BLOCKED = "SPAN_MARGIN_BLOCKED"
    SPAN_MARGIN_REVERSED = "SPAN_MARGIN_REVERSED"
    EXPOSURE_MARGIN_BLOCKED = "EXPOSURE_MARGIN_BLOCKED"
    EXPOSURE_MARGIN_REVERSED = "EXPOSURE_MARGIN_REVERSED"
    NET_OBLIGATION = "NET_OBLIGATION"
    BROKERAGE_CHARGE = "BROKERAGE_CHARGE"
    STT_CHARGE = "STT_CHARGE"
    OTHER = "OTHER"

class BrokerName(str, Enum):
    ZERODHA = "ZERODHA"
    UPSTOX = "UPSTOX"
    ICICI_BREEZE = "ICICI_BREEZE"
    ANGEL_ONE = "ANGEL_ONE"

class ExchangeSegment(str, Enum):
    EQUITY = "EQUITY"
    FO = "FO"
    COMMODITY = "COMMODITY"
    CURRENCY = "CURRENCY"

class StrategyStatus(str, Enum):
    ACTIVE = "ACTIVE"
    PAUSED = "PAUSED"
    COMPLETED = "COMPLETED"
    SQUARED_OFF = "SQUARED_OFF"
    DISABLED = "DISABLED"

class StrategyType(str, Enum):
    MANUAL = "MANUAL"
    ALGORITHMIC = "ALGORITHMIC"
    COPY_TRADING = "COPY_TRADING"
    BASKET = "BASKET"
    ARBITRAGE = "ARBITRAGE"
    HEDGE = "HEDGE"
    SCALPING = "SCALPING"
    SWING = "SWING"
    OPTIONS = "OPTIONS"
    FUTURES = "FUTURES"