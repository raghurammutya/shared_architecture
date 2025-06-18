# shared_architecture/utils/trading_permissions.py

from typing import List, Dict, Any, Optional, Set
from sqlalchemy.orm import Session
from enum import Enum

from ..db.models.trading_account_permission import PermissionType, TradingAccountPermission
from ..db.models.trading_account import TradingAccount
from ..db.models.organization import Organization
from ..db.models.risk_limits import RiskLimit, RiskLimitType
from ..db.models.trading_action_log import TradingActionLog, ActionType, ActionStatus
from ..auth import UserContext
from ..utils.enhanced_logging import get_logger
from ..exceptions.trade_exceptions import AuthorizationException, ValidationException

logger = get_logger(__name__)

class PermissionLevel(Enum):
    """Hierarchical permission levels"""
    NONE = 0
    READ_ONLY = 1
    LIMITED_TRADING = 2
    FULL_TRADING = 3
    ADMIN_TRADING = 4

class TradingPermissionValidator:
    """
    Comprehensive trading permission validation system
    Handles hierarchical permissions, risk limits, and audit logging
    """
    
    def __init__(self):
        # Permission hierarchy mapping
        self.READ_PERMISSIONS = {
            PermissionType.VIEW_POSITIONS,
            PermissionType.VIEW_ORDERS,
            PermissionType.VIEW_TRADES,
            PermissionType.VIEW_BALANCE,
            PermissionType.VIEW_PNL,
            PermissionType.VIEW_ANALYTICS,
            PermissionType.VIEW_STRATEGIES,
            PermissionType.VIEW_PORTFOLIO,
            PermissionType.FULL_READ
        }
        
        self.ORDER_PERMISSIONS = {
            PermissionType.PLACE_ORDERS,
            PermissionType.MODIFY_ORDERS,
            PermissionType.CANCEL_ORDERS,
            PermissionType.SQUARE_OFF_POSITIONS
        }
        
        self.STRATEGY_PERMISSIONS = {
            PermissionType.CREATE_STRATEGY,
            PermissionType.MODIFY_STRATEGY,
            PermissionType.ADJUST_STRATEGY,
            PermissionType.SQUARE_OFF_STRATEGY,
            PermissionType.DELETE_STRATEGY
        }
        
        self.PORTFOLIO_PERMISSIONS = {
            PermissionType.SQUARE_OFF_PORTFOLIO,
            PermissionType.MANAGE_PORTFOLIO
        }
        
        self.RISK_PERMISSIONS = {
            PermissionType.SET_RISK_LIMITS,
            PermissionType.OVERRIDE_RISK_LIMITS
        }
        
        self.ADMIN_PERMISSIONS = {
            PermissionType.BULK_OPERATIONS,
            PermissionType.ADMIN_TRADING
        }
        
        # High-risk actions that require special validation
        self.HIGH_RISK_ACTIONS = {
            ActionType.SQUARE_OFF_PORTFOLIO,
            ActionType.OVERRIDE_RISK_LIMIT,
            ActionType.BULK_SQUARE_OFF,
            ActionType.DELETE_STRATEGY
        }
    
    def get_user_permission_level(
        self, 
        user_context: UserContext, 
        trading_account: TradingAccount,
        db: Session
    ) -> PermissionLevel:
        """
        Determine user's permission level for a trading account
        """
        try:
            # Organization owners have admin trading access
            if trading_account.organization.owner_id == int(user_context.user_id):
                return PermissionLevel.ADMIN_TRADING
            
            # Backup owners have full trading access
            if trading_account.organization.backup_owner_id == int(user_context.user_id):
                return PermissionLevel.FULL_TRADING
            
            # Assigned users have full trading access
            if trading_account.assigned_user_id == int(user_context.user_id):
                return PermissionLevel.FULL_TRADING
            
            # Check explicit permissions
            user_permissions = self.get_user_permissions(user_context, trading_account, db)
            
            if PermissionType.ADMIN_TRADING in user_permissions:
                return PermissionLevel.ADMIN_TRADING
            elif PermissionType.FULL_TRADING in user_permissions:
                return PermissionLevel.FULL_TRADING
            elif any(perm in self.ORDER_PERMISSIONS for perm in user_permissions):
                return PermissionLevel.LIMITED_TRADING
            elif any(perm in self.READ_PERMISSIONS for perm in user_permissions):
                return PermissionLevel.READ_ONLY
            
            return PermissionLevel.NONE
            
        except Exception as e:
            logger.error(f"Error determining permission level: {str(e)}")
            return PermissionLevel.NONE
    
    def get_user_permissions(
        self, 
        user_context: UserContext, 
        trading_account: TradingAccount,
        db: Session
    ) -> Set[PermissionType]:
        """
        Get all effective permissions for user on trading account
        """
        permissions = set()
        
        try:
            # Get explicit permissions
            user_permissions = db.query(TradingAccountPermission).filter(
                TradingAccountPermission.user_id == int(user_context.user_id),
                TradingAccountPermission.trading_account_id == trading_account.id,
                TradingAccountPermission.is_active == True
            ).all()
            
            for permission in user_permissions:
                if permission.is_valid:
                    permissions.add(permission.permission_type)
            
            # Expand grouped permissions
            if PermissionType.FULL_READ in permissions:
                permissions.update(self.READ_PERMISSIONS)
            
            if PermissionType.FULL_TRADING in permissions:
                permissions.update(self.READ_PERMISSIONS)
                permissions.update(self.ORDER_PERMISSIONS)
                permissions.update(self.STRATEGY_PERMISSIONS)
                permissions.update(self.PORTFOLIO_PERMISSIONS)
            
            if PermissionType.ADMIN_TRADING in permissions:
                permissions.update(self.READ_PERMISSIONS)
                permissions.update(self.ORDER_PERMISSIONS)
                permissions.update(self.STRATEGY_PERMISSIONS)
                permissions.update(self.PORTFOLIO_PERMISSIONS)
                permissions.update(self.RISK_PERMISSIONS)
                permissions.update(self.ADMIN_PERMISSIONS)
            
            return permissions
            
        except Exception as e:
            logger.error(f"Error getting user permissions: {str(e)}")
            return set()
    
    def validate_trading_action(
        self,
        user_context: UserContext,
        trading_account: TradingAccount,
        action_type: ActionType,
        action_data: Dict[str, Any],
        db: Session
    ) -> Dict[str, Any]:
        """
        Comprehensive validation for trading actions
        
        Returns:
            Dict with validation result and details
        """
        validation_result = {
            "allowed": False,
            "permission_level": PermissionLevel.NONE,
            "required_permission": None,
            "missing_permissions": [],
            "risk_violations": [],
            "requires_approval": False,
            "error_message": None
        }
        
        try:
            # 1. Check basic permission level
            permission_level = self.get_user_permission_level(user_context, trading_account, db)
            validation_result["permission_level"] = permission_level
            
            if permission_level == PermissionLevel.NONE:
                validation_result["error_message"] = "No access to this trading account"
                return validation_result
            
            # 2. Map action to required permission
            required_permission = self._map_action_to_permission(action_type)
            validation_result["required_permission"] = required_permission
            
            if required_permission is None:
                validation_result["error_message"] = f"Unknown action type: {action_type}"
                return validation_result
            
            # 3. Check specific permission
            user_permissions = self.get_user_permissions(user_context, trading_account, db)
            
            if required_permission not in user_permissions:
                validation_result["missing_permissions"] = [required_permission]
                validation_result["error_message"] = f"Missing permission: {required_permission.value}"
                return validation_result
            
            # 4. Validate risk limits
            risk_violations = self._validate_risk_limits(
                trading_account, action_type, action_data, db
            )
            validation_result["risk_violations"] = risk_violations
            
            # 5. Check if action requires approval
            requires_approval = self._requires_approval(
                action_type, action_data, risk_violations, permission_level
            )
            validation_result["requires_approval"] = requires_approval
            
            # 6. Final approval
            if risk_violations and not self._can_override_risk(user_permissions):
                validation_result["error_message"] = f"Risk limit violations: {risk_violations}"
                return validation_result
            
            validation_result["allowed"] = True
            return validation_result
            
        except Exception as e:
            logger.error(f"Error validating trading action: {str(e)}")
            validation_result["error_message"] = f"Validation error: {str(e)}"
            return validation_result
    
    def _map_action_to_permission(self, action_type: ActionType) -> Optional[PermissionType]:
        """Map action types to required permissions"""
        action_permission_map = {
            # Order actions
            ActionType.PLACE_ORDER: PermissionType.PLACE_ORDERS,
            ActionType.MODIFY_ORDER: PermissionType.MODIFY_ORDERS,
            ActionType.CANCEL_ORDER: PermissionType.CANCEL_ORDERS,
            ActionType.SQUARE_OFF_POSITION: PermissionType.SQUARE_OFF_POSITIONS,
            
            # Strategy actions
            ActionType.CREATE_STRATEGY: PermissionType.CREATE_STRATEGY,
            ActionType.MODIFY_STRATEGY: PermissionType.MODIFY_STRATEGY,
            ActionType.ADJUST_STRATEGY: PermissionType.ADJUST_STRATEGY,
            ActionType.SQUARE_OFF_STRATEGY: PermissionType.SQUARE_OFF_STRATEGY,
            ActionType.DELETE_STRATEGY: PermissionType.DELETE_STRATEGY,
            
            # Portfolio actions
            ActionType.SQUARE_OFF_PORTFOLIO: PermissionType.SQUARE_OFF_PORTFOLIO,
            
            # Risk actions
            ActionType.SET_RISK_LIMIT: PermissionType.SET_RISK_LIMITS,
            ActionType.OVERRIDE_RISK_LIMIT: PermissionType.OVERRIDE_RISK_LIMITS,
            
            # Bulk actions
            ActionType.BULK_SQUARE_OFF: PermissionType.BULK_OPERATIONS,
            ActionType.BULK_CANCEL: PermissionType.BULK_OPERATIONS,
        }
        
        return action_permission_map.get(action_type)
    
    def _validate_risk_limits(
        self,
        trading_account: TradingAccount,
        action_type: ActionType,
        action_data: Dict[str, Any],
        db: Session
    ) -> List[str]:
        """
        Validate action against risk limits
        
        Returns:
            List of risk violation messages
        """
        violations = []
        
        try:
            # Get active risk limits for this account
            risk_limits = db.query(RiskLimit).filter(
                RiskLimit.trading_account_id == trading_account.id,
                RiskLimit.is_active == True
            ).all()
            
            for limit in risk_limits:
                violation = self._check_single_risk_limit(limit, action_type, action_data)
                if violation:
                    violations.append(violation)
            
            return violations
            
        except Exception as e:
            logger.error(f"Error validating risk limits: {str(e)}")
            return [f"Risk validation error: {str(e)}"]
    
    def _check_single_risk_limit(
        self,
        risk_limit: RiskLimit,
        action_type: ActionType,
        action_data: Dict[str, Any]
    ) -> Optional[str]:
        """Check if action violates a specific risk limit"""
        
        try:
            if risk_limit.limit_type == RiskLimitType.SINGLE_TRADE_RISK:
                trade_value = action_data.get("quantity", 0) * action_data.get("price", 0)
                if trade_value > risk_limit.limit_value:
                    return f"Trade value {trade_value} exceeds single trade limit {risk_limit.limit_value}"
            
            elif risk_limit.limit_type == RiskLimitType.POSITION_SIZE_LIMIT:
                quantity = action_data.get("quantity", 0)
                if quantity > risk_limit.limit_value:
                    return f"Position size {quantity} exceeds limit {risk_limit.limit_value}"
            
            elif risk_limit.limit_type == RiskLimitType.DAILY_LOSS_LIMIT:
                if risk_limit.current_usage > risk_limit.limit_value:
                    return f"Daily loss limit {risk_limit.limit_value} already exceeded"
            
            # Add more risk limit checks as needed
            
            return None
            
        except Exception as e:
            logger.error(f"Error checking risk limit: {str(e)}")
            return f"Risk check error: {str(e)}"
    
    def _requires_approval(
        self,
        action_type: ActionType,
        action_data: Dict[str, Any],
        risk_violations: List[str],
        permission_level: PermissionLevel
    ) -> bool:
        """Determine if action requires approval"""
        
        # High-risk actions always require approval
        if action_type in self.HIGH_RISK_ACTIONS:
            return True
        
        # Risk violations require approval unless user can override
        if risk_violations and permission_level < PermissionLevel.ADMIN_TRADING:
            return True
        
        # Large trades require approval
        trade_value = action_data.get("quantity", 0) * action_data.get("price", 0)
        if trade_value > 1000000:  # 10L+ trades need approval
            return True
        
        return False
    
    def _can_override_risk(self, user_permissions: Set[PermissionType]) -> bool:
        """Check if user can override risk limits"""
        return PermissionType.OVERRIDE_RISK_LIMITS in user_permissions
    
    def log_trading_action(
        self,
        user_context: UserContext,
        trading_account: TradingAccount,
        action_type: ActionType,
        action_data: Dict[str, Any],
        validation_result: Dict[str, Any],
        db: Session
    ) -> TradingActionLog:
        """
        Log trading action for audit trail
        """
        try:
            action_log = TradingActionLog(
                action_type=action_type,
                action_status=ActionStatus.PENDING if validation_result["allowed"] else ActionStatus.REJECTED,
                user_id=int(user_context.user_id),
                trading_account_id=trading_account.id,
                organization_id=trading_account.organization_id,
                instrument_symbol=action_data.get("symbol"),
                quantity=action_data.get("quantity"),
                price=action_data.get("price"),
                order_type=action_data.get("order_type"),
                action_data=str(action_data),
                requires_approval=validation_result["requires_approval"],
                error_message=validation_result.get("error_message")
            )
            
            db.add(action_log)
            db.commit()
            db.refresh(action_log)
            
            logger.info(f"Logged trading action: {action_type.value} by user {user_context.username}")
            return action_log
            
        except Exception as e:
            logger.error(f"Error logging trading action: {str(e)}")
            db.rollback()
            raise ValidationException(
                message="Failed to log trading action",
                details={"error": str(e)}
            )

# Global instance
trading_permission_validator = TradingPermissionValidator()

def get_trading_permission_validator() -> TradingPermissionValidator:
    """Get global trading permission validator instance"""
    return trading_permission_validator