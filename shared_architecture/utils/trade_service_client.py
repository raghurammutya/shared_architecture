# shared_architecture/utils/trade_service_client.py

import httpx
import hashlib
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from datetime import datetime

from ..utils.enhanced_logging import get_logger
from ..exceptions.trade_exceptions import AuthenticationException, ValidationException
from ..db.models.organization import Organization
from ..db.models.trading_account import TradingAccount
from ..auth import UserContext

logger = get_logger(__name__)

class TradeServiceClient:
    """
    Client for integrating with trade_service API
    Handles fetching trading accounts and validation
    """
    
    def __init__(self, trade_service_url: str):
        self.trade_service_url = trade_service_url.rstrip('/')
        self.timeout = 30.0
    
    def _hash_api_key(self, api_key: str) -> str:
        """Hash API key for secure storage"""
        return hashlib.sha256(api_key.encode()).hexdigest()
    
    def _mask_api_key(self, api_key: str) -> str:
        """Create masked version of API key for display"""
        if len(api_key) <= 12:
            return api_key[:4] + "*" * 4 + api_key[-4:]
        return api_key[:8] + "*" * 8 + api_key[-4:]
    
    async def fetch_trading_accounts(self, api_key: str, user_context: UserContext) -> Dict[str, Any]:
        """
        Fetch trading accounts from trade_service using API key
        
        Args:
            api_key: The organization's API key
            user_context: Current user context for authentication
            
        Returns:
            Dict containing the trade_service response
        """
        try:
            url = f"{self.trade_service_url}/api/trading-accounts"
            
            headers = {
                "Authorization": f"Bearer {user_context.user_id}",  # Use JWT for user auth
                "X-API-Key": api_key,  # Organization API key
                "Content-Type": "application/json"
            }
            
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(url, headers=headers)
                response.raise_for_status()
                
                data = response.json()
                
                if not data.get("status", False):
                    raise ValidationException(
                        message="Trade service returned error",
                        details={"response": data.get("message", "Unknown error")}
                    )
                
                logger.info(f"Successfully fetched {len(data.get('result', []))} trading accounts from trade_service")
                return data
                
        except httpx.HTTPStatusError as e:
            logger.error(f"Trade service HTTP error: {e.response.status_code} - {e.response.text}")
            raise ValidationException(
                message="Failed to fetch trading accounts from trade service",
                details={"status_code": e.response.status_code, "error": e.response.text}
            )
        except Exception as e:
            logger.error(f"Trade service client error: {str(e)}")
            raise ValidationException(
                message="Trade service communication failed",
                details={"error": str(e)}
            )
    
    async def validate_api_key(self, api_key: str, user_context: UserContext) -> bool:
        """
        Validate API key with trade_service
        
        Args:
            api_key: The API key to validate
            user_context: Current user context
            
        Returns:
            bool: True if API key is valid
        """
        try:
            # Try to fetch accounts - if successful, API key is valid
            response = await self.fetch_trading_accounts(api_key, user_context)
            return response.get("status", False)
        except Exception as e:
            logger.warning(f"API key validation failed: {str(e)}")
            return False
    
    def import_trading_accounts(
        self, 
        trade_service_response: Dict[str, Any], 
        organization: Organization,
        selected_account_ids: List[str],
        db: Session
    ) -> List[TradingAccount]:
        """
        Import selected trading accounts into the database
        
        Args:
            trade_service_response: Response from trade_service
            organization: The organization to import accounts to
            selected_account_ids: List of loginId values to import
            db: Database session
            
        Returns:
            List of created TradingAccount objects
        """
        try:
            accounts_data = trade_service_response.get("result", [])
            imported_accounts = []
            
            for account_data in accounts_data:
                login_id = account_data.get("loginId")
                
                # Skip if not selected
                if login_id not in selected_account_ids:
                    continue
                
                # Check if account already exists
                existing_account = db.query(TradingAccount).filter(
                    TradingAccount.login_id == login_id,
                    TradingAccount.broker == account_data.get("broker"),
                    TradingAccount.organization_id == organization.id
                ).first()
                
                if existing_account:
                    logger.info(f"Trading account already exists: {login_id}")
                    continue
                
                # Create new trading account
                trading_account = TradingAccount(
                    login_id=login_id,
                    pseudo_acc_name=account_data.get("pseudoAccName", ""),
                    broker=account_data.get("broker", ""),
                    platform=account_data.get("platform", ""),
                    system_id=account_data.get("systemId", 0),
                    system_id_of_pseudo_acc=account_data.get("systemIdOfPseudoAcc", 0),
                    license_expiry_date=account_data.get("licenseExpiryDate"),
                    license_days_left=account_data.get("licenseDaysLeft", 0),
                    is_live=account_data.get("live", False),
                    organization_id=organization.id,
                    is_active=True
                )
                
                db.add(trading_account)
                imported_accounts.append(trading_account)
                
                logger.info(f"Imported trading account: {login_id} ({account_data.get('broker')})")
            
            db.commit()
            
            logger.info(f"Successfully imported {len(imported_accounts)} trading accounts for organization {organization.name}")
            return imported_accounts
            
        except Exception as e:
            logger.error(f"Failed to import trading accounts: {str(e)}")
            db.rollback()
            raise ValidationException(
                message="Failed to import trading accounts",
                details={"error": str(e)}
            )
    
    def validate_user_access(
        self, 
        user_context: UserContext, 
        trading_account: TradingAccount,
        required_permission: Optional[str] = None
    ) -> bool:
        """
        Validate if user has access to trading account data
        
        Args:
            user_context: Current user context
            trading_account: The trading account to check access for
            required_permission: Specific permission required (optional)
            
        Returns:
            bool: True if user has access
        """
        try:
            # Organization owners have full access
            if trading_account.organization.owner_id == int(user_context.user_id):
                return True
            
            # Backup owners have full access
            if trading_account.organization.backup_owner_id == int(user_context.user_id):
                return True
            
            # Check if user is assigned to this trading account
            if trading_account.assigned_user_id == int(user_context.user_id):
                return True
            
            # Check explicit permissions
            if required_permission:
                for permission in trading_account.permissions:
                    if (permission.user_id == int(user_context.user_id) and 
                        permission.is_valid and
                        (permission.permission_type.value == required_permission or 
                         permission.permission_type.value == "full_read")):
                        return True
            else:
                # Any valid permission grants access
                for permission in trading_account.permissions:
                    if permission.user_id == int(user_context.user_id) and permission.is_valid:
                        return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error validating user access: {str(e)}")
            return False
    
    async def sync_trading_accounts(
        self, 
        organization: Organization, 
        user_context: UserContext,
        db: Session
    ) -> Dict[str, Any]:
        """
        Sync trading accounts from trade_service for an organization
        
        Args:
            organization: Organization to sync accounts for
            user_context: Current user context
            db: Database session
            
        Returns:
            Dict with sync results
        """
        try:
            # Decrypt API key (in real implementation, you'd decrypt the hashed key)
            # For now, assume we store the actual key temporarily during creation
            api_key = "dummy_key"  # This would be retrieved/decrypted from secure storage
            
            # Fetch current accounts from trade_service
            response = await self.fetch_trading_accounts(api_key, user_context)
            accounts_data = response.get("result", [])
            
            sync_results = {
                "fetched_count": len(accounts_data),
                "updated_count": 0,
                "new_count": 0,
                "deactivated_count": 0
            }
            
            # Get current login_ids from trade_service
            current_login_ids = {acc.get("loginId") for acc in accounts_data}
            
            # Update existing accounts and create new ones
            for account_data in accounts_data:
                login_id = account_data.get("loginId")
                broker = account_data.get("broker")
                
                existing_account = db.query(TradingAccount).filter(
                    TradingAccount.login_id == login_id,
                    TradingAccount.broker == broker,
                    TradingAccount.organization_id == organization.id
                ).first()
                
                if existing_account:
                    # Update existing account
                    existing_account.license_expiry_date = account_data.get("licenseExpiryDate")
                    existing_account.license_days_left = account_data.get("licenseDaysLeft", 0)
                    existing_account.is_live = account_data.get("live", False)
                    existing_account.last_synced_at = datetime.utcnow()
                    sync_results["updated_count"] += 1
                else:
                    # Create new account (auto-import)
                    new_account = TradingAccount(
                        login_id=login_id,
                        pseudo_acc_name=account_data.get("pseudoAccName", ""),
                        broker=broker,
                        platform=account_data.get("platform", ""),
                        system_id=account_data.get("systemId", 0),
                        system_id_of_pseudo_acc=account_data.get("systemIdOfPseudoAcc", 0),
                        license_expiry_date=account_data.get("licenseExpiryDate"),
                        license_days_left=account_data.get("licenseDaysLeft", 0),
                        is_live=account_data.get("live", False),
                        organization_id=organization.id,
                        is_active=True
                    )
                    db.add(new_account)
                    sync_results["new_count"] += 1
            
            # Deactivate accounts that no longer exist in trade_service
            org_accounts = db.query(TradingAccount).filter(
                TradingAccount.organization_id == organization.id,
                TradingAccount.is_active == True
            ).all()
            
            for account in org_accounts:
                if account.login_id not in current_login_ids:
                    account.is_active = False
                    sync_results["deactivated_count"] += 1
            
            db.commit()
            
            logger.info(f"Sync completed for organization {organization.name}: {sync_results}")
            return sync_results
            
        except Exception as e:
            logger.error(f"Failed to sync trading accounts: {str(e)}")
            db.rollback()
            raise ValidationException(
                message="Failed to sync trading accounts",
                details={"error": str(e)}
            )

# Global instance
trade_service_client: Optional[TradeServiceClient] = None

def get_trade_service_client() -> TradeServiceClient:
    """Get global trade service client instance"""
    global trade_service_client
    if trade_service_client is None:
        raise RuntimeError("Trade service client not initialized. Call init_trade_service_client() first.")
    return trade_service_client

def init_trade_service_client(trade_service_url: str):
    """Initialize global trade service client"""
    global trade_service_client
    trade_service_client = TradeServiceClient(trade_service_url)
    logger.info(f"Trade service client initialized: {trade_service_url}")