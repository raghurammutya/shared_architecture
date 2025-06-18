# shared_architecture/auth/__init__.py

from .jwt_manager import (
    JWTManager, JWTClaims, UserContext,
    get_jwt_manager, init_jwt_manager
)
from .middleware import (
    get_current_user, get_optional_user,
    require_permission, require_role, require_permissions,
    AuthenticationMiddleware
)

__all__ = [
    "JWTManager", "JWTClaims", "UserContext",
    "get_jwt_manager", "init_jwt_manager",
    "get_current_user", "get_optional_user",
    "require_permission", "require_role", "require_permissions",
    "AuthenticationMiddleware"
]