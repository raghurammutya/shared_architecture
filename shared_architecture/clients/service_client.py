# shared_architecture/clients/service_client.py

import httpx
import asyncio
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
import jwt
from contextlib import asynccontextmanager

from ..auth import UserContext
from ..utils.enhanced_logging import get_logger
from ..exceptions.base_exceptions import ServiceUnavailableError, UnauthorizedServiceError

logger = get_logger(__name__)

class ServiceContext:
    """Context for service-to-service communication"""
    def __init__(self, service_name: str, scopes: List[str] = None):
        self.service_name = service_name
        self.scopes = scopes or []
        self.created_at = datetime.utcnow()

class CircuitBreaker:
    """Circuit breaker pattern for service resilience"""
    
    def __init__(self, failure_threshold: int = 5, recovery_timeout: int = 30):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failure_count = 0
        self.last_failure_time = None
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN
    
    def can_execute(self) -> bool:
        if self.state == "CLOSED":
            return True
        
        if self.state == "OPEN":
            if (datetime.utcnow() - self.last_failure_time).seconds >= self.recovery_timeout:
                self.state = "HALF_OPEN"
                return True
            return False
        
        # HALF_OPEN state
        return True
    
    def record_success(self):
        self.failure_count = 0
        self.state = "CLOSED"
        logger.debug("Circuit breaker reset to CLOSED state")
    
    def record_failure(self):
        self.failure_count += 1
        self.last_failure_time = datetime.utcnow()
        
        if self.failure_count >= self.failure_threshold:
            self.state = "OPEN"
            logger.warning(f"Circuit breaker opened after {self.failure_count} failures")

class ServiceAuthenticator:
    """Handle service-to-service authentication"""
    
    def __init__(self, service_secret: str):
        self.service_secret = service_secret
    
    def create_service_token(self, service_name: str) -> str:
        """Create JWT token for service-to-service calls"""
        payload = {
            "service": service_name,
            "iss": "stocksblitz-platform",
            "aud": ["user_service", "trade_service"],
            "exp": datetime.utcnow() + timedelta(hours=1),
            "scope": ["inter_service_communication"],
            "iat": datetime.utcnow()
        }
        return jwt.encode(payload, self.service_secret, algorithm="HS256")
    
    def validate_service_token(self, token: str) -> ServiceContext:
        """Validate incoming service token"""
        try:
            payload = jwt.decode(token, self.service_secret, algorithms=["HS256"])
            return ServiceContext(
                service_name=payload["service"],
                scopes=payload.get("scope", [])
            )
        except jwt.InvalidTokenError as e:
            raise UnauthorizedServiceError(f"Invalid service token: {e}")

class InterServiceClient:
    """Base client for inter-service communication"""
    
    def __init__(self, service_name: str, base_url: str, service_secret: str, timeout: int = 30):
        self.service_name = service_name
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout
        self.authenticator = ServiceAuthenticator(service_secret)
        self.circuit_breaker = CircuitBreaker()
        self._client = None
    
    @asynccontextmanager
    async def get_client(self):
        """Get HTTP client with proper configuration"""
        if self._client is None:
            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(self.timeout),
                limits=httpx.Limits(max_keepalive_connections=20, max_connections=100)
            )
        
        try:
            yield self._client
        finally:
            # Keep client alive for connection pooling
            pass
    
    async def close(self):
        """Close the HTTP client"""
        if self._client:
            await self._client.aclose()
            self._client = None
    
    def _get_headers(self) -> Dict[str, str]:
        """Get headers for service-to-service calls"""
        service_token = self.authenticator.create_service_token(self.service_name)
        return {
            "Authorization": f"Service-Token {service_token}",
            "Content-Type": "application/json",
            "X-Service-Name": self.service_name,
            "X-Request-ID": f"{self.service_name}-{datetime.utcnow().timestamp()}"
        }
    
    async def _make_request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        """Make HTTP request with circuit breaker and retry logic"""
        
        if not self.circuit_breaker.can_execute():
            raise ServiceUnavailableError(f"Circuit breaker OPEN for {self.base_url}")
        
        url = f"{self.base_url}{endpoint}"
        headers = self._get_headers()
        
        if 'headers' in kwargs:
            headers.update(kwargs.pop('headers'))
        
        try:
            async with self.get_client() as client:
                response = await client.request(
                    method=method,
                    url=url,
                    headers=headers,
                    **kwargs
                )
                
                if response.status_code >= 400:
                    error_detail = response.text
                    if response.status_code >= 500:
                        self.circuit_breaker.record_failure()
                        raise ServiceUnavailableError(
                            f"Service error {response.status_code}: {error_detail}"
                        )
                    else:
                        raise httpx.HTTPStatusError(
                            f"HTTP {response.status_code}: {error_detail}",
                            request=response.request,
                            response=response
                        )
                
                self.circuit_breaker.record_success()
                
                if response.headers.get("content-type", "").startswith("application/json"):
                    return response.json()
                else:
                    return {"data": response.text}
                
        except (httpx.TimeoutException, httpx.ConnectError) as e:
            self.circuit_breaker.record_failure()
            logger.error(f"Service communication error with {url}: {e}")
            
            # Send system health alert
            await self._send_service_alert(f"Communication failed: {e}")
            
            raise ServiceUnavailableError(f"Failed to communicate with {self.base_url}: {e}")
    
    async def _send_service_alert(self, error_message: str):
        """Send alert for service communication issues"""
        try:
            from ..events.alert_system import get_alert_manager, AlertSeverity
            
            alert_manager = get_alert_manager()
            await alert_manager.create_system_health_alert(
                service_name=self.service_name,
                component="inter_service_communication",
                error_message=error_message,
                severity=AlertSeverity.ERROR
            )
        except Exception as e:
            logger.warning(f"Failed to send service alert: {e}")
        except Exception as e:
            logger.error(f"Unexpected error calling {url}: {e}")
            raise
    
    async def get(self, endpoint: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """Make GET request"""
        return await self._make_request("GET", endpoint, params=params)
    
    async def post(self, endpoint: str, data: Dict[str, Any] = None) -> Dict[str, Any]:
        """Make POST request"""
        return await self._make_request("POST", endpoint, json=data)
    
    async def put(self, endpoint: str, data: Dict[str, Any] = None) -> Dict[str, Any]:
        """Make PUT request"""
        return await self._make_request("PUT", endpoint, json=data)
    
    async def delete(self, endpoint: str) -> Dict[str, Any]:
        """Make DELETE request"""
        return await self._make_request("DELETE", endpoint)

class UserServiceClient(InterServiceClient):
    """Client for communicating with user service"""
    
    def __init__(self, base_url: str, service_secret: str):
        super().__init__("trade_service", base_url, service_secret)
    
    async def validate_user_permissions(self, user_id: int, action: str, trading_account_id: int) -> Dict[str, Any]:
        """Validate user permissions for trading action"""
        try:
            return await self.get(
                f"/api/permissions/validate",
                params={
                    "user_id": user_id,
                    "action": action,
                    "trading_account_id": trading_account_id
                }
            )
        except ServiceUnavailableError:
            logger.warning(f"User service unavailable, using emergency permissions for user {user_id}")
            return {
                "allowed": True,
                "emergency_mode": True,
                "restrictions": {
                    "daily_limit": 10000.00,
                    "single_trade_limit": 2000.00
                }
            }
    
    async def validate_trading_limits(self, user_id: int, trading_account_id: int, action_data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate trading action against limits"""
        return await self.post(
            f"/api/trading-limits/validate",
            data=action_data,
            params={"trading_account_id": trading_account_id}
        )
    
    async def update_usage_after_trade(self, user_id: int, trading_account_id: int, trade_data: Dict[str, Any]) -> Dict[str, Any]:
        """Update usage counters after successful trade"""
        return await self.post(
            f"/api/trading-limits/update-usage",
            data={
                "user_id": user_id,
                "trading_account_id": trading_account_id,
                "action_type": trade_data.get("action_type", "place_order"),
                "trade_value": trade_data.get("trade_value"),
                "instrument": trade_data.get("instrument"),
                "quantity": trade_data.get("quantity")
            }
        )
    
    async def get_user_info(self, user_id: int) -> Dict[str, Any]:
        """Get basic user information"""
        return await self.get(f"/users/{user_id}")
    
    async def get_organization_api_key(self, organization_id: int) -> Dict[str, Any]:
        """Get API key for organization"""
        return await self.get(f"/api/organizations/{organization_id}/api-key")

class TradeServiceClient(InterServiceClient):
    """Client for communicating with trade service"""
    
    def __init__(self, base_url: str, service_secret: str):
        super().__init__("user_service", base_url, service_secret)
    
    async def get_user_positions(self, user_id: int, trading_account_id: int) -> Dict[str, Any]:
        """Get current positions for user"""
        try:
            return await self.get(
                f"/api/positions",
                params={
                    "user_id": user_id,
                    "trading_account_id": trading_account_id
                }
            )
        except ServiceUnavailableError:
            logger.warning(f"Trade service unavailable, returning cached positions for user {user_id}")
            # Return cached or empty positions
            return {
                "positions": [],
                "cached": True,
                "warning": "Trade service unavailable - using cached data"
            }
    
    async def get_daily_order_count(self, user_id: int, trading_account_id: int, date: str = None) -> Dict[str, Any]:
        """Get order count for specific date"""
        params = {
            "user_id": user_id,
            "trading_account_id": trading_account_id
        }
        if date:
            params["date"] = date
        
        return await self.get("/api/orders/count", params=params)
    
    async def get_daily_trade_value(self, user_id: int, trading_account_id: int, date: str = None) -> Dict[str, Any]:
        """Get total trade value for specific date"""
        params = {
            "user_id": user_id,
            "trading_account_id": trading_account_id
        }
        if date:
            params["date"] = date
        
        return await self.get("/api/trades/daily-value", params=params)
    
    async def get_trading_account_summary(self, trading_account_id: int) -> Dict[str, Any]:
        """Get summary of trading account"""
        return await self.get(f"/api/trading-accounts/{trading_account_id}/summary")

# Global service client instances
_user_service_client: Optional[UserServiceClient] = None
_trade_service_client: Optional[TradeServiceClient] = None

def init_service_clients(user_service_url: str, trade_service_url: str, service_secret: str):
    """Initialize global service clients"""
    global _user_service_client, _trade_service_client
    
    _user_service_client = UserServiceClient(user_service_url, service_secret)
    _trade_service_client = TradeServiceClient(trade_service_url, service_secret)
    
    logger.info("Service clients initialized")

def get_user_service_client() -> UserServiceClient:
    """Get user service client instance"""
    if _user_service_client is None:
        raise RuntimeError("User service client not initialized. Call init_service_clients() first.")
    return _user_service_client

def get_trade_service_client() -> TradeServiceClient:
    """Get trade service client instance"""
    if _trade_service_client is None:
        raise RuntimeError("Trade service client not initialized. Call init_service_clients() first.")
    return _trade_service_client

async def cleanup_service_clients():
    """Cleanup service clients"""
    global _user_service_client, _trade_service_client
    
    if _user_service_client:
        await _user_service_client.close()
        _user_service_client = None
    
    if _trade_service_client:
        await _trade_service_client.close()
        _trade_service_client = None
    
    logger.info("Service clients cleaned up")