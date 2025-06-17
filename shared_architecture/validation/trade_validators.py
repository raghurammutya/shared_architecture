# shared_architecture/validation/trade_validators.py
import re
from decimal import Decimal, InvalidOperation
from typing import Any, Dict, List, Optional, Union, Callable
from datetime import datetime, date
from dataclasses import dataclass
from enum import Enum

from shared_architecture.exceptions.trade_exceptions import ValidationException, ErrorContext
from shared_architecture.enums import Exchange, TradeType, OrderType, ProductType

class ValidationSeverity(Enum):
    """Validation error severity levels"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"

@dataclass
class ValidationResult:
    """Result of a validation check"""
    is_valid: bool
    field_name: str
    message: str
    severity: ValidationSeverity = ValidationSeverity.ERROR
    suggested_value: Any = None

class TradeValidator:
    """Comprehensive validation for trade-related data"""
    
    # Regex patterns
    SYMBOL_PATTERN = re.compile(r'^[A-Z0-9&-]{1,20}$')
    INSTRUMENT_KEY_PATTERN = re.compile(r'^[A-Z]{3,4}@[A-Z0-9&-]+@[a-z]+$')
    PSEUDO_ACCOUNT_PATTERN = re.compile(r'^[A-Za-z0-9_-]{3,50}$')
    ORDER_ID_PATTERN = re.compile(r'^[A-Za-z0-9_-]{1,50}$')
    ORGANIZATION_ID_PATTERN = re.compile(r'^[A-Za-z0-9_-]{3,50}$')
    
    # Trading limits
    MAX_QUANTITY = 999999999
    MIN_QUANTITY = 1
    MAX_PRICE = Decimal('999999.99')
    MIN_PRICE = Decimal('0.01')
    MAX_TRIGGER_PRICE = Decimal('999999.99')
    MIN_TRIGGER_PRICE = Decimal('0.01')
    
    @staticmethod
    def validate_symbol(symbol: str, context: ErrorContext = None) -> ValidationResult:
        """Validate trading symbol format"""
        if not symbol:
            return ValidationResult(
                is_valid=False,
                field_name="symbol",
                message="Symbol is required",
                severity=ValidationSeverity.ERROR
            )
        
        if not isinstance(symbol, str):
            return ValidationResult(
                is_valid=False,
                field_name="symbol",
                message=f"Symbol must be a string, got {type(symbol).__name__}",
                severity=ValidationSeverity.ERROR
            )
        
        if not TradeValidator.SYMBOL_PATTERN.match(symbol):
            return ValidationResult(
                is_valid=False,
                field_name="symbol",
                message=f"Invalid symbol format: {symbol}. Must contain only uppercase letters, numbers, &, and - (1-20 chars)",
                severity=ValidationSeverity.ERROR,
                suggested_value=symbol.upper() if symbol.replace('&', '').replace('-', '').isalnum() else None
            )
        
        return ValidationResult(
            is_valid=True,
            field_name="symbol",
            message="Valid symbol format"
        )
    
    @staticmethod
    def validate_instrument_key(instrument_key: str, context: ErrorContext = None) -> ValidationResult:
        """Validate instrument key format (NSE@RELIANCE@equities)"""
        if not instrument_key:
            return ValidationResult(
                is_valid=False,
                field_name="instrument_key",
                message="Instrument key is required",
                severity=ValidationSeverity.ERROR
            )
        
        if not isinstance(instrument_key, str):
            return ValidationResult(
                is_valid=False,
                field_name="instrument_key",
                message=f"Instrument key must be a string, got {type(instrument_key).__name__}",
                severity=ValidationSeverity.ERROR
            )
        
        if not TradeValidator.INSTRUMENT_KEY_PATTERN.match(instrument_key):
            return ValidationResult(
                is_valid=False,
                field_name="instrument_key",
                message=f"Invalid instrument key format: {instrument_key}. Expected format: EXCHANGE@SYMBOL@category",
                severity=ValidationSeverity.ERROR
            )
        
        # Validate exchange part
        parts = instrument_key.split('@')
        if len(parts) != 3:
            return ValidationResult(
                is_valid=False,
                field_name="instrument_key",
                message=f"Instrument key must have exactly 3 parts separated by '@': {instrument_key}",
                severity=ValidationSeverity.ERROR
            )
        
        exchange, symbol, category = parts
        
        # Validate exchange
        try:
            Exchange(exchange)
        except ValueError:
            return ValidationResult(
                is_valid=False,
                field_name="instrument_key",
                message=f"Invalid exchange in instrument key: {exchange}. Valid exchanges: {[e.value for e in Exchange]}",
                severity=ValidationSeverity.ERROR
            )
        
        return ValidationResult(
            is_valid=True,
            field_name="instrument_key",
            message="Valid instrument key format"
        )
    
    @staticmethod
    def validate_quantity(quantity: Union[int, str], context: ErrorContext = None) -> ValidationResult:
        """Validate trade quantity"""
        if quantity is None:
            return ValidationResult(
                is_valid=False,
                field_name="quantity",
                message="Quantity is required",
                severity=ValidationSeverity.ERROR
            )
        
        # Convert to int if string
        try:
            qty = int(quantity)
        except (ValueError, TypeError):
            return ValidationResult(
                is_valid=False,
                field_name="quantity",
                message=f"Quantity must be a valid integer, got: {quantity}",
                severity=ValidationSeverity.ERROR
            )
        
        if qty < TradeValidator.MIN_QUANTITY:
            return ValidationResult(
                is_valid=False,
                field_name="quantity",
                message=f"Quantity must be at least {TradeValidator.MIN_QUANTITY}, got: {qty}",
                severity=ValidationSeverity.ERROR
            )
        
        if qty > TradeValidator.MAX_QUANTITY:
            return ValidationResult(
                is_valid=False,
                field_name="quantity",
                message=f"Quantity cannot exceed {TradeValidator.MAX_QUANTITY}, got: {qty}",
                severity=ValidationSeverity.ERROR
            )
        
        return ValidationResult(
            is_valid=True,
            field_name="quantity",
            message="Valid quantity"
        )
    
    @staticmethod
    def validate_price(price: Union[float, str, Decimal], field_name: str = "price", context: ErrorContext = None) -> ValidationResult:
        """Validate price values (price, trigger_price, etc.)"""
        if price is None:
            return ValidationResult(
                is_valid=False,
                field_name=field_name,
                message=f"{field_name} is required",
                severity=ValidationSeverity.ERROR
            )
        
        # Convert to Decimal for precise validation
        try:
            price_decimal = Decimal(str(price))
        except (ValueError, InvalidOperation):
            return ValidationResult(
                is_valid=False,
                field_name=field_name,
                message=f"{field_name} must be a valid number, got: {price}",
                severity=ValidationSeverity.ERROR
            )
        
        if price_decimal < TradeValidator.MIN_PRICE:
            return ValidationResult(
                is_valid=False,
                field_name=field_name,
                message=f"{field_name} must be at least {TradeValidator.MIN_PRICE}, got: {price_decimal}",
                severity=ValidationSeverity.ERROR
            )
        
        if price_decimal > TradeValidator.MAX_PRICE:
            return ValidationResult(
                is_valid=False,
                field_name=field_name,
                message=f"{field_name} cannot exceed {TradeValidator.MAX_PRICE}, got: {price_decimal}",
                severity=ValidationSeverity.ERROR
            )
        
        # Check decimal places (max 2)
        if price_decimal.as_tuple().exponent < -2:
            return ValidationResult(
                is_valid=False,
                field_name=field_name,
                message=f"{field_name} cannot have more than 2 decimal places, got: {price_decimal}",
                severity=ValidationSeverity.ERROR,
                suggested_value=float(price_decimal.quantize(Decimal('0.01')))
            )
        
        return ValidationResult(
            is_valid=True,
            field_name=field_name,
            message=f"Valid {field_name}"
        )
    
    @staticmethod
    def validate_trade_type(trade_type: str, context: ErrorContext = None) -> ValidationResult:
        """Validate trade type (BUY/SELL)"""
        if not trade_type:
            return ValidationResult(
                is_valid=False,
                field_name="trade_type",
                message="Trade type is required",
                severity=ValidationSeverity.ERROR
            )
        
        if not isinstance(trade_type, str):
            return ValidationResult(
                is_valid=False,
                field_name="trade_type",
                message=f"Trade type must be a string, got {type(trade_type).__name__}",
                severity=ValidationSeverity.ERROR
            )
        
        try:
            TradeType(trade_type.upper())
        except ValueError:
            return ValidationResult(
                is_valid=False,
                field_name="trade_type",
                message=f"Invalid trade type: {trade_type}. Valid types: {[t.value for t in TradeType]}",
                severity=ValidationSeverity.ERROR,
                suggested_value=trade_type.upper() if trade_type.upper() in [t.value for t in TradeType] else None
            )
        
        return ValidationResult(
            is_valid=True,
            field_name="trade_type",
            message="Valid trade type"
        )
    
    @staticmethod
    def validate_order_type(order_type: str, context: ErrorContext = None) -> ValidationResult:
        """Validate order type (MARKET/LIMIT/SL/SL-M)"""
        if not order_type:
            return ValidationResult(
                is_valid=False,
                field_name="order_type",
                message="Order type is required",
                severity=ValidationSeverity.ERROR
            )
        
        if not isinstance(order_type, str):
            return ValidationResult(
                is_valid=False,
                field_name="order_type",
                message=f"Order type must be a string, got {type(order_type).__name__}",
                severity=ValidationSeverity.ERROR
            )
        
        try:
            OrderType(order_type.upper())
        except ValueError:
            return ValidationResult(
                is_valid=False,
                field_name="order_type",
                message=f"Invalid order type: {order_type}. Valid types: {[t.value for t in OrderType]}",
                severity=ValidationSeverity.ERROR
            )
        
        return ValidationResult(
            is_valid=True,
            field_name="order_type",
            message="Valid order type"
        )
    
    @staticmethod
    def validate_exchange(exchange: str, context: ErrorContext = None) -> ValidationResult:
        """Validate exchange"""
        if not exchange:
            return ValidationResult(
                is_valid=False,
                field_name="exchange",
                message="Exchange is required",
                severity=ValidationSeverity.ERROR
            )
        
        if not isinstance(exchange, str):
            return ValidationResult(
                is_valid=False,
                field_name="exchange",
                message=f"Exchange must be a string, got {type(exchange).__name__}",
                severity=ValidationSeverity.ERROR
            )
        
        try:
            Exchange(exchange.upper())
        except ValueError:
            return ValidationResult(
                is_valid=False,
                field_name="exchange",
                message=f"Invalid exchange: {exchange}. Valid exchanges: {[e.value for e in Exchange]}",
                severity=ValidationSeverity.ERROR,
                suggested_value=exchange.upper() if exchange.upper() in [e.value for e in Exchange] else None
            )
        
        return ValidationResult(
            is_valid=True,
            field_name="exchange",
            message="Valid exchange"
        )
    
    @staticmethod
    def validate_pseudo_account(pseudo_account: str, context: ErrorContext = None) -> ValidationResult:
        """Validate pseudo account format"""
        if not pseudo_account:
            return ValidationResult(
                is_valid=False,
                field_name="pseudo_account",
                message="Pseudo account is required",
                severity=ValidationSeverity.ERROR
            )
        
        if not isinstance(pseudo_account, str):
            return ValidationResult(
                is_valid=False,
                field_name="pseudo_account",
                message=f"Pseudo account must be a string, got {type(pseudo_account).__name__}",
                severity=ValidationSeverity.ERROR
            )
        
        if not TradeValidator.PSEUDO_ACCOUNT_PATTERN.match(pseudo_account):
            return ValidationResult(
                is_valid=False,
                field_name="pseudo_account",
                message=f"Invalid pseudo account format: {pseudo_account}. Must be 3-50 chars, alphanumeric with _ and -",
                severity=ValidationSeverity.ERROR
            )
        
        return ValidationResult(
            is_valid=True,
            field_name="pseudo_account",
            message="Valid pseudo account format"
        )
    
    @staticmethod
    def validate_organization_id(organization_id: str, context: ErrorContext = None) -> ValidationResult:
        """Validate organization ID format"""
        if not organization_id:
            return ValidationResult(
                is_valid=False,
                field_name="organization_id",
                message="Organization ID is required",
                severity=ValidationSeverity.ERROR
            )
        
        if not isinstance(organization_id, str):
            return ValidationResult(
                is_valid=False,
                field_name="organization_id",
                message=f"Organization ID must be a string, got {type(organization_id).__name__}",
                severity=ValidationSeverity.ERROR
            )
        
        if not TradeValidator.ORGANIZATION_ID_PATTERN.match(organization_id):
            return ValidationResult(
                is_valid=False,
                field_name="organization_id",
                message=f"Invalid organization ID format: {organization_id}. Must be 3-50 chars, alphanumeric with _ and -",
                severity=ValidationSeverity.ERROR
            )
        
        return ValidationResult(
            is_valid=True,
            field_name="organization_id",
            message="Valid organization ID format"
        )
    
    @staticmethod
    def validate_strategy_id(strategy_id: str, context: ErrorContext = None, allow_none: bool = True) -> ValidationResult:
        """Validate strategy ID format"""
        if not strategy_id:
            if allow_none:
                return ValidationResult(
                    is_valid=True,
                    field_name="strategy_id",
                    message="Strategy ID is optional"
                )
            else:
                return ValidationResult(
                    is_valid=False,
                    field_name="strategy_id",
                    message="Strategy ID is required",
                    severity=ValidationSeverity.ERROR
                )
        
        if not isinstance(strategy_id, str):
            return ValidationResult(
                is_valid=False,
                field_name="strategy_id",
                message=f"Strategy ID must be a string, got {type(strategy_id).__name__}",
                severity=ValidationSeverity.ERROR
            )
        
        # Strategy ID can be alphanumeric with underscores and hyphens, 1-50 chars
        if not re.match(r'^[A-Za-z0-9_-]{1,50}$', strategy_id):
            return ValidationResult(
                is_valid=False,
                field_name="strategy_id",
                message=f"Invalid strategy ID format: {strategy_id}. Must be 1-50 chars, alphanumeric with _ and -",
                severity=ValidationSeverity.ERROR
            )
        
        return ValidationResult(
            is_valid=True,
            field_name="strategy_id",
            message="Valid strategy ID format"
        )

class OrderValidator:
    """Specialized validator for order-related data"""
    
    @staticmethod
    def validate_complete_order(order_data: Dict[str, Any], context: ErrorContext = None) -> List[ValidationResult]:
        """Validate a complete order with all required fields"""
        results = []
        
        # Required fields validation
        required_fields = [
            'pseudo_account', 'exchange', 'symbol', 'trade_type', 
            'order_type', 'quantity', 'price'
        ]
        
        for field in required_fields:
            if field not in order_data or order_data[field] is None:
                results.append(ValidationResult(
                    is_valid=False,
                    field_name=field,
                    message=f"Required field '{field}' is missing",
                    severity=ValidationSeverity.ERROR
                ))
        
        # Individual field validation
        if 'pseudo_account' in order_data:
            results.append(TradeValidator.validate_pseudo_account(order_data['pseudo_account'], context))
        
        if 'exchange' in order_data:
            results.append(TradeValidator.validate_exchange(order_data['exchange'], context))
        
        if 'symbol' in order_data:
            results.append(TradeValidator.validate_symbol(order_data['symbol'], context))
        
        if 'trade_type' in order_data:
            results.append(TradeValidator.validate_trade_type(order_data['trade_type'], context))
        
        if 'order_type' in order_data:
            results.append(TradeValidator.validate_order_type(order_data['order_type'], context))
        
        if 'quantity' in order_data:
            results.append(TradeValidator.validate_quantity(order_data['quantity'], context))
        
        if 'price' in order_data:
            results.append(TradeValidator.validate_price(order_data['price'], 'price', context))
        
        if 'trigger_price' in order_data and order_data['trigger_price'] is not None:
            results.append(TradeValidator.validate_price(order_data['trigger_price'], 'trigger_price', context))
        
        if 'organization_id' in order_data:
            results.append(TradeValidator.validate_organization_id(order_data['organization_id'], context))
        
        if 'strategy_id' in order_data:
            results.append(TradeValidator.validate_strategy_id(order_data['strategy_id'], context))
        
        # Business logic validation
        if 'order_type' in order_data and 'trigger_price' in order_data:
            order_type = order_data.get('order_type', '').upper()
            trigger_price = order_data.get('trigger_price')
            
            if order_type in ['SL', 'SL-M'] and (trigger_price is None or trigger_price <= 0):
                results.append(ValidationResult(
                    is_valid=False,
                    field_name="trigger_price",
                    message=f"Trigger price is required for {order_type} orders",
                    severity=ValidationSeverity.ERROR
                ))
        
        return results
    
    @staticmethod
    def validate_modify_order(modify_data: Dict[str, Any], context: ErrorContext = None) -> List[ValidationResult]:
        """Validate order modification data"""
        results = []
        
        # Order ID is required for modification
        if 'order_id' not in modify_data or not modify_data['order_id']:
            results.append(ValidationResult(
                is_valid=False,
                field_name="order_id",
                message="Order ID is required for modification",
                severity=ValidationSeverity.ERROR
            ))
        
        # Validate modifiable fields if present
        modifiable_fields = ['quantity', 'price', 'trigger_price']
        for field in modifiable_fields:
            if field in modify_data and modify_data[field] is not None:
                if field == 'quantity':
                    results.append(TradeValidator.validate_quantity(modify_data[field], context))
                else:
                    results.append(TradeValidator.validate_price(modify_data[field], field, context))
        
        return results

def validate_and_raise(validation_results: List[ValidationResult], context: ErrorContext = None):
    """Check validation results and raise ValidationException if any errors found"""
    errors = [r for r in validation_results if not r.is_valid and r.severity in [ValidationSeverity.ERROR, ValidationSeverity.CRITICAL]]
    
    if errors:
        error_messages = [f"{r.field_name}: {r.message}" for r in errors]
        raise ValidationException(
            message=f"Validation failed: {'; '.join(error_messages)}",
            context=context,
            field_name=errors[0].field_name if len(errors) == 1 else None
        )

def validate_with_warnings(validation_results: List[ValidationResult]) -> Dict[str, List[str]]:
    """Return validation summary with errors and warnings"""
    return {
        "errors": [f"{r.field_name}: {r.message}" for r in validation_results 
                  if not r.is_valid and r.severity in [ValidationSeverity.ERROR, ValidationSeverity.CRITICAL]],
        "warnings": [f"{r.field_name}: {r.message}" for r in validation_results 
                    if not r.is_valid and r.severity == ValidationSeverity.WARNING],
        "suggestions": {r.field_name: r.suggested_value for r in validation_results 
                       if r.suggested_value is not None}
    }