from enum import Enum, IntEnum, auto

class UserRole(Enum):
    ADMIN = auto()
    EDITOR = auto()
    VIEWER = auto()

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
    POSITION_TO_HOLDING = "POSITION_TO_HOLDING"
    HOLDING_TO_POSITION = "HOLDING_TO_POSITION"

class OrderEvent(str, Enum):
    ORDER_PLACED = "ORDER_PLACED"
    ORDER_ACCEPTED = "ORDER_ACCEPTED"
    ORDER_PARTIALLY_FILLED = "ORDER_PARTIALLY_FILLED"
    ORDER_FILLED = "ORDER_FILLED"
    ORDER_REJECTED = "ORDER_REJECTED"
    ORDER_CANCELLED = "ORDER_CANCELLED"
    ORDER_MODIFIED = "ORDER_MODIFIED" 