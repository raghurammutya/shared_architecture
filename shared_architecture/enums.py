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
