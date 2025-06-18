# JWT Authentication Usage Guide

This guide explains how to use JWT tokens across microservices in the trading platform using the shared_architecture package.

## Overview

The shared_architecture package provides comprehensive JWT authentication and Keycloak integration that can be used across all microservices for consistent authentication and authorization.

## Key Components

### 1. JWT Manager (`shared_architecture.auth.jwt_manager`)
- Validates JWT tokens from Keycloak
- Extracts user context and permissions
- Maps Keycloak roles to local roles

### 2. Authentication Middleware (`shared_architecture.auth.middleware`)
- FastAPI dependencies for JWT authentication
- Role and permission-based decorators
- Optional authentication support

### 3. Keycloak Integration (`shared_architecture.utils.keycloak_helper`)
- User provisioning and synchronization
- Role management
- Admin operations

## Quick Start

### 1. Initialize Authentication in Your Microservice

Add to your `main.py`:

```python
from shared_architecture.auth import init_jwt_manager
from shared_architecture.utils.keycloak_helper import init_keycloak_manager

# In your startup event
async def startup():
    # Initialize JWT manager (required)
    init_jwt_manager(
        keycloak_url="http://keycloak:8080",
        realm="trading",
        client_id="your-client-id"
    )
    
    # Initialize Keycloak manager (optional - for user provisioning)
    init_keycloak_manager(
        keycloak_url="http://keycloak:8080",
        realm="trading", 
        client_id="your-client-id",
        client_secret="your-client-secret",
        admin_username="admin",
        admin_password="admin-password"
    )
```

### 2. Protect Endpoints with Authentication

```python
from fastapi import Depends
from shared_architecture.auth import get_current_user, UserContext

@app.get("/protected")
async def protected_endpoint(current_user: UserContext = Depends(get_current_user)):
    """This endpoint requires valid JWT token"""
    return {
        "message": f"Hello {current_user.username}",
        "user_id": current_user.user_id,
        "roles": current_user.roles,
        "permissions": current_user.permissions
    }
```

### 3. Use Role-Based Access Control

```python
from shared_architecture.auth import require_role
from shared_architecture.db.models.user import UserRole

@app.post("/admin-only")
@require_role(UserRole.ADMIN)
async def admin_endpoint(current_user: UserContext = Depends(get_current_user)):
    """Only admin users can access this"""
    return {"message": "Admin access granted"}
```

### 4. Use Permission-Based Access Control

```python
from shared_architecture.auth import require_permission

@app.get("/trades")
@require_permission("trade:read")
async def get_trades(current_user: UserContext = Depends(get_current_user)):
    """Requires trade:read permission"""
    return {"trades": []}

@app.post("/trades")
@require_permission("trade:create") 
async def create_trade(current_user: UserContext = Depends(get_current_user)):
    """Requires trade:create permission"""
    return {"trade_id": 123}
```

### 5. Optional Authentication

```python
from shared_architecture.auth import get_optional_user

@app.get("/public-data")
async def public_data(current_user: UserContext = Depends(get_optional_user)):
    """Works with or without authentication"""
    if current_user:
        return {"message": f"Hello {current_user.username}", "premium_data": True}
    else:
        return {"message": "Hello anonymous", "premium_data": False}
```

## JWT Token Structure

### Claims Structure
```json
{
  "sub": "keycloak-user-id",
  "email": "user@example.com", 
  "preferred_username": "username",
  "given_name": "John",
  "family_name": "Doe",
  "realm_access": {
    "roles": ["admin", "user"]
  },
  "resource_access": {
    "your-client-id": {
      "roles": ["client-specific-role"]
    }
  },
  "exp": 1640995200,
  "iat": 1640991600,
  "iss": "http://keycloak:8080/realms/trading"
}
```

### User Context Structure
```python
class UserContext:
    user_id: str           # Keycloak user ID
    email: str            # User email
    username: str         # Username
    first_name: str       # First name
    last_name: str        # Last name  
    roles: List[str]      # Keycloak roles
    permissions: List[str] # Derived permissions
    local_user_role: UserRole # Mapped local role
    groups: List[str]     # User groups
```

## Permission System

### Role Hierarchy
1. **VIEWER** - Read-only access
2. **EDITOR** - Read and limited write access
3. **ADMIN** - Full access

### Default Permission Mapping
```python
ADMIN_PERMISSIONS = [
    "user:create", "user:read", "user:update", "user:delete",
    "group:create", "group:read", "group:update", "group:delete", 
    "trade:create", "trade:read", "trade:update", "trade:delete",
    "system:admin"
]

EDITOR_PERMISSIONS = [
    "user:read", "user:update",
    "group:read",
    "trade:create", "trade:read", "trade:update"
]

VIEWER_PERMISSIONS = [
    "user:read", "group:read", "trade:read"
]
```

## Cross-Microservice Authentication

### 1. Service-to-Service Authentication

```python
import httpx
from shared_architecture.auth import get_current_user

async def call_other_service(current_user: UserContext = Depends(get_current_user)):
    """Forward JWT token to other services"""
    
    # Extract token from request (automatically handled by middleware)
    token = request.headers.get("Authorization")
    
    async with httpx.AsyncClient() as client:
        response = await client.get(
            "http://trade-service/api/trades",
            headers={"Authorization": token}
        )
        return response.json()
```

### 2. Token Forwarding Pattern

```python
from fastapi import Request

async def proxy_request(request: Request, current_user: UserContext = Depends(get_current_user)):
    """Forward authenticated request to another service"""
    
    # Token is automatically validated by get_current_user
    # Forward the same token to downstream service
    
    async with httpx.AsyncClient() as client:
        response = await client.get(
            "http://another-service/api/data",
            headers={"Authorization": request.headers.get("Authorization")}
        )
        return response.json()
```

## Keycloak Integration

### 1. User Provisioning

```python
# Automatic user provisioning on Keycloak login
@app.post("/auth/keycloak-login")
async def keycloak_login(username: str, password: str, db: Session = Depends(get_db)):
    from app.utils.keycloak_helper import authenticate_with_keycloak
    
    # This will:
    # 1. Authenticate with Keycloak
    # 2. Validate JWT token
    # 3. Create/update local user
    # 4. Return comprehensive auth response
    return await authenticate_with_keycloak(username, password, db)
```

### 2. Sync Local User to Keycloak

```python
from shared_architecture.utils.keycloak_helper import get_keycloak_manager

async def sync_user_to_keycloak(user_id: int, password: str):
    """Sync locally created user to Keycloak"""
    keycloak_manager = get_keycloak_manager()
    
    user = db.query(User).filter(User.id == user_id).first()
    success = await keycloak_manager.sync_user_with_keycloak(user, db)
    
    return {"synced": success}
```

## Environment Configuration

Add these to your environment variables:

```bash
# Required for JWT validation
KEYCLOAK_URL=http://keycloak:8080
KEYCLOAK_REALM=trading
KEYCLOAK_CLIENT_ID=your-client-id

# Optional for user provisioning
KEYCLOAK_CLIENT_SECRET=your-client-secret
KEYCLOAK_ADMIN_USERNAME=admin
KEYCLOAK_ADMIN_PASSWORD=admin-password
```

## Common Patterns

### 1. Multi-Tenant Support

```python
@app.get("/tenant-data/{tenant_id}")
async def get_tenant_data(
    tenant_id: str,
    current_user: UserContext = Depends(get_current_user)
):
    # Check if user has access to this tenant
    if tenant_id not in current_user.groups:
        raise HTTPException(403, "Access denied to tenant")
    
    return {"tenant_data": f"Data for {tenant_id}"}
```

### 2. Resource-Based Authorization

```python
@app.get("/trades/{trade_id}")
async def get_trade(
    trade_id: int,
    current_user: UserContext = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    trade = db.query(Trade).filter(Trade.id == trade_id).first()
    
    # Check ownership or admin access
    if trade.user_id != current_user.user_id and "admin" not in current_user.roles:
        raise HTTPException(403, "Access denied to this trade")
    
    return trade
```

### 3. Conditional Logic Based on Roles

```python
@app.get("/dashboard")
async def get_dashboard(current_user: UserContext = Depends(get_current_user)):
    data = {"basic_stats": get_basic_stats()}
    
    if "admin" in current_user.roles:
        data["admin_stats"] = get_admin_stats()
    
    if "trade:read" in current_user.permissions:
        data["trade_summary"] = get_trade_summary()
    
    return data
```

## Testing

### 1. Mock JWT for Testing

```python
import pytest
from shared_architecture.auth import UserContext, UserRole

@pytest.fixture
def mock_admin_user():
    return UserContext(
        user_id="test-user-id",
        email="admin@test.com",
        username="admin",
        first_name="Test",
        last_name="Admin",
        roles=["admin"],
        permissions=["user:create", "user:read", "trade:create"],
        local_user_role=UserRole.ADMIN,
        groups=["test-group"]
    )

def test_protected_endpoint(client, mock_admin_user):
    with client.dependency_overrides({get_current_user: lambda: mock_admin_user}):
        response = client.get("/protected")
        assert response.status_code == 200
```

## Error Handling

The authentication system provides detailed error responses:

```json
{
  "detail": {
    "message": "Token has expired",
    "error_type": "AuthenticationException",
    "details": {
      "exp": 1640995200,
      "current_time": 1640995300
    }
  }
}
```

Common error types:
- `AuthenticationException` - Invalid or missing token
- `AuthorizationException` - Insufficient permissions
- `TokenExpiredException` - Token has expired
- `InvalidTokenException` - Malformed token

## Best Practices

1. **Always validate tokens** - Use `get_current_user` dependency
2. **Use permission-based access** - More granular than role-based
3. **Forward tokens** - Pass JWT tokens between services
4. **Handle graceful degradation** - Use `get_optional_user` for public endpoints
5. **Cache user context** - Avoid re-validating tokens unnecessarily
6. **Monitor auth metrics** - Track authentication success/failure rates
7. **Use resource-based authorization** - Check ownership of resources
8. **Implement proper logout** - Invalidate tokens when needed

## Security Considerations

1. **Token Storage** - Store JWT tokens securely on client side
2. **Token Expiration** - Use short-lived access tokens with refresh tokens
3. **HTTPS Only** - Always use HTTPS in production
4. **Validate Issuer** - Ensure tokens come from trusted Keycloak instance
5. **Monitor Failed Attempts** - Track and alert on authentication failures
6. **Role Principle of Least Privilege** - Give users minimum required permissions
7. **Regular Key Rotation** - Rotate Keycloak signing keys regularly
8. **Audit Logging** - Log all authentication and authorization events