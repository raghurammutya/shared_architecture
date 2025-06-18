# shared_architecture/utils/trading_limit_validator.py

from typing import List, Dict, Any, Optional, Tuple
from sqlalchemy.orm import Session
from datetime import datetime, time
from decimal import Decimal

from ..db.models.user_trading_limits import UserTradingLimit, TradingLimitType, LimitEnforcement
from ..db.models.trading_limit_breach import TradingLimitBreach, BreachSeverity, BreachAction, BreachStatus
from ..db.models.trading_account import TradingAccount
from ..auth import UserContext
from ..utils.enhanced_logging import get_logger
from ..exceptions.trade_exceptions import ValidationException, AuthorizationException

logger = get_logger(__name__)

class TradingAction:
    """Represents a trading action to be validated"""
    def __init__(
        self,
        action_type: str,                    # place_order, modify_order, square_off, etc.
        instrument: str,
        quantity: int,
        price: Decimal,
        trade_value: Decimal,
        order_type: str = "MARKET",
        strategy_id: Optional[int] = None
    ):
        self.action_type = action_type
        self.instrument = instrument
        self.quantity = quantity
        self.price = price
        self.trade_value = trade_value
        self.order_type = order_type
        self.strategy_id = strategy_id
        self.timestamp = datetime.now()

class LimitValidationResult:
    """Result of limit validation"""
    def __init__(self):
        self.allowed = True
        self.violations: List[Dict[str, Any]] = []
        self.warnings: List[Dict[str, Any]] = []
        self.breaches_detected: List[TradingLimitBreach] = []
        self.actions_required: List[BreachAction] = []
        self.override_possible = False
        self.error_message: Optional[str] = None

class TradingLimitValidator:
    """
    Comprehensive trading limit validation and enforcement system
    Validates all trading actions against user-specific limits
    """
    
    def __init__(self):
        self.breach_handlers = {
            BreachSeverity.LOW: self._handle_low_severity_breach,
            BreachSeverity.MEDIUM: self._handle_medium_severity_breach,
            BreachSeverity.HIGH: self._handle_high_severity_breach,
            BreachSeverity.CRITICAL: self._handle_critical_severity_breach
        }
    
    async def validate_trading_action(
        self,
        user_context: UserContext,
        trading_account: TradingAccount,
        action: TradingAction,
        db: Session
    ) -> LimitValidationResult:
        """
        Validate a trading action against all applicable limits
        """
        result = LimitValidationResult()
        
        try:
            # Get all applicable limits for this user and account
            limits = self._get_applicable_limits(
                user_context, trading_account, action, db
            )
            
            if not limits:
                logger.debug(f"No trading limits found for user {user_context.user_id}")
                return result
            
            # Validate against each limit
            for limit in limits:
                violation = self._validate_single_limit(limit, action, db)
                
                if violation:
                    if limit.enforcement_type == LimitEnforcement.HARD_LIMIT:
                        result.allowed = False
                        result.violations.append(violation)
                        
                        # Create breach record
                        breach = self._create_breach_record(
                            user_context, trading_account, limit, action, violation, db
                        )
                        result.breaches_detected.append(breach)
                        
                        # Send alert for breach
                        await self._send_breach_alert(user_context, trading_account, limit, violation)
                        
                    elif limit.enforcement_type == LimitEnforcement.SOFT_LIMIT:
                        result.warnings.append(violation)
                        
                    elif limit.enforcement_type == LimitEnforcement.ADVISORY:
                        # Just log for monitoring
                        logger.info(f"Advisory limit exceeded: {violation}")
            
            # Determine required actions
            if result.breaches_detected:
                for breach in result.breaches_detected:
                    actions = self._determine_breach_actions(breach)
                    result.actions_required.extend(actions)
                    
                    # Check if override is possible
                    if breach.limit.override_allowed:
                        result.override_possible = True
            
            # Set error message if not allowed
            if not result.allowed:
                result.error_message = self._format_violation_message(result.violations)
            
            return result
            
        except Exception as e:
            logger.error(f"Error validating trading limits: {str(e)}")
            result.allowed = False
            result.error_message = f"Limit validation error: {str(e)}"
            return result
    
    def _get_applicable_limits(
        self,
        user_context: UserContext,
        trading_account: TradingAccount,
        action: TradingAction,
        db: Session
    ) -> List[UserTradingLimit]:
        """Get all limits applicable to this user and action"""
        
        query = db.query(UserTradingLimit).filter(
            UserTradingLimit.user_id == int(user_context.user_id),
            UserTradingLimit.trading_account_id == trading_account.id,
            UserTradingLimit.is_active == True
        )
        
        # Filter by strategy if applicable
        if action.strategy_id:
            query = query.filter(
                (UserTradingLimit.strategy_id == action.strategy_id) |
                (UserTradingLimit.strategy_id.is_(None))
            )
        else:
            query = query.filter(UserTradingLimit.strategy_id.is_(None))
        
        return query.all()
    
    def _validate_single_limit(
        self,
        limit: UserTradingLimit,
        action: TradingAction,
        db: Session
    ) -> Optional[Dict[str, Any]]:
        """Validate action against a single limit"""
        
        # Reset usage if needed
        self._reset_usage_if_needed(limit, db)
        
        # Validate based on limit type
        if limit.limit_type == TradingLimitType.DAILY_TRADING_LIMIT:
            return self._validate_daily_trading_limit(limit, action)
            
        elif limit.limit_type == TradingLimitType.SINGLE_TRADE_LIMIT:
            return self._validate_single_trade_limit(limit, action)
            
        elif limit.limit_type == TradingLimitType.DAILY_ORDER_COUNT:
            return self._validate_daily_order_count(limit, action)
            
        elif limit.limit_type == TradingLimitType.ALLOWED_INSTRUMENTS:
            return self._validate_allowed_instruments(limit, action)
            
        elif limit.limit_type == TradingLimitType.BLOCKED_INSTRUMENTS:
            return self._validate_blocked_instruments(limit, action)
            
        elif limit.limit_type == TradingLimitType.TRADING_HOURS:
            return self._validate_trading_hours(limit, action)
            
        elif limit.limit_type == TradingLimitType.SINGLE_ORDER_QUANTITY:
            return self._validate_single_order_quantity(limit, action)
            
        elif limit.limit_type == TradingLimitType.MAX_OPEN_POSITIONS:
            return self._validate_max_open_positions(limit, action, db)
        
        # Add more limit type validations as needed
        return None
    
    def _validate_daily_trading_limit(
        self,
        limit: UserTradingLimit,
        action: TradingAction
    ) -> Optional[Dict[str, Any]]:
        """Validate daily trading value limit"""
        
        projected_usage = limit.current_usage_value + action.trade_value
        
        if projected_usage > limit.limit_value:
            return {
                "limit_type": "daily_trading_limit",
                "limit_value": float(limit.limit_value),
                "current_usage": float(limit.current_usage_value),
                "attempted_value": float(action.trade_value),
                "projected_usage": float(projected_usage),
                "breach_amount": float(projected_usage - limit.limit_value),
                "message": f"Daily trading limit of ₹{limit.limit_value:,.2f} would be exceeded. Current usage: ₹{limit.current_usage_value:,.2f}, Attempted: ₹{action.trade_value:,.2f}"
            }
        
        return None
    
    def _validate_single_trade_limit(
        self,
        limit: UserTradingLimit,
        action: TradingAction
    ) -> Optional[Dict[str, Any]]:
        """Validate single trade value limit"""
        
        if action.trade_value > limit.limit_value:
            return {
                "limit_type": "single_trade_limit",
                "limit_value": float(limit.limit_value),
                "attempted_value": float(action.trade_value),
                "breach_amount": float(action.trade_value - limit.limit_value),
                "message": f"Single trade limit of ₹{limit.limit_value:,.2f} exceeded. Attempted trade: ₹{action.trade_value:,.2f}"
            }
        
        return None
    
    def _validate_daily_order_count(
        self,
        limit: UserTradingLimit,
        action: TradingAction
    ) -> Optional[Dict[str, Any]]:
        """Validate daily order count limit"""
        
        projected_count = limit.current_usage_count + 1
        
        if projected_count > limit.limit_count:
            return {
                "limit_type": "daily_order_count",
                "limit_count": limit.limit_count,
                "current_count": limit.current_usage_count,
                "projected_count": projected_count,
                "message": f"Daily order limit of {limit.limit_count} orders would be exceeded. Current orders: {limit.current_usage_count}"
            }
        
        return None
    
    def _validate_allowed_instruments(
        self,
        limit: UserTradingLimit,
        action: TradingAction
    ) -> Optional[Dict[str, Any]]:
        """Validate allowed instruments whitelist"""
        
        if not limit.check_instrument_restriction(action.instrument):
            allowed_list = limit.limit_text or "None"
            return {
                "limit_type": "allowed_instruments",
                "instrument": action.instrument,
                "allowed_instruments": allowed_list,
                "message": f"Instrument {action.instrument} is not in allowed list: {allowed_list}"
            }
        
        return None
    
    def _validate_blocked_instruments(
        self,
        limit: UserTradingLimit,
        action: TradingAction
    ) -> Optional[Dict[str, Any]]:
        """Validate blocked instruments blacklist"""
        
        if not limit.check_instrument_restriction(action.instrument):
            blocked_list = limit.limit_text or "None"
            return {
                "limit_type": "blocked_instruments",
                "instrument": action.instrument,
                "blocked_instruments": blocked_list,
                "message": f"Instrument {action.instrument} is in blocked list: {blocked_list}"
            }
        
        return None
    
    def _validate_trading_hours(
        self,
        limit: UserTradingLimit,
        action: TradingAction
    ) -> Optional[Dict[str, Any]]:
        """Validate trading hours restriction"""
        
        if not limit.check_time_restriction(action.timestamp):
            return {
                "limit_type": "trading_hours",
                "current_time": action.timestamp.strftime("%H:%M:%S"),
                "allowed_start": limit.start_time.strftime("%H:%M:%S") if limit.start_time else "Not set",
                "allowed_end": limit.end_time.strftime("%H:%M:%S") if limit.end_time else "Not set",
                "allowed_days": limit.allowed_days or "All days",
                "message": f"Trading not allowed at {action.timestamp.strftime('%H:%M:%S on %A')}. Allowed: {limit.start_time}-{limit.end_time} on {limit.allowed_days or 'all days'}"
            }
        
        return None
    
    def _validate_single_order_quantity(
        self,
        limit: UserTradingLimit,
        action: TradingAction
    ) -> Optional[Dict[str, Any]]:
        """Validate single order quantity limit"""
        
        if action.quantity > limit.limit_count:
            return {
                "limit_type": "single_order_quantity",
                "limit_quantity": limit.limit_count,
                "attempted_quantity": action.quantity,
                "breach_amount": action.quantity - limit.limit_count,
                "message": f"Single order quantity limit of {limit.limit_count} shares exceeded. Attempted: {action.quantity} shares"
            }
        
        return None
    
    def _validate_max_open_positions(
        self,
        limit: UserTradingLimit,
        action: TradingAction,
        db: Session
    ) -> Optional[Dict[str, Any]]:
        """Validate maximum open positions limit"""
        
        # This would require querying current positions from trade_service
        # For now, return a placeholder validation
        current_positions = 0  # Would be fetched from trade_service
        
        if action.action_type == "place_order" and current_positions >= limit.limit_count:
            return {
                "limit_type": "max_open_positions",
                "limit_count": limit.limit_count,
                "current_positions": current_positions,
                "message": f"Maximum open positions limit of {limit.limit_count} reached. Current positions: {current_positions}"
            }
        
        return None
    
    def _reset_usage_if_needed(self, limit: UserTradingLimit, db: Session):
        """Reset usage counters if reset period has elapsed"""
        
        if not limit.auto_reset or not limit.last_reset_at:
            return
        
        now = datetime.utcnow()
        reset_needed = False
        
        if limit.usage_reset_frequency == "daily":
            reset_needed = now.date() > limit.last_reset_at.date()
        elif limit.usage_reset_frequency == "weekly":
            days_since_reset = (now - limit.last_reset_at).days
            reset_needed = days_since_reset >= 7
        elif limit.usage_reset_frequency == "monthly":
            reset_needed = (now.year, now.month) > (limit.last_reset_at.year, limit.last_reset_at.month)
        
        if reset_needed:
            limit.reset_usage()
            db.commit()
            logger.info(f"Reset usage for limit {limit.id} ({limit.limit_type.value})")
    
    def _create_breach_record(
        self,
        user_context: UserContext,
        trading_account: TradingAccount,
        limit: UserTradingLimit,
        action: TradingAction,
        violation: Dict[str, Any],
        db: Session
    ) -> TradingLimitBreach:
        """Create a breach record for tracking and monitoring"""
        
        breach = TradingLimitBreach(
            user_id=int(user_context.user_id),
            trading_account_id=trading_account.id,
            organization_id=trading_account.organization_id,
            limit_id=limit.id,
            breach_type=limit.limit_type.value,
            severity=self._determine_breach_severity(limit, violation),
            limit_value=limit.limit_value,
            attempted_value=violation.get("attempted_value"),
            current_usage=limit.current_usage_value,
            breach_amount=violation.get("breach_amount"),
            action_attempted=action.action_type,
            instrument_symbol=action.instrument,
            breach_reason=violation.get("message")
        )
        
        db.add(breach)
        db.commit()
        db.refresh(breach)
        
        # Update limit breach count
        limit.breach_count += 1
        limit.consecutive_breaches += 1
        limit.last_breach_at = datetime.utcnow()
        db.commit()
        
        logger.warning(f"Trading limit breach detected: {breach.breach_type} for user {user_context.user_id}")
        
        return breach
    
    async def _send_breach_alert(self, user_context: UserContext, trading_account, limit, violation: Dict[str, Any]):
        """Send alert for trading limit breach"""
        try:
            from ..events.alert_system import get_alert_manager, AlertSeverity
            
            # Determine alert severity based on breach
            breach_percentage = violation.get("breach_amount", 0) / violation.get("limit_value", 1) * 100
            if breach_percentage > 50:
                severity = AlertSeverity.CRITICAL
            elif breach_percentage > 25:
                severity = AlertSeverity.ERROR
            else:
                severity = AlertSeverity.WARNING
            
            alert_manager = get_alert_manager()
            await alert_manager.create_trading_limit_breach_alert(
                user_id=int(user_context.user_id),
                organization_id=trading_account.organization_id,
                limit_type=limit.limit_type.value,
                breach_amount=violation.get("breach_amount", 0),
                current_usage=violation.get("current_usage", 0),
                limit_value=violation.get("limit_value", 0),
                severity=severity
            )
            
        except Exception as e:
            logger.error(f"Failed to send breach alert: {e}")
    
    def _determine_breach_severity(
        self,
        limit: UserTradingLimit,
        violation: Dict[str, Any]
    ) -> BreachSeverity:
        """Determine severity of the breach"""
        
        breach_percentage = 0
        if "breach_amount" in violation and "limit_value" in violation:
            limit_value = violation["limit_value"]
            breach_amount = violation["breach_amount"]
            if limit_value > 0:
                breach_percentage = (breach_amount / limit_value) * 100
        
        # Determine severity based on breach percentage and consecutive breaches
        if breach_percentage > 50 or limit.consecutive_breaches >= 5:
            return BreachSeverity.CRITICAL
        elif breach_percentage > 25 or limit.consecutive_breaches >= 3:
            return BreachSeverity.HIGH
        elif breach_percentage > 10 or limit.consecutive_breaches >= 1:
            return BreachSeverity.MEDIUM
        else:
            return BreachSeverity.LOW
    
    def _determine_breach_actions(self, breach: TradingLimitBreach) -> List[BreachAction]:
        """Determine what actions to take for a breach"""
        
        actions = []
        
        if breach.severity == BreachSeverity.LOW:
            actions.append(BreachAction.WARNING)
            
        elif breach.severity == BreachSeverity.MEDIUM:
            actions.extend([BreachAction.WARNING, BreachAction.NOTIFY_ADMIN])
            
        elif breach.severity == BreachSeverity.HIGH:
            actions.extend([BreachAction.WARNING, BreachAction.RESTRICT, BreachAction.NOTIFY_ADMIN])
            
        elif breach.severity == BreachSeverity.CRITICAL:
            actions.extend([
                BreachAction.WARNING, 
                BreachAction.SUSPEND, 
                BreachAction.NOTIFY_ADMIN,
                BreachAction.AUTO_SQUARE_OFF
            ])
        
        return actions
    
    def _format_violation_message(self, violations: List[Dict[str, Any]]) -> str:
        """Format violations into a user-friendly message"""
        
        if not violations:
            return "Trading action not allowed"
        
        messages = [v.get("message", "Limit exceeded") for v in violations]
        return "; ".join(messages)
    
    def update_usage_after_trade(
        self,
        user_context: UserContext,
        trading_account: TradingAccount,
        action: TradingAction,
        db: Session
    ):
        """Update usage counters after a successful trade"""
        
        limits = self._get_applicable_limits(user_context, trading_account, action, db)
        
        for limit in limits:
            if limit.limit_type in [
                TradingLimitType.DAILY_TRADING_LIMIT,
                TradingLimitType.MONTHLY_TRADING_LIMIT
            ]:
                limit.current_usage_value += action.trade_value
                
            elif limit.limit_type == TradingLimitType.DAILY_ORDER_COUNT:
                limit.current_usage_count += 1
            
            # Reset consecutive breaches on successful trade
            limit.consecutive_breaches = 0
        
        db.commit()
        logger.debug(f"Updated usage counters for user {user_context.user_id}")
    
    # Breach handling methods
    def _handle_low_severity_breach(self, breach: TradingLimitBreach, db: Session):
        """Handle low severity breaches"""
        breach.add_action_taken(BreachAction.WARNING)
        # Send warning notification
        
    def _handle_medium_severity_breach(self, breach: TradingLimitBreach, db: Session):
        """Handle medium severity breaches"""
        breach.add_action_taken(BreachAction.WARNING)
        breach.add_action_taken(BreachAction.NOTIFY_ADMIN)
        # Send warning and notify admin
        
    def _handle_high_severity_breach(self, breach: TradingLimitBreach, db: Session):
        """Handle high severity breaches"""
        breach.add_action_taken(BreachAction.WARNING)
        breach.add_action_taken(BreachAction.RESTRICT)
        breach.add_action_taken(BreachAction.NOTIFY_ADMIN)
        # Restrict further trading and alert admin
        
    def _handle_critical_severity_breach(self, breach: TradingLimitBreach, db: Session):
        """Handle critical severity breaches"""
        breach.add_action_taken(BreachAction.WARNING)
        breach.add_action_taken(BreachAction.SUSPEND)
        breach.add_action_taken(BreachAction.NOTIFY_ADMIN)
        breach.add_action_taken(BreachAction.AUTO_SQUARE_OFF)
        # Suspend trading, alert admin, consider auto square-off

# Global instance
trading_limit_validator = TradingLimitValidator()

def get_trading_limit_validator() -> TradingLimitValidator:
    """Get global trading limit validator instance"""
    return trading_limit_validator