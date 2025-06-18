# Trading Limits System - Complete Guide

## Overview

The Trading Limits system provides comprehensive risk management capabilities by allowing organization owners to set granular trading boundaries for users within trading accounts. This system helps prevent excessive risk exposure and ensures disciplined trading practices.

## Key Features

- **Multiple Limit Types**: Financial, quantity, instrument, time-based, and leverage limits
- **Flexible Enforcement**: Hard limits (block), soft limits (warn), or advisory (monitor only)
- **Real-time Validation**: Validate all trading actions before execution
- **Automatic Breach Detection**: Track violations with severity-based responses
- **Usage Tracking**: Monitor current usage against limits with automatic resets
- **Comprehensive Reporting**: Detailed analytics and breach reporting

## Limit Types

### Financial Limits
- **Daily Trading Limit**: Maximum trading value per day (₹50,000)
- **Single Trade Limit**: Maximum value per individual trade (₹10,000)
- **Daily Loss Limit**: Maximum loss allowed per day (₹5,000)
- **Monthly Trading Limit**: Maximum trading value per month (₹1,000,000)
- **Position Value Limit**: Maximum total position value (₹100,000)

### Quantity Limits
- **Daily Order Count**: Maximum orders per day (20 orders)
- **Single Order Quantity**: Maximum shares per order (1,000 shares)
- **Max Open Positions**: Maximum concurrent open positions (10 positions)

### Instrument Limits
- **Allowed Instruments**: Whitelist of tradeable instruments ("RELIANCE,TCS,INFY")
- **Blocked Instruments**: Blacklist of restricted instruments ("PENNY_STOCKS")
- **Allowed Segments**: Permitted trading segments ("CASH,FUTURES")

### Time-based Limits
- **Trading Hours**: Allowed trading time window (09:15-15:30)
- **Allowed Days**: Permitted trading days ("MONDAY,TUESDAY,WEDNESDAY,THURSDAY,FRIDAY")

### Leverage Limits
- **Max Leverage**: Maximum leverage multiplier (5x)
- **Margin Utilization**: Maximum margin usage percentage (80%)

### Strategy Limits
- **Strategy Allocation**: Maximum capital per strategy (₹25,000)
- **Max Strategies**: Maximum number of active strategies (5)

## Usage Examples

### 1. Create a Daily Trading Limit

```http
POST /api/trading-limits
Authorization: Bearer <jwt_token>
Content-Type: application/json

{
  "user_id": 123,
  "trading_account_id": 456,
  "limit_type": "daily_trading_limit",
  "limit_value": 50000.00,
  "enforcement_type": "hard_limit",
  "warning_threshold": 80.0,
  "usage_reset_frequency": "daily"
}
```

**Response:**
```json
{
  "id": 789,
  "user_id": 123,
  "trading_account_id": 456,
  "limit_type": "daily_trading_limit",
  "limit_value": 50000.00,
  "current_usage_value": 0.00,
  "usage_percentage": 0.0,
  "remaining_limit": 50000.00,
  "is_active": true,
  "enforcement_type": "hard_limit"
}
```

### 2. Set Trading Hours Restriction

```http
POST /api/trading-limits
Authorization: Bearer <jwt_token>
Content-Type: application/json

{
  "user_id": 123,
  "trading_account_id": 456,
  "limit_type": "trading_hours",
  "start_time": "09:15:00",
  "end_time": "15:30:00",
  "allowed_days": "MONDAY,TUESDAY,WEDNESDAY,THURSDAY,FRIDAY",
  "enforcement_type": "hard_limit"
}
```

### 3. Create Instrument Whitelist

```http
POST /api/trading-limits
Authorization: Bearer <jwt_token>
Content-Type: application/json

{
  "user_id": 123,
  "trading_account_id": 456,
  "limit_type": "allowed_instruments",
  "limit_text": "RELIANCE,TCS,INFY,HDFCBANK,ICICIBANK,SBIN",
  "enforcement_type": "hard_limit"
}
```

### 4. Validate Trading Action

```http
POST /api/trading-limits/validate?trading_account_id=456
Authorization: Bearer <jwt_token>
Content-Type: application/json

{
  "action_type": "place_order",
  "instrument": "RELIANCE",
  "quantity": 100,
  "price": 2500.00,
  "trade_value": 250000.00,
  "order_type": "LIMIT"
}
```

**Response (Limit Exceeded):**
```json
{
  "allowed": false,
  "violations": [
    {
      "limit_type": "daily_trading_limit",
      "limit_value": 50000.0,
      "current_usage": 30000.0,
      "attempted_value": 250000.0,
      "projected_usage": 280000.0,
      "breach_amount": 230000.0,
      "message": "Daily trading limit of ₹50,000.00 would be exceeded. Current usage: ₹30,000.00, Attempted: ₹250,000.00"
    }
  ],
  "warnings": [],
  "actions_required": ["WARNING", "NOTIFY_ADMIN"],
  "override_possible": false,
  "error_message": "Daily trading limit of ₹50,000.00 would be exceeded. Current usage: ₹30,000.00, Attempted: ₹250,000.00"
}
```

### 5. Bulk Create Limits for Multiple Users

```http
POST /api/trading-limits/bulk-create
Authorization: Bearer <jwt_token>
Content-Type: application/json

{
  "apply_to_all_users": true,
  "user_ids": [123, 124, 125],
  "limits": [
    {
      "user_id": 123,
      "trading_account_id": 456,
      "limit_type": "daily_trading_limit",
      "limit_value": 50000.00,
      "enforcement_type": "hard_limit"
    },
    {
      "user_id": 123,
      "trading_account_id": 456,
      "limit_type": "single_trade_limit",
      "limit_value": 10000.00,
      "enforcement_type": "hard_limit"
    }
  ]
}
```

## Integration with Trading Operations

### Order Placement Flow

```python
from shared_architecture.utils.trading_limit_validator import TradingAction, get_trading_limit_validator
from shared_architecture.auth import UserContext

async def place_order(order_data, user_context: UserContext, trading_account, db):
    # 1. Create trading action
    action = TradingAction(
        action_type="place_order",
        instrument=order_data.instrument,
        quantity=order_data.quantity,
        price=order_data.price,
        trade_value=order_data.quantity * order_data.price
    )
    
    # 2. Validate against limits
    validator = get_trading_limit_validator()
    result = validator.validate_trading_action(user_context, trading_account, action, db)
    
    # 3. Check if allowed
    if not result.allowed:
        raise HTTPException(status_code=400, detail=result.error_message)
    
    # 4. Place order with trade service
    order_response = await place_order_with_trade_service(order_data)
    
    # 5. Update usage counters
    if order_response.success:
        validator.update_usage_after_trade(user_context, trading_account, action, db)
    
    return order_response
```

### Strategy-Specific Limits

You can set limits that apply only to specific strategies:

```http
POST /api/trading-limits
Authorization: Bearer <jwt_token>
Content-Type: application/json

{
  "user_id": 123,
  "trading_account_id": 456,
  "strategy_id": 789,
  "limit_type": "strategy_allocation",
  "limit_value": 25000.00,
  "limit_scope": "strategy_specific",
  "enforcement_type": "hard_limit"
}
```

## Breach Handling

### Severity Levels

- **LOW**: Minor breach (≤10% over limit), sends warning
- **MEDIUM**: Moderate breach (10-25% over), warns and notifies admin
- **HIGH**: Serious breach (25-50% over), restricts trading and alerts admin
- **CRITICAL**: Severe breach (>50% over), suspends trading and triggers auto square-off

### Breach Actions

1. **WARNING**: Send notification to user
2. **RESTRICT**: Limit further trading actions
3. **SUSPEND**: Temporarily suspend all trading
4. **NOTIFY_ADMIN**: Alert organization administrators
5. **AUTO_SQUARE_OFF**: Automatically close positions

### Breach Monitoring

```http
GET /api/trading-limits/breaches?user_id=123&severity=high
Authorization: Bearer <jwt_token>
```

**Response:**
```json
[
  {
    "id": 101,
    "user_id": 123,
    "breach_type": "daily_trading_limit",
    "severity": "high",
    "limit_value": 50000.0,
    "attempted_value": 75000.0,
    "breach_amount": 25000.0,
    "breach_percentage": 50.0,
    "actions_taken": ["warning", "restrict", "notify_admin"],
    "breach_time": "2024-01-15T14:30:00Z",
    "is_resolved": false
  }
]
```

## Usage Tracking and Reset

### Automatic Reset

Usage counters automatically reset based on the configured frequency:

- **Daily**: Reset at midnight
- **Weekly**: Reset every Monday
- **Monthly**: Reset on the 1st of each month

### Manual Reset

```http
POST /api/trading-limits/reset-usage
Authorization: Bearer <jwt_token>
Content-Type: application/json

{
  "limit_ids": [789, 790, 791],
  "reason": "Monthly reset for performance review"
}
```

## Common Use Cases

### 1. Conservative Trader Profile

```json
{
  "limits": [
    {
      "limit_type": "daily_trading_limit",
      "limit_value": 25000.00,
      "enforcement_type": "hard_limit"
    },
    {
      "limit_type": "single_trade_limit", 
      "limit_value": 5000.00,
      "enforcement_type": "hard_limit"
    },
    {
      "limit_type": "daily_order_count",
      "limit_count": 10,
      "enforcement_type": "soft_limit"
    },
    {
      "limit_type": "allowed_instruments",
      "limit_text": "NIFTY50_STOCKS",
      "enforcement_type": "hard_limit"
    }
  ]
}
```

### 2. Active Day Trader Profile

```json
{
  "limits": [
    {
      "limit_type": "daily_trading_limit",
      "limit_value": 100000.00,
      "enforcement_type": "hard_limit"
    },
    {
      "limit_type": "single_trade_limit",
      "limit_value": 20000.00,
      "enforcement_type": "soft_limit"
    },
    {
      "limit_type": "daily_order_count",
      "limit_count": 50,
      "enforcement_type": "advisory"
    },
    {
      "limit_type": "trading_hours",
      "start_time": "09:15:00",
      "end_time": "15:30:00",
      "enforcement_type": "hard_limit"
    }
  ]
}
```

### 3. Algorithm Trading Profile

```json
{
  "limits": [
    {
      "limit_type": "daily_trading_limit",
      "limit_value": 500000.00,
      "enforcement_type": "hard_limit"
    },
    {
      "limit_type": "max_open_positions",
      "limit_count": 20,
      "enforcement_type": "hard_limit"
    },
    {
      "limit_type": "daily_loss_limit",
      "limit_value": 50000.00,
      "enforcement_type": "hard_limit"
    },
    {
      "limit_type": "single_order_quantity",
      "limit_count": 500,
      "enforcement_type": "soft_limit"
    }
  ]
}
```

## API Reference

### Endpoints

- `POST /api/trading-limits` - Create new trading limit
- `GET /api/trading-limits` - List trading limits with filtering
- `GET /api/trading-limits/{limit_id}` - Get specific trading limit
- `PUT /api/trading-limits/{limit_id}` - Update trading limit
- `DELETE /api/trading-limits/{limit_id}` - Delete trading limit
- `POST /api/trading-limits/validate` - Validate trading action
- `POST /api/trading-limits/reset-usage` - Reset usage counters
- `GET /api/trading-limits/breaches` - List limit breaches
- `POST /api/trading-limits/bulk-create` - Create multiple limits

### Query Parameters

- `user_id` - Filter by user
- `trading_account_id` - Filter by trading account
- `limit_type` - Filter by limit type
- `is_active` - Filter by active status
- `is_breached` - Filter by breach status
- `skip` - Pagination offset
- `limit` - Pagination limit

## Best Practices

### 1. Start Conservative
Begin with conservative limits and gradually increase based on user performance and risk tolerance.

### 2. Layer Multiple Limits
Use multiple complementary limits (daily trading + single trade + order count) for comprehensive risk management.

### 3. Monitor Regularly
Set up regular monitoring and reporting to track usage patterns and breach frequencies.

### 4. Use Soft Limits for Guidance
Implement soft limits for advisory purposes to guide users without blocking trades.

### 5. Strategy-Specific Controls
Set tighter limits for high-risk strategies and looser limits for conservative strategies.

### 6. Time-based Restrictions
Use trading hours limits to prevent after-hours trading mistakes.

### 7. Instrument Controls
Restrict access to volatile or complex instruments for inexperienced users.

## Security Considerations

- Only organization owners can create, modify, or delete trading limits
- Users can view their own limits but cannot modify them
- All limit changes are logged with audit trails
- Breach notifications are sent to both users and administrators
- Override capabilities require explicit permissions

## Performance Optimization

- Limits are cached for fast validation
- Usage counters are updated asynchronously where possible
- Batch operations are supported for bulk limit management
- Database indexes optimize common query patterns

This comprehensive trading limits system provides the flexibility and control needed to manage risk effectively while maintaining operational efficiency.