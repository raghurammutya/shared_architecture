from enum import Enum

class UserRole(str, Enum):
    ADMIN = "admin"
    USER = "user"
    MANAGER = "manager"

class AccountStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    PENDING = "pending"
    SUSPENDED = "suspended"
