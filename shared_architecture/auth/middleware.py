# shared_architecture/auth/middleware.py

from fastapi import Request, HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional, Callable, List
import functools

from .jwt_manager import get_jwt_manager, UserContext, JWTClaims
from ..utils.enhanced_logging import get_logger
from ..exceptions.trade_exceptions import AuthenticationException, AuthorizationException
from ..db.models.user import UserRole

logger = get_logger(__name__)

# HTTP Bearer token scheme
bearer_scheme = HTTPBearer(auto_error=False)

async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme)
) -> UserContext:
    """
    FastAPI dependency to extract current user from JWT token
    """
    if not credentials:
        raise AuthenticationException(
            message="Missing authentication token",
            details={"header": "Authorization"}
        )
    
    try:
        jwt_manager = get_jwt_manager()
        
        # Validate token and extract claims
        claims = await jwt_manager.validate_token(credentials.credentials)
        
        # Extract user context
        user_context = jwt_manager.extract_user_context(claims)
        
        logger.debug(f"Authentication successful for user: {user_context.username}")
        
        return user_context
        
    except AuthenticationException:
        raise
    except Exception as e:
        logger.error(f"Authentication failed: {str(e)}")
        raise AuthenticationException(
            message="Authentication failed",
            details={"error": str(e)}
        )

async def get_optional_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme)
) -> Optional[UserContext]:
    """
    FastAPI dependency to optionally extract current user from JWT token
    Returns None if no token provided or token is invalid
    """
    if not credentials:
        return None
    
    try:
        return await get_current_user(credentials)
    except Exception as e:
        logger.warning(f"Optional authentication failed: {str(e)}")
        return None

def require_permission(permission: str):
    """
    Decorator to require specific permission for endpoint access
    Usage: @require_permission("user:create")
    """
    def decorator(func: Callable):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            # Extract user context from kwargs (injected by FastAPI dependency)
            user_context = None
            for arg in args:
                if isinstance(arg, UserContext):
                    user_context = arg
                    break
            
            # Check in kwargs as well
            if not user_context:
                for key, value in kwargs.items():
                    if isinstance(value, UserContext):
                        user_context = value
                        break
            
            if not user_context:
                raise AuthenticationException(
                    message="User context not found",
                    details={"decorator": "require_permission", "permission": permission}
                )
            
            jwt_manager = get_jwt_manager()
            if not jwt_manager.check_permission(user_context, permission):
                raise AuthorizationException(
                    message=f"Permission denied: {permission}",
                    details={
                        "user": user_context.username,
                        "required_permission": permission,
                        "user_permissions": user_context.permissions
                    }
                )
            
            return await func(*args, **kwargs)
        
        return wrapper
    return decorator

def require_role(role: UserRole):
    """
    Decorator to require minimum role for endpoint access
    Usage: @require_role(UserRole.ADMIN)
    """
    def decorator(func: Callable):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            # Extract user context from kwargs (injected by FastAPI dependency)
            user_context = None
            for arg in args:
                if isinstance(arg, UserContext):
                    user_context = arg
                    break
            
            # Check in kwargs as well
            if not user_context:
                for key, value in kwargs.items():
                    if isinstance(value, UserContext):
                        user_context = value
                        break
            
            if not user_context:
                raise AuthenticationException(
                    message="User context not found",
                    details={"decorator": "require_role", "role": role.value}
                )
            
            jwt_manager = get_jwt_manager()
            if not jwt_manager.check_role(user_context, role):
                raise AuthorizationException(
                    message=f"Role access denied: {role.value}",
                    details={
                        "user": user_context.username,
                        "required_role": role.value,
                        "user_role": user_context.local_user_role.value if user_context.local_user_role else None
                    }
                )
            
            return await func(*args, **kwargs)
        
        return wrapper
    return decorator

def require_permissions(permissions: List[str], require_all: bool = True):
    """
    Decorator to require multiple permissions for endpoint access
    
    Args:
        permissions: List of required permissions
        require_all: If True, user must have ALL permissions. If False, user needs ANY permission.
    
    Usage: 
        @require_permissions(["user:read", "user:update"])
        @require_permissions(["admin:access", "super:access"], require_all=False)
    """
    def decorator(func: Callable):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            # Extract user context
            user_context = None
            for arg in args:
                if isinstance(arg, UserContext):
                    user_context = arg
                    break
            
            if not user_context:
                for key, value in kwargs.items():
                    if isinstance(value, UserContext):
                        user_context = value
                        break
            
            if not user_context:
                raise AuthenticationException(
                    message="User context not found",
                    details={"decorator": "require_permissions", "permissions": permissions}
                )
            
            jwt_manager = get_jwt_manager()
            user_permissions_set = set(user_context.permissions)
            required_permissions_set = set(permissions)
            
            if require_all:
                # User must have all required permissions
                if not required_permissions_set.issubset(user_permissions_set):
                    missing_permissions = required_permissions_set - user_permissions_set
                    raise AuthorizationException(
                        message=f"Missing required permissions: {list(missing_permissions)}",
                        details={
                            "user": user_context.username,
                            "required_permissions": permissions,
                            "missing_permissions": list(missing_permissions),
                            "user_permissions": user_context.permissions
                        }
                    )
            else:
                # User needs at least one of the required permissions
                if not required_permissions_set.intersection(user_permissions_set):
                    raise AuthorizationException(
                        message=f"Access denied: user lacks any of the required permissions",
                        details={
                            "user": user_context.username,
                            "required_permissions": permissions,
                            "user_permissions": user_context.permissions
                        }
                    )
            
            return await func(*args, **kwargs)
        
        return wrapper
    return decorator

class AuthenticationMiddleware:
    """
    ASGI middleware for JWT authentication
    """
    
    def __init__(self, app, exclude_paths: Optional[List[str]] = None):
        self.app = app
        self.exclude_paths = exclude_paths or [
            "/docs", "/redoc", "/openapi.json", "/health", "/health/detailed", "/"
        ]
    
    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        
        path = scope["path"]
        
        # Skip authentication for excluded paths
        if any(path.startswith(excluded) for excluded in self.exclude_paths):
            await self.app(scope, receive, send)
            return
        
        # Extract authorization header
        headers = dict(scope["headers"])
        auth_header = headers.get(b"authorization")
        
        if not auth_header:
            # No auth header - let the endpoint decide if it needs authentication
            await self.app(scope, receive, send)
            return
        
        try:
            # Decode authorization header
            auth_value = auth_header.decode("utf-8")
            if not auth_value.startswith("Bearer "):
                await self.app(scope, receive, send)
                return
            
            token = auth_value.split(" ", 1)[1]
            
            # Validate token
            jwt_manager = get_jwt_manager()
            claims = await jwt_manager.validate_token(token)
            user_context = jwt_manager.extract_user_context(claims)
            
            # Add user context to scope for use in endpoints
            scope["user_context"] = user_context
            
            logger.debug(f"Middleware authenticated user: {user_context.username}")
            
        except Exception as e:
            logger.warning(f"Middleware authentication failed: {str(e)}")
            # Don't block request - let endpoint handle authentication if required
        
        await self.app(scope, receive, send)