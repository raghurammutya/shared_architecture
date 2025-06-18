# shared_architecture/setup/service_integrations.py

"""
Service integration setup for inter-service communication and alerting
"""

from typing import Dict, Any, Optional
from ..clients.service_client import init_service_clients
from ..events.alert_system import init_alert_system, start_alert_processing
from ..resilience.failure_handlers import get_failure_handler
from ..utils.enhanced_logging import get_logger

logger = get_logger(__name__)

class ServiceIntegrationManager:
    """Manage all service integrations and dependencies"""
    
    def __init__(self):
        self.initialized = False
        self.services_config = {}
        self.alert_config = {}
    
    async def initialize(self, config: Dict[str, Any]):
        """Initialize all service integrations"""
        
        if self.initialized:
            logger.warning("Service integrations already initialized")
            return
        
        self.services_config = config.get("services", {})
        self.alert_config = config.get("alerting", {})
        
        # Initialize service clients
        await self._init_service_clients()
        
        # Initialize alerting system
        await self._init_alerting_system()
        
        # Start alert processing
        await start_alert_processing()
        
        self.initialized = True
        logger.info("✅ Service integrations initialized successfully")
    
    async def _init_service_clients(self):
        """Initialize inter-service communication clients"""
        try:
            user_service_url = self.services_config.get("user_service", {}).get("url", "http://localhost:8002")
            trade_service_url = self.services_config.get("trade_service", {}).get("url", "http://localhost:8004")
            service_secret = self.services_config.get("service_secret", "default-service-secret-change-in-production")
            
            init_service_clients(
                user_service_url=user_service_url,
                trade_service_url=trade_service_url,
                service_secret=service_secret
            )
            
            logger.info("✅ Service clients initialized")
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize service clients: {e}")
            raise
    
    async def _init_alerting_system(self):
        """Initialize comprehensive alerting system"""
        try:
            # Email configuration
            email_config = self.alert_config.get("email")
            if email_config and email_config.get("enabled", False):
                email_settings = {
                    "smtp_server": email_config.get("smtp_server", "localhost"),
                    "smtp_port": email_config.get("smtp_port", 587),
                    "username": email_config.get("username"),
                    "password": email_config.get("password"),
                    "from_email": email_config.get("from_email", "noreply@stocksblitz.com")
                }
            else:
                email_settings = None
            
            # Slack configuration  
            slack_config = self.alert_config.get("slack")
            slack_webhook = None
            if slack_config and slack_config.get("enabled", False):
                slack_webhook = slack_config.get("webhook_url")
            
            # SMS configuration
            sms_config = self.alert_config.get("sms")
            if sms_config and sms_config.get("enabled", False):
                sms_settings = {
                    "provider": sms_config.get("provider", "twilio"),
                    "account_sid": sms_config.get("account_sid"),
                    "auth_token": sms_config.get("auth_token"),
                    "from_number": sms_config.get("from_number")
                }
            else:
                sms_settings = None
            
            # WebSocket manager (would be initialized by the main app)
            websocket_manager = None  # This would be passed from the main application
            
            init_alert_system(
                email_config=email_settings,
                slack_webhook=slack_webhook,
                sms_config=sms_settings,
                websocket_manager=websocket_manager
            )
            
            logger.info("✅ Alerting system initialized")
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize alerting system: {e}")
            # Continue without alerting rather than failing completely
    
    def get_integration_status(self) -> Dict[str, Any]:
        """Get status of all integrations"""
        
        status = {
            "initialized": self.initialized,
            "services": {},
            "alerting": {},
            "failure_handling": {}
        }
        
        # Check service client status
        try:
            from ..clients.service_client import get_user_service_client, get_trade_service_client
            
            user_client = get_user_service_client()
            trade_client = get_trade_service_client()
            
            status["services"] = {
                "user_service_client": {
                    "initialized": user_client is not None,
                    "base_url": getattr(user_client, 'base_url', None),
                    "circuit_breaker_state": getattr(user_client.circuit_breaker, 'state', None)
                },
                "trade_service_client": {
                    "initialized": trade_client is not None,
                    "base_url": getattr(trade_client, 'base_url', None),
                    "circuit_breaker_state": getattr(trade_client.circuit_breaker, 'state', None)
                }
            }
            
        except Exception as e:
            status["services"]["error"] = str(e)
        
        # Check alerting system status
        try:
            from ..events.alert_system import get_alert_manager
            
            alert_manager = get_alert_manager()
            alert_stats = alert_manager.get_statistics()
            
            status["alerting"] = {
                "initialized": True,
                "stats": alert_stats,
                "channels": alert_stats.get("channels_registered", []),
                "queue_size": alert_stats.get("queue_size", 0)
            }
            
        except Exception as e:
            status["alerting"] = {
                "initialized": False,
                "error": str(e)
            }
        
        # Check failure handler status
        try:
            failure_handler = get_failure_handler()
            
            status["failure_handling"] = {
                "initialized": failure_handler is not None,
                "cache_size": len(failure_handler.cache_manager.cache),
                "retry_queue_size": len(failure_handler.retry_queue.queue)
            }
            
        except Exception as e:
            status["failure_handling"] = {
                "initialized": False,
                "error": str(e)
            }
        
        return status

# Global integration manager
_integration_manager: Optional[ServiceIntegrationManager] = None

def get_integration_manager() -> ServiceIntegrationManager:
    """Get global integration manager"""
    global _integration_manager
    if _integration_manager is None:
        _integration_manager = ServiceIntegrationManager()
    return _integration_manager

async def setup_service_integrations(config: Dict[str, Any]):
    """Setup all service integrations"""
    manager = get_integration_manager()
    await manager.initialize(config)

def get_integration_status() -> Dict[str, Any]:
    """Get integration status"""
    manager = get_integration_manager()
    return manager.get_integration_status()

# Example configuration for services
EXAMPLE_CONFIG = {
    "services": {
        "user_service": {
            "url": "http://user-service:8002"
        },
        "trade_service": {
            "url": "http://trade-service:8004"
        },
        "service_secret": "your-service-secret-here"
    },
    "alerting": {
        "email": {
            "enabled": True,
            "smtp_server": "smtp.gmail.com",
            "smtp_port": 587,
            "username": "alerts@stocksblitz.com",
            "password": "app-password",
            "from_email": "noreply@stocksblitz.com"
        },
        "slack": {
            "enabled": True,
            "webhook_url": "https://hooks.slack.com/services/YOUR/SLACK/WEBHOOK"
        },
        "sms": {
            "enabled": False,
            "provider": "twilio",
            "account_sid": "your-twilio-sid",
            "auth_token": "your-twilio-token",
            "from_number": "+1234567890"
        }
    }
}