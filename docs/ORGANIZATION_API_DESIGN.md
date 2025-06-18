# Organization & Trading Account Management API Design

## Overview

This document outlines the API design for managing organizations, trading accounts, and permissions in the multi-tenant trading platform.

## Database Schema Summary

### Organizations Table
```sql
CREATE TABLE tradingdb.organizations (
    id SERIAL PRIMARY KEY,
    name VARCHAR NOT NULL,
    description TEXT,
    api_key_hash VARCHAR UNIQUE NOT NULL,
    api_key_visible VARCHAR NOT NULL,
    api_key_created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    owner_id INTEGER NOT NULL REFERENCES tradingdb.users(id),
    backup_owner_id INTEGER REFERENCES tradingdb.users(id),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE
);
```

### Trading Accounts Table
```sql
CREATE TABLE tradingdb.trading_accounts (
    id SERIAL PRIMARY KEY,
    login_id VARCHAR NOT NULL,
    pseudo_acc_name VARCHAR NOT NULL,
    broker VARCHAR NOT NULL,
    platform VARCHAR NOT NULL,
    system_id BIGINT NOT NULL,
    system_id_of_pseudo_acc BIGINT NOT NULL,
    license_expiry_date VARCHAR,
    license_days_left INTEGER,
    is_live BOOLEAN DEFAULT FALSE,
    organization_id INTEGER NOT NULL REFERENCES tradingdb.organizations(id),
    assigned_user_id INTEGER REFERENCES tradingdb.users(id),
    is_active BOOLEAN DEFAULT TRUE,
    imported_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_synced_at TIMESTAMP WITH TIME ZONE,
    trading_password_hash VARCHAR,
    additional_credentials VARCHAR
);
```

### Trading Account Permissions Table
```sql
CREATE TABLE tradingdb.trading_account_permissions (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES tradingdb.users(id),
    trading_account_id INTEGER NOT NULL REFERENCES tradingdb.trading_accounts(id),
    organization_id INTEGER NOT NULL REFERENCES tradingdb.organizations(id),
    permission_type VARCHAR NOT NULL, -- PermissionType enum
    granted_by_id INTEGER NOT NULL REFERENCES tradingdb.users(id),
    granted_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    expires_at TIMESTAMP WITH TIME ZONE,
    is_active BOOLEAN DEFAULT TRUE,
    revoked_at TIMESTAMP WITH TIME ZONE,
    revoked_by_id INTEGER REFERENCES tradingdb.users(id),
    notes VARCHAR
);
```

## API Endpoints

### Organization Management

#### 1. Create Organization
```http
POST /api/organizations
Authorization: Bearer <jwt_token>
Content-Type: application/json

{
  "name": "Algo Trading Group",
  "description": "My algorithmic trading organization",
  "api_key": "your-broker-api-key-here",
  "backup_owner_id": 456
}
```

**Response:**
```json
{
  "id": 123,
  "name": "Algo Trading Group",
  "description": "My algorithmic trading organization",
  "masked_api_key": "your-bro****-here",
  "owner_id": 789,
  "backup_owner_id": 456,
  "is_active": true,
  "created_at": "2024-01-15T10:30:00Z",
  "total_accounts": 0
}
```

#### 2. List User's Organizations
```http
GET /api/organizations
Authorization: Bearer <jwt_token>
```

**Response:**
```json
{
  "owned": [
    {
      "id": 123,
      "name": "Algo Trading Group",
      "total_accounts": 5,
      "is_active": true
    }
  ],
  "backup_owner": [
    {
      "id": 124,
      "name": "Secondary Group",
      "total_accounts": 3,
      "is_active": true
    }
  ]
}
```

#### 3. Get Organization Details
```http
GET /api/organizations/{organization_id}
Authorization: Bearer <jwt_token>
```

#### 4. Update Organization
```http
PUT /api/organizations/{organization_id}
Authorization: Bearer <jwt_token>
Content-Type: application/json

{
  "name": "Updated Group Name",
  "api_key": "new-api-key-here"
}
```

#### 5. Delete Organization
```http
DELETE /api/organizations/{organization_id}
Authorization: Bearer <jwt_token>
```

### Trading Account Management

#### 1. Fetch Available Trading Accounts
```http
GET /api/organizations/{organization_id}/available-accounts
Authorization: Bearer <jwt_token>
```

**Response:**
```json
{
  "result": [
    {
      "loginId": "229004",
      "pseudoAccName": "UPSTOX-NM",
      "broker": "Upstox",
      "platform": "UPSTOX_API",
      "licenseExpiryDate": "20-Sep-2023",
      "live": false,
      "systemId": 20739003,
      "systemIdOfPseudoAcc": 20739004,
      "licenseDaysLeft": 0
    }
  ],
  "message": null,
  "status": true
}
```

#### 2. Import Selected Trading Accounts
```http
POST /api/organizations/{organization_id}/import-accounts
Authorization: Bearer <jwt_token>
Content-Type: application/json

{
  "selected_login_ids": ["229004", "AR291"]
}
```

#### 3. List Organization's Trading Accounts
```http
GET /api/organizations/{organization_id}/trading-accounts
Authorization: Bearer <jwt_token>
```

**Response:**
```json
{
  "accounts": [
    {
      "id": 1,
      "login_id": "229004",
      "pseudo_acc_name": "UPSTOX-NM",
      "broker": "Upstox",
      "assigned_user_id": null,
      "is_active": true,
      "account_identifier": "Upstox:229004"
    }
  ],
  "total": 1
}
```

#### 4. Assign Trading Account to User
```http
POST /api/organizations/{organization_id}/assign-accounts
Authorization: Bearer <jwt_token>
Content-Type: application/json

{
  "user_id": 789,
  "trading_account_ids": [1, 2]
}
```

#### 5. Sync Trading Accounts
```http
POST /api/organizations/{organization_id}/sync-accounts
Authorization: Bearer <jwt_token>
```

**Response:**
```json
{
  "fetched_count": 10,
  "updated_count": 8,
  "new_count": 2,
  "deactivated_count": 1
}
```

### Permission Management

#### 1. Grant Account Permissions
```http
POST /api/trading-accounts/{account_id}/permissions
Authorization: Bearer <jwt_token>
Content-Type: application/json

{
  "user_id": 456,
  "permission_type": "view_positions",
  "expires_at": "2024-12-31T23:59:59Z",
  "notes": "Temporary access for analysis"
}
```

#### 2. Bulk Grant Permissions
```http
POST /api/organizations/{organization_id}/bulk-permissions
Authorization: Bearer <jwt_token>
Content-Type: application/json

{
  "user_ids": [456, 789],
  "trading_account_ids": [1, 2, 3],
  "permission_types": ["view_positions", "view_orders"],
  "expires_at": "2024-12-31T23:59:59Z",
  "notes": "Monthly review access"
}
```

#### 3. List User's Accessible Accounts
```http
GET /api/users/me/accessible-accounts
Authorization: Bearer <jwt_token>
```

**Response:**
```json
{
  "assigned_accounts": [
    {
      "id": 1,
      "login_id": "229004",
      "broker": "Upstox",
      "organization_name": "Algo Trading Group"
    }
  ],
  "permitted_accounts": [
    {
      "id": 2,
      "login_id": "AR291",
      "broker": "SAS",
      "permissions": ["view_positions", "view_orders"],
      "organization_name": "Secondary Group"
    }
  ]
}
```

#### 4. Revoke Permission
```http
DELETE /api/trading-account-permissions/{permission_id}
Authorization: Bearer <jwt_token>
```

## Authentication & Authorization Flow

### 1. User Authentication
```
Client → POST /auth/keycloak-login → JWT Token
JWT Token contains:
- user_id (Keycloak ID)
- email
- roles
- permissions
```

### 2. Organization Access Control
```python
def check_organization_access(user_context: UserContext, org_id: int, action: str):
    """
    Organization access rules:
    - Owner: Full access (read, write, delete, manage)
    - Backup Owner: Full access except delete
    - Members: Read access to assigned accounts only
    """
    organization = get_organization(org_id)
    
    if organization.owner_id == user_context.user_id:
        return True  # Owner has full access
    
    if organization.backup_owner_id == user_context.user_id:
        return action != "delete"  # Backup owner can't delete org
    
    # Check if user has any trading accounts in this org
    if action == "read":
        return has_account_access(user_context.user_id, org_id)
    
    return False  # No write access for non-owners
```

### 3. Trading Account Access Control
```python
def check_account_access(user_context: UserContext, account_id: int, permission: str):
    """
    Trading account access rules:
    - Organization Owner/Backup: Full access to all accounts
    - Assigned User: Full access to assigned accounts
    - Permitted User: Access based on granted permissions
    """
    account = get_trading_account(account_id)
    
    # Organization owners have full access
    if is_organization_owner(user_context.user_id, account.organization_id):
        return True
    
    # Assigned user has full access
    if account.assigned_user_id == user_context.user_id:
        return True
    
    # Check explicit permissions
    return has_permission(user_context.user_id, account_id, permission)
```

## Trade Service Integration

### 1. API Key Validation
```python
async def validate_api_key_with_trade_service(api_key: str, user_context: UserContext):
    """
    Validate API key by making test request to trade_service
    """
    headers = {
        "Authorization": f"Bearer {user_context.jwt_token}",
        "X-API-Key": api_key
    }
    
    response = await httpx.get(
        f"{TRADE_SERVICE_URL}/api/trading-accounts",
        headers=headers
    )
    
    return response.status_code == 200
```

### 2. Data Fetching with Authorization
```python
async def fetch_user_trading_data(user_context: UserContext, account_id: int, data_type: str):
    """
    Fetch trading data from trade_service with proper authorization
    """
    # 1. Validate user access to account
    if not check_account_access(user_context, account_id, data_type):
        raise AuthorizationException("Access denied")
    
    # 2. Get organization API key
    account = get_trading_account(account_id)
    api_key = decrypt_api_key(account.organization.api_key_hash)
    
    # 3. Make request to trade_service
    headers = {
        "Authorization": f"Bearer {user_context.jwt_token}",
        "X-API-Key": api_key,
        "X-Account-ID": account.login_id,
        "X-Broker": account.broker
    }
    
    response = await httpx.get(
        f"{TRADE_SERVICE_URL}/api/{data_type}",
        headers=headers
    )
    
    return response.json()
```

## Extended Permission Types

```python
class PermissionType(enum.Enum):
    # READ PERMISSIONS
    VIEW_POSITIONS = "view_positions"
    VIEW_ORDERS = "view_orders"
    VIEW_TRADES = "view_trades"
    VIEW_BALANCE = "view_balance"
    VIEW_PNL = "view_pnl"
    VIEW_ANALYTICS = "view_analytics"
    VIEW_STRATEGIES = "view_strategies"
    VIEW_PORTFOLIO = "view_portfolio"
    FULL_READ = "full_read"
    
    # ORDER MANAGEMENT PERMISSIONS
    PLACE_ORDERS = "place_orders"
    MODIFY_ORDERS = "modify_orders"
    CANCEL_ORDERS = "cancel_orders"
    SQUARE_OFF_POSITIONS = "square_off_positions"
    
    # STRATEGY MANAGEMENT PERMISSIONS
    CREATE_STRATEGY = "create_strategy"
    MODIFY_STRATEGY = "modify_strategy"
    ADJUST_STRATEGY = "adjust_strategy"
    SQUARE_OFF_STRATEGY = "square_off_strategy"
    DELETE_STRATEGY = "delete_strategy"
    
    # PORTFOLIO MANAGEMENT PERMISSIONS
    SQUARE_OFF_PORTFOLIO = "square_off_portfolio"
    MANAGE_PORTFOLIO = "manage_portfolio"
    
    # RISK MANAGEMENT PERMISSIONS
    SET_RISK_LIMITS = "set_risk_limits"
    OVERRIDE_RISK_LIMITS = "override_risk_limits"
    
    # BULK OPERATIONS
    BULK_OPERATIONS = "bulk_operations"
    
    # ADMINISTRATIVE PERMISSIONS
    FULL_TRADING = "full_trading"
    ADMIN_TRADING = "admin_trading"
```

## Complete Strategy Management

### Database Schema - Strategy as First-Class Entity

```sql
-- Strategies within trading accounts
CREATE TABLE tradingdb.strategies (
    id SERIAL PRIMARY KEY,
    name VARCHAR NOT NULL,
    description TEXT,
    strategy_type VARCHAR NOT NULL, -- StrategyType enum
    status VARCHAR NOT NULL, -- StrategyStatus enum
    trading_account_id INTEGER NOT NULL REFERENCES tradingdb.trading_accounts(id),
    organization_id INTEGER NOT NULL REFERENCES tradingdb.organizations(id),
    created_by_id INTEGER NOT NULL REFERENCES tradingdb.users(id),
    assigned_to_id INTEGER REFERENCES tradingdb.users(id),
    trade_service_strategy_id VARCHAR UNIQUE, -- ID from trade_service
    
    -- Strategy parameters (JSON)
    parameters TEXT,
    risk_parameters TEXT,
    
    -- Financial tracking
    initial_capital DECIMAL(15,2),
    current_value DECIMAL(15,2) DEFAULT 0,
    realized_pnl DECIMAL(15,2) DEFAULT 0,
    unrealized_pnl DECIMAL(15,2) DEFAULT 0,
    
    -- Position/order counts
    active_positions_count INTEGER DEFAULT 0,
    total_orders_count INTEGER DEFAULT 0,
    
    -- Risk management
    max_loss_limit DECIMAL(15,2),
    max_profit_target DECIMAL(15,2),
    auto_square_off BOOLEAN DEFAULT FALSE,
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE,
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    
    is_active BOOLEAN DEFAULT TRUE
);

-- Strategy-specific permissions
CREATE TABLE tradingdb.strategy_permissions (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES tradingdb.users(id),
    strategy_id INTEGER NOT NULL REFERENCES tradingdb.strategies(id),
    trading_account_id INTEGER NOT NULL REFERENCES tradingdb.trading_accounts(id),
    organization_id INTEGER NOT NULL REFERENCES tradingdb.organizations(id),
    permission_type VARCHAR NOT NULL, -- StrategyPermissionType enum
    granted_by_id INTEGER NOT NULL REFERENCES tradingdb.users(id),
    granted_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    expires_at TIMESTAMP WITH TIME ZONE,
    is_active BOOLEAN DEFAULT TRUE,
    revoked_at TIMESTAMP WITH TIME ZONE,
    revoked_by_id INTEGER REFERENCES tradingdb.users(id),
    notes VARCHAR
);

-- Strategy action audit log
CREATE TABLE tradingdb.strategy_action_logs (
    id SERIAL PRIMARY KEY,
    action_type VARCHAR NOT NULL, -- StrategyActionType enum
    action_status VARCHAR NOT NULL, -- StrategyActionStatus enum
    user_id INTEGER NOT NULL REFERENCES tradingdb.users(id),
    strategy_id INTEGER NOT NULL REFERENCES tradingdb.strategies(id),
    trading_account_id INTEGER NOT NULL REFERENCES tradingdb.trading_accounts(id),
    organization_id INTEGER NOT NULL REFERENCES tradingdb.organizations(id),
    
    -- Action metadata
    action_data TEXT, -- JSON
    before_state TEXT, -- JSON
    after_state TEXT, -- JSON
    
    -- External references
    trade_service_request_id VARCHAR,
    
    -- Timestamps
    requested_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    executed_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    
    -- Error handling
    error_message TEXT,
    requires_approval BOOLEAN DEFAULT FALSE,
    approved_by_id INTEGER REFERENCES tradingdb.users(id),
    approved_at TIMESTAMP WITH TIME ZONE
);
```

## Strategy Management API Endpoints

### Strategy CRUD Operations

#### 1. Create Strategy
```http
POST /api/trading-accounts/{account_id}/strategies
Authorization: Bearer <jwt_token>
Content-Type: application/json

{
  "name": "Momentum RSI Strategy",
  "description": "RSI-based momentum strategy for large caps",
  "strategy_type": "MOMENTUM",
  "assigned_to_id": 456,
  "initial_capital": 500000,
  "parameters": {
    "instruments": ["RELIANCE", "TCS", "INFY"],
    "rsi_period": 14,
    "rsi_overbought": 70,
    "rsi_oversold": 30,
    "position_size": 100,
    "entry_threshold": 0.8
  },
  "risk_parameters": {
    "max_loss_per_trade": 5000,
    "max_portfolio_exposure": 0.2,
    "stop_loss_percentage": 2.0,
    "take_profit_percentage": 4.0
  },
  "max_loss_limit": 50000,
  "max_profit_target": 100000,
  "auto_square_off": true
}
```

**Response:**
```json
{
  "id": 123,
  "name": "Momentum RSI Strategy",
  "strategy_type": "MOMENTUM",
  "status": "DRAFT",
  "trade_service_strategy_id": "STRAT_001",
  "initial_capital": 500000,
  "current_value": 0,
  "total_pnl": 0,
  "is_running": false,
  "can_be_started": true,
  "created_at": "2024-01-15T10:30:00Z"
}
```

#### 2. List Strategies in Trading Account
```http
GET /api/trading-accounts/{account_id}/strategies
Authorization: Bearer <jwt_token>
?status=active&strategy_type=momentum
```

**Response:**
```json
{
  "strategies": [
    {
      "id": 123,
      "name": "Momentum RSI Strategy",
      "strategy_type": "MOMENTUM",
      "status": "ACTIVE",
      "current_value": 520000,
      "realized_pnl": 15000,
      "unrealized_pnl": 5000,
      "total_pnl": 20000,
      "pnl_percentage": 4.0,
      "active_positions_count": 3,
      "total_orders_count": 15,
      "is_running": true
    }
  ],
  "total": 1,
  "active_count": 1,
  "total_pnl": 20000
}
```

#### 3. Get Strategy Details
```http
GET /api/trading-accounts/{account_id}/strategies/{strategy_id}
Authorization: Bearer <jwt_token>
?include_positions=true&include_orders=true&include_analytics=true
```

**Response:**
```json
{
  "strategy": {
    "id": 123,
    "name": "Momentum RSI Strategy",
    "parameters_dict": {
      "rsi_period": 14,
      "position_size": 100
    },
    "risk_parameters_dict": {
      "max_loss_per_trade": 5000,
      "stop_loss_percentage": 2.0
    }
  },
  "positions": [
    {
      "symbol": "RELIANCE",
      "quantity": 100,
      "avg_price": 2500,
      "current_price": 2520,
      "pnl": 2000,
      "entry_time": "2024-01-15T09:30:00Z"
    }
  ],
  "orders": [
    {
      "order_id": "ORD123",
      "symbol": "TCS",
      "quantity": 50,
      "order_type": "LIMIT",
      "status": "PENDING",
      "created_at": "2024-01-15T10:15:00Z"
    }
  ],
  "holdings": [
    {
      "symbol": "INFY",
      "quantity": 75,
      "avg_price": 1800,
      "current_value": 135000
    }
  ],
  "margins": {
    "available_margin": 150000,
    "used_margin": 350000,
    "margin_utilization": 70.0
  },
  "analytics": {
    "sharpe_ratio": 1.5,
    "max_drawdown": 0.08,
    "win_rate": 0.65,
    "avg_trade_duration": 45.5
  }
}
```

#### 4. Modify Strategy
```http
PUT /api/trading-accounts/{account_id}/strategies/{strategy_id}
Authorization: Bearer <jwt_token>
Content-Type: application/json

{
  "name": "Enhanced Momentum RSI Strategy",
  "parameters": {
    "rsi_period": 21,
    "position_size": 150
  },
  "risk_parameters": {
    "max_loss_per_trade": 7500,
    "stop_loss_percentage": 1.5
  },
  "max_loss_limit": 75000
}
```

### Strategy Lifecycle Management

#### 1. Start Strategy
```http
POST /api/trading-accounts/{account_id}/strategies/{strategy_id}/start
Authorization: Bearer <jwt_token>
Content-Type: application/json

{
  "reason": "Market conditions favorable for momentum strategy"
}
```

**Response:**
```json
{
  "strategy_id": 123,
  "status": "ACTIVE",
  "started_at": "2024-01-15T10:30:00Z",
  "message": "Strategy started successfully",
  "trade_service_response": {
    "strategy_id": "STRAT_001",
    "status": "running",
    "initial_positions": []
  }
}
```

#### 2. Pause Strategy
```http
POST /api/trading-accounts/{account_id}/strategies/{strategy_id}/pause
Authorization: Bearer <jwt_token>
Content-Type: application/json

{
  "reason": "Temporary market volatility"
}
```

#### 3. Stop Strategy
```http
POST /api/trading-accounts/{account_id}/strategies/{strategy_id}/stop
Authorization: Bearer <jwt_token>
Content-Type: application/json

{
  "reason": "Strategy objective achieved"
}
```

#### 4. Square Off Strategy
```http
POST /api/trading-accounts/{account_id}/strategies/{strategy_id}/square-off
Authorization: Bearer <jwt_token>
Content-Type: application/json

{
  "reason": "Risk management - stop loss triggered",
  "force_exit": false,
  "confirm_action": true
}
```

**Response:**
```json
{
  "strategy_id": 123,
  "status": "SQUARED_OFF",
  "positions_closed": 3,
  "orders_cancelled": 2,
  "final_pnl": 18500,
  "completed_at": "2024-01-15T15:30:00Z",
  "trade_service_response": {
    "square_off_orders": ["ORD456", "ORD457", "ORD458"],
    "total_value": 518500
  }
}
```

### Strategy Permission Management

#### 1. Grant Strategy Permission
```http
POST /api/strategies/{strategy_id}/permissions
Authorization: Bearer <jwt_token>
Content-Type: application/json

{
  "user_id": 789,
  "permission_type": "VIEW_STRATEGY",
  "expires_at": "2024-12-31T23:59:59Z",
  "notes": "Temporary access for performance review"
}
```

#### 2. List Strategy Permissions
```http
GET /api/strategies/{strategy_id}/permissions
Authorization: Bearer <jwt_token>
```

**Response:**
```json
{
  "permissions": [
    {
      "id": 1,
      "user_id": 789,
      "permission_type": "VIEW_STRATEGY",
      "granted_by_id": 456,
      "granted_at": "2024-01-15T10:30:00Z",
      "expires_at": "2024-12-31T23:59:59Z",
      "is_valid": true,
      "notes": "Temporary access for performance review"
    }
  ],
  "total": 1
}
```

#### 3. Revoke Strategy Permission
```http
DELETE /api/strategy-permissions/{permission_id}
Authorization: Bearer <jwt_token>
Content-Type: application/json

{
  "reason": "Access period completed"
}
```

### Strategy Analytics and Monitoring

#### 1. Get Strategy Performance
```http
GET /api/strategies/{strategy_id}/analytics
Authorization: Bearer <jwt_token>
?period=monthly&metrics=pnl,sharpe_ratio,drawdown
```

**Response:**
```json
{
  "strategy_id": 123,
  "period": "monthly",
  "metrics": {
    "total_pnl": 18500,
    "pnl_percentage": 3.7,
    "sharpe_ratio": 1.45,
    "max_drawdown": 0.08,
    "win_rate": 0.65,
    "total_trades": 25,
    "winning_trades": 16,
    "losing_trades": 9,
    "avg_win": 2850,
    "avg_loss": -1200,
    "best_trade": 8500,
    "worst_trade": -3200,
    "avg_trade_duration": 2.5,
    "volatility": 0.15
  },
  "daily_pnl": [
    {"date": "2024-01-01", "pnl": 1500},
    {"date": "2024-01-02", "pnl": -800},
    {"date": "2024-01-03", "pnl": 2200}
  ]
}
```

#### 2. Compare Strategies
```http
POST /api/trading-accounts/{account_id}/strategies/compare
Authorization: Bearer <jwt_token>
Content-Type: application/json

{
  "strategy_ids": [123, 124, 125],
  "comparison_metrics": ["pnl_percentage", "sharpe_ratio", "max_drawdown"],
  "period": "monthly"
}
```

**Response:**
```json
{
  "comparison": [
    {
      "strategy_id": 123,
      "strategy_name": "Momentum RSI Strategy",
      "pnl_percentage": 3.7,
      "sharpe_ratio": 1.45,
      "max_drawdown": 0.08
    },
    {
      "strategy_id": 124,
      "strategy_name": "Mean Reversion Strategy",
      "pnl_percentage": 2.1,
      "sharpe_ratio": 1.12,
      "max_drawdown": 0.05
    }
  ],
  "best_performer": {
    "strategy_id": 123,
    "metric": "pnl_percentage",
    "value": 3.7
  }
}
```

### Bulk Strategy Operations

#### 1. Bulk Strategy Actions
```http
POST /api/trading-accounts/{account_id}/strategies/bulk-action
Authorization: Bearer <jwt_token>
Content-Type: application/json

{
  "strategy_ids": [123, 124, 125],
  "action_type": "square_off",
  "reason": "End of trading session",
  "force_exit": false
}
```

**Response:**
```json
{
  "action_id": "BULK_001",
  "strategies_affected": 3,
  "results": [
    {
      "strategy_id": 123,
      "status": "success",
      "message": "Strategy squared off successfully"
    },
    {
      "strategy_id": 124,
      "status": "success", 
      "message": "Strategy squared off successfully"
    },
    {
      "strategy_id": 125,
      "status": "failed",
      "message": "Strategy not in active state"
    }
  ],
  "total_success": 2,
  "total_failed": 1
}
```

### Strategy Risk Management

#### 1. Set Strategy Risk Limits
```http
POST /api/strategies/{strategy_id}/risk-limits
Authorization: Bearer <jwt_token>
Content-Type: application/json

{
  "daily_loss_limit": 10000,
  "position_size_limit": 200,
  "leverage_limit": 3.0,
  "max_open_positions": 5
}
```

#### 2. Get Strategy Risk Status
```http
GET /api/strategies/{strategy_id}/risk-status
Authorization: Bearer <jwt_token>
```

**Response:**
```json
{
  "strategy_id": 123,
  "risk_limits": [
    {
      "limit_type": "daily_loss_limit",
      "limit_value": 10000,
      "current_usage": 3500,
      "usage_percentage": 35.0,
      "is_breached": false
    }
  ],
  "current_risk_score": "MEDIUM",
  "alerts": [
    {
      "type": "WARNING",
      "message": "Position size approaching limit",
      "timestamp": "2024-01-15T14:30:00Z"
    }
  ]
}
```

## Trading Operations API Endpoints

### Order Management

#### 1. Place Order
```http
POST /api/trading-accounts/{account_id}/orders
Authorization: Bearer <jwt_token>
Content-Type: application/json

{
  "symbol": "RELIANCE",
  "quantity": 100,
  "price": 2500.50,
  "order_type": "LIMIT",
  "side": "BUY",
  "product_type": "INTRADAY",
  "stop_loss": 2450.00,
  "target": 2600.00
}
```

**Response:**
```json
{
  "action_id": 123,
  "action_type": "place_order",
  "status": "executed",
  "message": "Order placed successfully",
  "broker_order_id": "ORD123456",
  "executed_at": "2024-01-15T10:30:00Z",
  "requires_approval": false
}
```

#### 2. Modify Order
```http
PUT /api/trading-accounts/{account_id}/orders/{order_id}
Authorization: Bearer <jwt_token>
Content-Type: application/json

{
  "broker_order_id": "ORD123456",
  "quantity": 150,
  "price": 2520.00
}
```

#### 3. Cancel Order
```http
DELETE /api/trading-accounts/{account_id}/orders/{order_id}
Authorization: Bearer <jwt_token>
Content-Type: application/json

{
  "broker_order_id": "ORD123456",
  "reason": "Market conditions changed"
}
```

#### 4. Square Off Position
```http
POST /api/trading-accounts/{account_id}/positions/{symbol}/square-off
Authorization: Bearer <jwt_token>
Content-Type: application/json

{
  "symbol": "RELIANCE",
  "quantity": 50,
  "price": 2580.00
}
```

### Strategy Management

#### 1. Create Strategy
```http
POST /api/trading-accounts/{account_id}/strategies
Authorization: Bearer <jwt_token>
Content-Type: application/json

{
  "name": "Momentum Strategy 1",
  "description": "RSI-based momentum strategy",
  "strategy_type": "MOMENTUM",
  "instruments": ["RELIANCE", "TCS", "INFY"],
  "parameters": {
    "rsi_period": 14,
    "rsi_overbought": 70,
    "rsi_oversold": 30,
    "position_size": 100
  },
  "risk_parameters": {
    "max_loss_per_trade": 1000,
    "max_portfolio_exposure": 0.1
  }
}
```

#### 2. Adjust Strategy
```http
POST /api/trading-accounts/{account_id}/strategies/{strategy_id}/adjust
Authorization: Bearer <jwt_token>
Content-Type: application/json

{
  "strategy_id": "STRAT_001",
  "adjustment_type": "SCALE_UP",
  "adjustment_parameters": {
    "scale_factor": 1.5,
    "new_position_size": 150
  },
  "reason": "Favorable market conditions"
}
```

#### 3. Square Off Strategy
```http
POST /api/trading-accounts/{account_id}/strategies/{strategy_id}/square-off
Authorization: Bearer <jwt_token>
Content-Type: application/json

{
  "strategy_id": "STRAT_001",
  "reason": "Risk management",
  "force_exit": false
}
```

### Portfolio Management

#### 1. Square Off Portfolio
```http
POST /api/trading-accounts/{account_id}/portfolio/square-off
Authorization: Bearer <jwt_token>
Content-Type: application/json

{
  "reason": "Market closure emergency",
  "confirm_action": true,
  "exclude_strategies": ["STRAT_002"]
}
```

#### 2. Get Portfolio Status
```http
GET /api/trading-accounts/{account_id}/portfolio/status
Authorization: Bearer <jwt_token>
```

**Response:**
```json
{
  "total_positions": 15,
  "total_value": 1500000,
  "realized_pnl": 25000,
  "unrealized_pnl": -5000,
  "active_strategies": 3,
  "risk_utilization": 65.5,
  "positions": [
    {
      "symbol": "RELIANCE",
      "quantity": 100,
      "avg_price": 2500,
      "current_price": 2520,
      "pnl": 2000
    }
  ]
}
```

### Risk Management

#### 1. Set Risk Limits
```http
POST /api/trading-accounts/{account_id}/risk-limits
Authorization: Bearer <jwt_token>
Content-Type: application/json

{
  "limit_type": "daily_loss_limit",
  "limit_value": 10000,
  "currency": "INR",
  "is_hard_limit": true
}
```

#### 2. Get Risk Status
```http
GET /api/trading-accounts/{account_id}/risk-status
Authorization: Bearer <jwt_token>
```

**Response:**
```json
{
  "risk_limits": [
    {
      "limit_type": "daily_loss_limit",
      "limit_value": 10000,
      "current_usage": 3500,
      "usage_percentage": 35.0,
      "is_breached": false,
      "remaining_capacity": 6500
    }
  ],
  "overall_risk_score": "MEDIUM",
  "alerts": []
}
```

### Bulk Operations

#### 1. Bulk Square Off
```http
POST /api/trading-accounts/{account_id}/bulk/square-off
Authorization: Bearer <jwt_token>
Content-Type: application/json

{
  "positions": ["RELIANCE", "TCS", "INFY"],
  "reason": "End of day square off",
  "force_exit": false
}
```

#### 2. Bulk Cancel Orders
```http
POST /api/trading-accounts/{account_id}/bulk/cancel-orders
Authorization: Bearer <jwt_token>
Content-Type: application/json

{
  "order_ids": ["ORD123", "ORD124", "ORD125"],
  "reason": "Strategy change"
}
```

### Permission Validation

#### 1. Validate Action Permission
```http
POST /api/trading-accounts/{account_id}/validate-action
Authorization: Bearer <jwt_token>
Content-Type: application/json

{
  "action_type": "place_order",
  "action_data": {
    "symbol": "RELIANCE",
    "quantity": 100,
    "price": 2500
  }
}
```

**Response:**
```json
{
  "allowed": true,
  "permission_level": "FULL_TRADING",
  "required_permission": "place_orders",
  "missing_permissions": [],
  "risk_violations": [],
  "requires_approval": false,
  "error_message": null
}
```

### Approval Workflow

#### 1. Request Approval
```http
POST /api/trading-actions/{action_id}/request-approval
Authorization: Bearer <jwt_token>
Content-Type: application/json

{
  "action_id": 123,
  "approver_notes": "High-value trade requiring approval"
}
```

#### 2. Approve/Reject Action
```http
POST /api/trading-actions/{action_id}/approve
Authorization: Bearer <jwt_token>
Content-Type: application/json

{
  "action_id": 123,
  "approved": true,
  "notes": "Approved after risk review"
}
```

### Audit and Monitoring

#### 1. Get Action History
```http
GET /api/trading-accounts/{account_id}/action-history
Authorization: Bearer <jwt_token>
?start_date=2024-01-01&end_date=2024-01-31&action_type=place_order
```

**Response:**
```json
{
  "actions": [
    {
      "id": 123,
      "action_type": "place_order",
      "status": "executed",
      "user_id": 456,
      "symbol": "RELIANCE",
      "quantity": 100,
      "executed_at": "2024-01-15T10:30:00Z",
      "broker_order_id": "ORD123456"
    }
  ],
  "total": 1,
  "page": 1,
  "per_page": 50
}
```

## Security Features

1. **API Key Security**
   - Hashed storage using SHA-256
   - Masked display (show only first 8 + last 4 chars)
   - Rotation capability

2. **Permission Expiration**
   - Time-based expiration
   - Manual revocation
   - Audit trail

3. **Access Logging**
   - All API calls logged with user context
   - Failed authorization attempts tracked
   - Data access audit trail

4. **Validation**
   - JWT token validation
   - API key validation with trade_service
   - Resource ownership validation

## Example Workflow

### 1. Organization Creation
```
1. User creates organization with API key
2. System validates API key with trade_service
3. System hashes and stores API key
4. Organization created successfully
```

### 2. Account Import
```
1. Organization owner fetches available accounts from trade_service
2. Owner selects accounts to import
3. System imports selected accounts
4. Accounts available for assignment
```

### 3. Permission Grant
```
1. Organization owner grants view_positions permission to user X for account Y
2. Permission stored with expiration date
3. User X can now access position data for account Y
4. Access automatically expires based on expiration date
```

### 4. Data Access
```
1. User requests trading data for account
2. System validates user permission for specific data type
3. System retrieves organization API key
4. System calls trade_service with user JWT + API key + account details
5. Data returned to authorized user
```

## Permission Hierarchy and Validation

### Permission Levels
```python
class PermissionLevel(Enum):
    NONE = 0              # No access
    READ_ONLY = 1         # View data only
    LIMITED_TRADING = 2   # Basic trading operations
    FULL_TRADING = 3      # All trading operations
    ADMIN_TRADING = 4     # All operations + admin functions
```

### Permission Inheritance
```python
# Users with higher-level permissions automatically get lower-level permissions
ADMIN_TRADING: includes FULL_TRADING, LIMITED_TRADING, READ_ONLY
FULL_TRADING: includes LIMITED_TRADING, READ_ONLY  
LIMITED_TRADING: includes READ_ONLY
READ_ONLY: basic viewing permissions only
```

### Role-Based Default Permissions
```python
# Organization Owner
ADMIN_TRADING for all organization accounts

# Organization Backup Owner  
FULL_TRADING for all organization accounts

# Assigned Account User
FULL_TRADING for assigned accounts only

# Permitted User
Specific permissions granted explicitly
```

### Risk-Based Validation
```python
# High-risk actions require additional validation:
HIGH_RISK_ACTIONS = [
    "square_off_portfolio",     # Close entire portfolio
    "override_risk_limits",     # Bypass risk controls  
    "bulk_square_off",         # Mass position closure
    "delete_strategy"          # Remove active strategies
]

# Approval workflow for high-risk actions:
1. Action requested → Validation → Approval required
2. Organization owner/backup owner approves
3. Action executed with full audit trail
```

## Example Trading Workflows

### Workflow 1: Day Trader Setup
```
1. Organization Owner creates "Day Trading Group"
2. Imports 5 trading accounts from broker API
3. Assigns Account A to User Alice (full trading)
4. Grants User Bob "place_orders" + "view_positions" for Account B
5. Sets risk limits: daily_loss_limit = ₹50,000 per account

Alice can:
- Place/modify/cancel orders on Account A
- Create/manage strategies on Account A
- View all data for Account A

Bob can:
- Place orders on Account B (but cannot modify/cancel)
- View positions on Account B
- Cannot create strategies or access other data
```

### Workflow 2: Strategy Manager Access
```
1. Organization has 10 trading accounts
2. Strategy Manager gets specific permissions:
   - CREATE_STRATEGY for accounts 1-5
   - ADJUST_STRATEGY for accounts 1-10  
   - VIEW_ANALYTICS for accounts 1-10
   - Cannot place individual orders or square off

Strategy Manager can:
- Create new strategies on assigned accounts
- Adjust parameters of all strategies
- View analytics and performance
- Cannot execute manual trades
```

### Workflow 3: Risk Manager Role
```
1. Risk Manager gets permissions:
   - SET_RISK_LIMITS for all accounts
   - OVERRIDE_RISK_LIMITS (with approval)
   - VIEW_PORTFOLIO for all accounts
   - SQUARE_OFF_PORTFOLIO (emergency only)

Risk Manager can:
- Monitor all accounts' risk exposure
- Set and adjust risk limits
- Force square-off in emergency (requires approval)
- Override limits temporarily (logged and approved)
```

### Workflow 4: Client Access
```
1. External client gets limited access:
   - VIEW_POSITIONS for their account only
   - VIEW_PNL for their account only
   - No trading permissions

Client can:
- Log in and see their current positions
- View profit/loss for their investments
- Cannot execute any trades
- Cannot see other accounts or strategies
```

## Advanced Security Features

### 1. Time-Based Permissions
```python
# Permissions can have expiration dates
{
  "user_id": 123,
  "permission_type": "place_orders",
  "expires_at": "2024-12-31T23:59:59Z"
}

# System automatically revokes expired permissions
# Email notifications before expiration
```

### 2. IP-Based Restrictions
```python
# Restrict trading actions to specific IPs
{
  "user_id": 123,
  "allowed_ips": ["192.168.1.100", "203.0.113.0/24"],
  "trading_hours_only": true
}
```

### 3. Two-Factor Authentication for High-Risk Actions
```python
# Require 2FA for:
- Portfolio square-off
- Risk limit overrides  
- Large trades (>₹10L)
- Bulk operations

# Implementation:
1. User initiates high-risk action
2. System sends OTP to registered mobile
3. User provides OTP within 5 minutes
4. Action executed with audit trail
```

### 4. Real-Time Risk Monitoring
```python
# Continuous monitoring:
- Position size vs limits
- P&L vs daily loss limits
- Strategy performance vs benchmarks
- Unusual trading patterns

# Automatic actions:
- Stop trading when limits breached
- Alert organization owners
- Force square-off if critical limits hit
```

### 5. Comprehensive Audit Trail
```python
# Every action logged with:
{
  "timestamp": "2024-01-15T10:30:00Z",
  "user_id": 123,
  "action": "place_order",
  "account_id": 456,
  "details": {
    "symbol": "RELIANCE",
    "quantity": 100,
    "price": 2500
  },
  "ip_address": "192.168.1.100",
  "user_agent": "TradingApp/1.0",
  "risk_score": "LOW",
  "approval_required": false,
  "execution_time_ms": 150
}
```

## Integration with Trade Service

### Request Flow with Enhanced Security
```python
async def execute_trading_action(
    user_context: UserContext,
    account_id: int,
    action_type: ActionType,
    action_data: Dict[str, Any]
):
    # 1. Validate user permissions
    validation = trading_permission_validator.validate_trading_action(
        user_context, account, action_type, action_data, db
    )
    
    if not validation["allowed"]:
        raise AuthorizationException(validation["error_message"])
    
    # 2. Check risk limits
    if validation["risk_violations"]:
        if not can_override_risk(user_context):
            raise RiskLimitException(validation["risk_violations"])
    
    # 3. Handle approval workflow
    if validation["requires_approval"]:
        action_log = create_pending_action(user_context, action_data)
        return {"status": "pending_approval", "action_id": action_log.id}
    
    # 4. Execute with trade service
    headers = {
        "Authorization": f"Bearer {user_context.jwt_token}",
        "X-API-Key": decrypt_api_key(account.organization.api_key_hash),
        "X-Account-ID": account.login_id,
        "X-Broker": account.broker,
        "X-Action-ID": action_log.id,  # For audit correlation
        "X-Risk-Score": calculate_risk_score(action_data)
    }
    
    response = await trade_service_client.execute_action(
        action_type, action_data, headers
    )
    
    # 5. Log execution result
    update_action_log(action_log, response)
    
    return response
```

This design provides enterprise-grade trading permission management with comprehensive security, risk controls, and audit capabilities suitable for institutional trading platforms.