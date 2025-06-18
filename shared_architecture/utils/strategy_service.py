# shared_architecture/utils/strategy_service.py

import httpx
import json
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from datetime import datetime

from ..utils.enhanced_logging import get_logger
from ..exceptions.trade_exceptions import AuthenticationException, ValidationException
from ..db.models.strategy import Strategy, StrategyStatus, StrategyType
from ..db.models.strategy_permission import StrategyPermission, StrategyPermissionType
from ..db.models.strategy_action_log import StrategyActionLog, StrategyActionType, StrategyActionStatus
from ..db.models.trading_account import TradingAccount
from ..auth import UserContext

logger = get_logger(__name__)

class StrategyService:
    """
    Service for managing strategies and integrating with trade_service
    Handles strategy CRUD operations, permissions, and trade_service communication
    """
    
    def __init__(self, trade_service_url: str):
        self.trade_service_url = trade_service_url.rstrip('/')
        self.timeout = 30.0
    
    async def create_strategy(
        self,
        user_context: UserContext,
        trading_account: TradingAccount,
        strategy_data: Dict[str, Any],
        db: Session
    ) -> Strategy:
        """
        Create a new strategy in local database and sync with trade_service
        """
        try:
            # Create local strategy
            strategy = Strategy(
                name=strategy_data["name"],
                description=strategy_data.get("description"),
                strategy_type=StrategyType(strategy_data["strategy_type"]),
                trading_account_id=trading_account.id,
                organization_id=trading_account.organization_id,
                created_by_id=int(user_context.user_id),
                assigned_to_id=strategy_data.get("assigned_to_id"),
                initial_capital=strategy_data.get("initial_capital"),
                auto_square_off=strategy_data.get("auto_square_off", False),
                max_loss_limit=strategy_data.get("max_loss_limit"),
                max_profit_target=strategy_data.get("max_profit_target")
            )
            
            # Set parameters
            if "parameters" in strategy_data:
                strategy.set_parameters(strategy_data["parameters"])
            if "risk_parameters" in strategy_data:
                strategy.set_risk_parameters(strategy_data["risk_parameters"])
            
            db.add(strategy)
            db.flush()  # Get the ID
            
            # Create strategy in trade_service
            trade_service_response = await self._create_strategy_in_trade_service(
                user_context, trading_account, strategy, db
            )
            
            # Update with trade_service ID
            strategy.trade_service_strategy_id = trade_service_response.get("strategy_id")
            
            # Log action
            self._log_strategy_action(
                user_context, strategy, StrategyActionType.CREATE_STRATEGY,
                strategy_data, StrategyActionStatus.EXECUTED, db
            )
            
            db.commit()
            db.refresh(strategy)
            
            logger.info(f"Strategy created: {strategy.name} (ID: {strategy.id})")
            return strategy
            
        except Exception as e:
            logger.error(f"Failed to create strategy: {str(e)}")
            db.rollback()
            raise ValidationException(
                message="Failed to create strategy",
                details={"error": str(e)}
            )
    
    async def modify_strategy(
        self,
        user_context: UserContext,
        strategy: Strategy,
        update_data: Dict[str, Any],
        db: Session
    ) -> Strategy:
        """
        Modify an existing strategy
        """
        try:
            if not strategy.can_be_modified:
                raise ValidationException(
                    message=f"Strategy cannot be modified in {strategy.status.value} status"
                )
            
            # Store before state
            before_state = {
                "parameters": strategy.parameters_dict,
                "risk_parameters": strategy.risk_parameters_dict,
                "status": strategy.status.value
            }
            
            # Update local strategy
            if "name" in update_data:
                strategy.name = update_data["name"]
            if "description" in update_data:
                strategy.description = update_data["description"]
            if "parameters" in update_data:
                strategy.set_parameters(update_data["parameters"])
            if "risk_parameters" in update_data:
                strategy.set_risk_parameters(update_data["risk_parameters"])
            if "max_loss_limit" in update_data:
                strategy.max_loss_limit = update_data["max_loss_limit"]
            if "max_profit_target" in update_data:
                strategy.max_profit_target = update_data["max_profit_target"]
            
            # Sync with trade_service
            if strategy.trade_service_strategy_id:
                await self._update_strategy_in_trade_service(
                    user_context, strategy, update_data, db
                )
            
            # Store after state
            after_state = {
                "parameters": strategy.parameters_dict,
                "risk_parameters": strategy.risk_parameters_dict,
                "status": strategy.status.value
            }
            
            # Log action
            self._log_strategy_action(
                user_context, strategy, StrategyActionType.MODIFY_STRATEGY,
                update_data, StrategyActionStatus.EXECUTED, db,
                before_state=before_state, after_state=after_state
            )
            
            db.commit()
            db.refresh(strategy)
            
            logger.info(f"Strategy modified: {strategy.name} (ID: {strategy.id})")
            return strategy
            
        except Exception as e:
            logger.error(f"Failed to modify strategy: {str(e)}")
            db.rollback()
            raise ValidationException(
                message="Failed to modify strategy",
                details={"error": str(e)}
            )
    
    async def start_strategy(
        self,
        user_context: UserContext,
        strategy: Strategy,
        db: Session
    ) -> Dict[str, Any]:
        """
        Start/activate a strategy
        """
        try:
            if not strategy.can_be_started:
                raise ValidationException(
                    message=f"Strategy cannot be started in {strategy.status.value} status"
                )
            
            # Start strategy in trade_service
            response = await self._start_strategy_in_trade_service(
                user_context, strategy, db
            )
            
            # Update local status
            strategy.status = StrategyStatus.ACTIVE
            strategy.started_at = datetime.utcnow()
            
            # Log action
            self._log_strategy_action(
                user_context, strategy, StrategyActionType.START_STRATEGY,
                {}, StrategyActionStatus.EXECUTED, db
            )
            
            db.commit()
            
            logger.info(f"Strategy started: {strategy.name} (ID: {strategy.id})")
            return response
            
        except Exception as e:
            logger.error(f"Failed to start strategy: {str(e)}")
            db.rollback()
            raise ValidationException(
                message="Failed to start strategy",
                details={"error": str(e)}
            )
    
    async def stop_strategy(
        self,
        user_context: UserContext,
        strategy: Strategy,
        reason: Optional[str],
        db: Session
    ) -> Dict[str, Any]:
        """
        Stop a running strategy
        """
        try:
            if not strategy.can_be_stopped:
                raise ValidationException(
                    message=f"Strategy cannot be stopped in {strategy.status.value} status"
                )
            
            # Stop strategy in trade_service
            response = await self._stop_strategy_in_trade_service(
                user_context, strategy, reason, db
            )
            
            # Update local status
            strategy.status = StrategyStatus.STOPPED
            strategy.completed_at = datetime.utcnow()
            
            # Log action
            self._log_strategy_action(
                user_context, strategy, StrategyActionType.STOP_STRATEGY,
                {"reason": reason}, StrategyActionStatus.EXECUTED, db
            )
            
            db.commit()
            
            logger.info(f"Strategy stopped: {strategy.name} (ID: {strategy.id})")
            return response
            
        except Exception as e:
            logger.error(f"Failed to stop strategy: {str(e)}")
            db.rollback()
            raise ValidationException(
                message="Failed to stop strategy",
                details={"error": str(e)}
            )
    
    async def square_off_strategy(
        self,
        user_context: UserContext,
        strategy: Strategy,
        reason: Optional[str],
        force_exit: bool,
        db: Session
    ) -> Dict[str, Any]:
        """
        Square off all positions in a strategy
        """
        try:
            # Square off in trade_service
            response = await self._square_off_strategy_in_trade_service(
                user_context, strategy, reason, force_exit, db
            )
            
            # Update local status
            strategy.status = StrategyStatus.SQUARED_OFF
            strategy.completed_at = datetime.utcnow()
            
            # Log action
            self._log_strategy_action(
                user_context, strategy, StrategyActionType.SQUARE_OFF_STRATEGY,
                {"reason": reason, "force_exit": force_exit}, 
                StrategyActionStatus.EXECUTED, db
            )
            
            db.commit()
            
            logger.info(f"Strategy squared off: {strategy.name} (ID: {strategy.id})")
            return response
            
        except Exception as e:
            logger.error(f"Failed to square off strategy: {str(e)}")
            db.rollback()
            raise ValidationException(
                message="Failed to square off strategy",
                details={"error": str(e)}
            )
    
    async def get_strategy_details(
        self,
        user_context: UserContext,
        strategy: Strategy,
        db: Session
    ) -> Dict[str, Any]:
        """
        Get comprehensive strategy details from trade_service
        """
        try:
            if not strategy.trade_service_strategy_id:
                raise ValidationException(
                    message="Strategy not synchronized with trade service"
                )
            
            # Get strategy details from trade_service
            response = await self._get_strategy_from_trade_service(
                user_context, strategy, db
            )
            
            # Update local strategy with latest data
            if "realized_pnl" in response:
                strategy.realized_pnl = response["realized_pnl"]
            if "unrealized_pnl" in response:
                strategy.unrealized_pnl = response["unrealized_pnl"]
            if "current_value" in response:
                strategy.current_value = response["current_value"]
            if "active_positions_count" in response:
                strategy.active_positions_count = response["active_positions_count"]
            if "total_orders_count" in response:
                strategy.total_orders_count = response["total_orders_count"]
            
            db.commit()
            
            return response
            
        except Exception as e:
            logger.error(f"Failed to get strategy details: {str(e)}")
            raise ValidationException(
                message="Failed to get strategy details",
                details={"error": str(e)}
            )
    
    async def sync_strategies(
        self,
        user_context: UserContext,
        trading_account: TradingAccount,
        db: Session
    ) -> Dict[str, Any]:
        """
        Sync all strategies for a trading account with trade_service
        """
        try:
            # Get strategies from trade_service
            trade_service_strategies = await self._get_all_strategies_from_trade_service(
                user_context, trading_account, db
            )
            
            sync_results = {
                "fetched_count": len(trade_service_strategies),
                "updated_count": 0,
                "new_count": 0,
                "deactivated_count": 0
            }
            
            # Update existing strategies and create new ones
            for ts_strategy in trade_service_strategies:
                strategy_id = ts_strategy.get("strategy_id")
                
                # Find existing strategy
                existing_strategy = db.query(Strategy).filter(
                    Strategy.trade_service_strategy_id == strategy_id,
                    Strategy.trading_account_id == trading_account.id
                ).first()
                
                if existing_strategy:
                    # Update existing strategy
                    existing_strategy.realized_pnl = ts_strategy.get("realized_pnl", 0)
                    existing_strategy.unrealized_pnl = ts_strategy.get("unrealized_pnl", 0)
                    existing_strategy.current_value = ts_strategy.get("current_value", 0)
                    existing_strategy.active_positions_count = ts_strategy.get("positions_count", 0)
                    existing_strategy.total_orders_count = ts_strategy.get("orders_count", 0)
                    sync_results["updated_count"] += 1
                else:
                    # Create new strategy from trade_service
                    new_strategy = Strategy(
                        name=ts_strategy.get("name", f"Strategy {strategy_id}"),
                        description=ts_strategy.get("description"),
                        strategy_type=StrategyType(ts_strategy.get("type", "MANUAL")),
                        trading_account_id=trading_account.id,
                        organization_id=trading_account.organization_id,
                        created_by_id=int(user_context.user_id),
                        trade_service_strategy_id=strategy_id,
                        status=StrategyStatus(ts_strategy.get("status", "active")),
                        realized_pnl=ts_strategy.get("realized_pnl", 0),
                        unrealized_pnl=ts_strategy.get("unrealized_pnl", 0),
                        current_value=ts_strategy.get("current_value", 0)
                    )
                    db.add(new_strategy)
                    sync_results["new_count"] += 1
            
            db.commit()
            
            logger.info(f"Strategy sync completed: {sync_results}")
            return sync_results
            
        except Exception as e:
            logger.error(f"Failed to sync strategies: {str(e)}")
            db.rollback()
            raise ValidationException(
                message="Failed to sync strategies",
                details={"error": str(e)}
            )
    
    # Private methods for trade_service integration
    
    async def _create_strategy_in_trade_service(
        self,
        user_context: UserContext,
        trading_account: TradingAccount,
        strategy: Strategy,
        db: Session
    ) -> Dict[str, Any]:
        """Create strategy in trade_service"""
        url = f"{self.trade_service_url}/api/strategies"
        
        headers = self._get_trade_service_headers(user_context, trading_account)
        
        payload = {
            "name": strategy.name,
            "description": strategy.description,
            "type": strategy.strategy_type.value,
            "parameters": strategy.parameters_dict,
            "risk_parameters": strategy.risk_parameters_dict,
            "account_id": trading_account.login_id,
            "broker": trading_account.broker
        }
        
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(url, json=payload, headers=headers)
            response.raise_for_status()
            return response.json()
    
    async def _update_strategy_in_trade_service(
        self,
        user_context: UserContext,
        strategy: Strategy,
        update_data: Dict[str, Any],
        db: Session
    ) -> Dict[str, Any]:
        """Update strategy in trade_service"""
        url = f"{self.trade_service_url}/api/strategies/{strategy.trade_service_strategy_id}"
        
        headers = self._get_trade_service_headers(user_context, strategy.trading_account)
        
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.put(url, json=update_data, headers=headers)
            response.raise_for_status()
            return response.json()
    
    async def _start_strategy_in_trade_service(
        self,
        user_context: UserContext,
        strategy: Strategy,
        db: Session
    ) -> Dict[str, Any]:
        """Start strategy in trade_service"""
        url = f"{self.trade_service_url}/api/strategies/{strategy.trade_service_strategy_id}/start"
        
        headers = self._get_trade_service_headers(user_context, strategy.trading_account)
        
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(url, headers=headers)
            response.raise_for_status()
            return response.json()
    
    async def _stop_strategy_in_trade_service(
        self,
        user_context: UserContext,
        strategy: Strategy,
        reason: Optional[str],
        db: Session
    ) -> Dict[str, Any]:
        """Stop strategy in trade_service"""
        url = f"{self.trade_service_url}/api/strategies/{strategy.trade_service_strategy_id}/stop"
        
        headers = self._get_trade_service_headers(user_context, strategy.trading_account)
        payload = {"reason": reason} if reason else {}
        
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(url, json=payload, headers=headers)
            response.raise_for_status()
            return response.json()
    
    async def _square_off_strategy_in_trade_service(
        self,
        user_context: UserContext,
        strategy: Strategy,
        reason: Optional[str],
        force_exit: bool,
        db: Session
    ) -> Dict[str, Any]:
        """Square off strategy in trade_service"""
        url = f"{self.trade_service_url}/api/strategies/{strategy.trade_service_strategy_id}/square-off"
        
        headers = self._get_trade_service_headers(user_context, strategy.trading_account)
        payload = {
            "reason": reason,
            "force_exit": force_exit
        }
        
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(url, json=payload, headers=headers)
            response.raise_for_status()
            return response.json()
    
    async def _get_strategy_from_trade_service(
        self,
        user_context: UserContext,
        strategy: Strategy,
        db: Session
    ) -> Dict[str, Any]:
        """Get strategy details from trade_service"""
        url = f"{self.trade_service_url}/api/strategies/{strategy.trade_service_strategy_id}"
        
        headers = self._get_trade_service_headers(user_context, strategy.trading_account)
        
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(url, headers=headers)
            response.raise_for_status()
            return response.json()
    
    async def _get_all_strategies_from_trade_service(
        self,
        user_context: UserContext,
        trading_account: TradingAccount,
        db: Session
    ) -> List[Dict[str, Any]]:
        """Get all strategies for trading account from trade_service"""
        url = f"{self.trade_service_url}/api/strategies"
        
        headers = self._get_trade_service_headers(user_context, trading_account)
        params = {
            "account_id": trading_account.login_id,
            "broker": trading_account.broker
        }
        
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(url, params=params, headers=headers)
            response.raise_for_status()
            data = response.json()
            return data.get("strategies", [])
    
    def _get_trade_service_headers(
        self,
        user_context: UserContext,
        trading_account: TradingAccount
    ) -> Dict[str, str]:
        """Get headers for trade_service requests"""
        # Decrypt API key (implement proper decryption)
        api_key = "dummy_api_key"  # This should be decrypted from organization.api_key_hash
        
        return {
            "Authorization": f"Bearer {user_context.user_id}",
            "X-API-Key": api_key,
            "X-Account-ID": trading_account.login_id,
            "X-Broker": trading_account.broker,
            "Content-Type": "application/json"
        }
    
    def _log_strategy_action(
        self,
        user_context: UserContext,
        strategy: Strategy,
        action_type: StrategyActionType,
        action_data: Dict[str, Any],
        status: StrategyActionStatus,
        db: Session,
        before_state: Optional[Dict[str, Any]] = None,
        after_state: Optional[Dict[str, Any]] = None
    ):
        """Log strategy action for audit trail"""
        try:
            action_log = StrategyActionLog(
                action_type=action_type,
                action_status=status,
                user_id=int(user_context.user_id),
                strategy_id=strategy.id,
                trading_account_id=strategy.trading_account_id,
                organization_id=strategy.organization_id,
                action_data=json.dumps(action_data) if action_data else None,
                before_state=json.dumps(before_state) if before_state else None,
                after_state=json.dumps(after_state) if after_state else None
            )
            
            db.add(action_log)
            
        except Exception as e:
            logger.error(f"Failed to log strategy action: {str(e)}")

# Global instance
strategy_service: Optional[StrategyService] = None

def get_strategy_service() -> StrategyService:
    """Get global strategy service instance"""
    global strategy_service
    if strategy_service is None:
        raise RuntimeError("Strategy service not initialized. Call init_strategy_service() first.")
    return strategy_service

def init_strategy_service(trade_service_url: str):
    """Initialize global strategy service"""
    global strategy_service
    strategy_service = StrategyService(trade_service_url)
    logger.info(f"Strategy service initialized: {trade_service_url}")