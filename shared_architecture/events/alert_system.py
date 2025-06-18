# shared_architecture/events/alert_system.py

import asyncio
import json
from typing import Dict, Any, List, Optional, Callable
from datetime import datetime, timedelta
from enum import Enum
from dataclasses import dataclass, asdict
from sqlalchemy.orm import Session

from ..utils.enhanced_logging import get_logger
from ..exceptions.base_exceptions import AlertDeliveryError

logger = get_logger(__name__)

class AlertSeverity(Enum):
    """Alert severity levels"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"

class AlertCategory(Enum):
    """Alert categories"""
    TRADING_LIMIT = "trading_limit"
    TRADE_EXECUTION = "trade_execution"
    SYSTEM_HEALTH = "system_health"
    SECURITY = "security"
    PERFORMANCE = "performance"
    DATA_QUALITY = "data_quality"

class AlertStatus(Enum):
    """Alert processing status"""
    PENDING = "pending"
    PROCESSING = "processing"
    DELIVERED = "delivered"
    FAILED = "failed"
    ACKNOWLEDGED = "acknowledged"

@dataclass
class Alert:
    """Base alert structure"""
    alert_id: str
    alert_type: str
    category: AlertCategory
    severity: AlertSeverity
    title: str
    message: str
    source_service: str
    timestamp: datetime
    
    # Context data
    user_id: Optional[int] = None
    organization_id: Optional[int] = None
    trading_account_id: Optional[int] = None
    
    # Alert-specific data
    data: Dict[str, Any] = None
    
    # Delivery settings
    delivery_channels: List[str] = None
    escalation_rules: Dict[str, Any] = None
    
    # Status tracking
    status: AlertStatus = AlertStatus.PENDING
    retry_count: int = 0
    last_attempt: Optional[datetime] = None
    acknowledged_by: Optional[int] = None
    acknowledged_at: Optional[datetime] = None
    
    def __post_init__(self):
        if self.data is None:
            self.data = {}
        if self.delivery_channels is None:
            self.delivery_channels = []
        if self.escalation_rules is None:
            self.escalation_rules = {}

class AlertChannel:
    """Base class for alert delivery channels"""
    
    def __init__(self, name: str):
        self.name = name
    
    async def deliver(self, alert: Alert) -> bool:
        """Deliver alert through this channel"""
        raise NotImplementedError

class EmailAlertChannel(AlertChannel):
    """Email alert delivery"""
    
    def __init__(self, smtp_config: Dict[str, Any]):
        super().__init__("email")
        self.smtp_config = smtp_config
    
    async def deliver(self, alert: Alert) -> bool:
        """Send email alert"""
        try:
            # Email delivery logic would go here
            # For now, simulate delivery
            logger.info(f"📧 Email alert sent: {alert.title}")
            await asyncio.sleep(0.1)  # Simulate network delay
            return True
        except Exception as e:
            logger.error(f"Failed to send email alert: {e}")
            return False

class SlackAlertChannel(AlertChannel):
    """Slack alert delivery"""
    
    def __init__(self, webhook_url: str):
        super().__init__("slack")
        self.webhook_url = webhook_url
    
    async def deliver(self, alert: Alert) -> bool:
        """Send Slack alert"""
        try:
            # Slack delivery logic would go here
            logger.info(f"💬 Slack alert sent: {alert.title}")
            await asyncio.sleep(0.1)
            return True
        except Exception as e:
            logger.error(f"Failed to send Slack alert: {e}")
            return False

class WebSocketAlertChannel(AlertChannel):
    """WebSocket push notification"""
    
    def __init__(self, websocket_manager):
        super().__init__("websocket")
        self.websocket_manager = websocket_manager
    
    async def deliver(self, alert: Alert) -> bool:
        """Send WebSocket alert"""
        try:
            if alert.user_id:
                await self.websocket_manager.send_to_user(
                    alert.user_id,
                    {
                        "type": "alert",
                        "severity": alert.severity.value,
                        "title": alert.title,
                        "message": alert.message,
                        "timestamp": alert.timestamp.isoformat()
                    }
                )
            logger.info(f"🔌 WebSocket alert sent: {alert.title}")
            return True
        except Exception as e:
            logger.error(f"Failed to send WebSocket alert: {e}")
            return False

class SMSAlertChannel(AlertChannel):
    """SMS alert delivery"""
    
    def __init__(self, sms_config: Dict[str, Any]):
        super().__init__("sms")
        self.sms_config = sms_config
    
    async def deliver(self, alert: Alert) -> bool:
        """Send SMS alert"""
        try:
            # SMS delivery logic would go here
            logger.info(f"📱 SMS alert sent: {alert.title}")
            await asyncio.sleep(0.1)
            return True
        except Exception as e:
            logger.error(f"Failed to send SMS alert: {e}")
            return False

class AlertRouter:
    """Route alerts to appropriate channels based on rules"""
    
    def __init__(self):
        self.routing_rules = {
            # Trading limit alerts
            (AlertCategory.TRADING_LIMIT, AlertSeverity.WARNING): ["websocket", "email"],
            (AlertCategory.TRADING_LIMIT, AlertSeverity.ERROR): ["websocket", "email", "slack"],
            (AlertCategory.TRADING_LIMIT, AlertSeverity.CRITICAL): ["websocket", "email", "slack", "sms"],
            
            # Trade execution alerts
            (AlertCategory.TRADE_EXECUTION, AlertSeverity.WARNING): ["websocket"],
            (AlertCategory.TRADE_EXECUTION, AlertSeverity.ERROR): ["websocket", "email"],
            (AlertCategory.TRADE_EXECUTION, AlertSeverity.CRITICAL): ["websocket", "email", "slack"],
            
            # System health alerts
            (AlertCategory.SYSTEM_HEALTH, AlertSeverity.WARNING): ["slack"],
            (AlertCategory.SYSTEM_HEALTH, AlertSeverity.ERROR): ["slack", "email"],
            (AlertCategory.SYSTEM_HEALTH, AlertSeverity.CRITICAL): ["slack", "email", "sms"],
            
            # Security alerts
            (AlertCategory.SECURITY, AlertSeverity.WARNING): ["email", "slack"],
            (AlertCategory.SECURITY, AlertSeverity.ERROR): ["email", "slack"],
            (AlertCategory.SECURITY, AlertSeverity.CRITICAL): ["email", "slack", "sms"],
        }
    
    def get_delivery_channels(self, alert: Alert) -> List[str]:
        """Get delivery channels for alert"""
        if alert.delivery_channels:
            return alert.delivery_channels
        
        key = (alert.category, alert.severity)
        return self.routing_rules.get(key, ["email"])

class AlertManager:
    """Central alert management system"""
    
    def __init__(self):
        self.channels: Dict[str, AlertChannel] = {}
        self.router = AlertRouter()
        self.alert_queue = asyncio.Queue()
        self.is_processing = False
        self.alert_handlers: Dict[str, Callable] = {}
        
        # Alert statistics
        self.stats = {
            "total_alerts": 0,
            "delivered_alerts": 0,
            "failed_alerts": 0,
            "retry_attempts": 0
        }
    
    def register_channel(self, channel: AlertChannel):
        """Register alert delivery channel"""
        self.channels[channel.name] = channel
        logger.info(f"Registered alert channel: {channel.name}")
    
    def register_handler(self, alert_type: str, handler: Callable):
        """Register custom alert handler"""
        self.alert_handlers[alert_type] = handler
        logger.info(f"Registered alert handler for: {alert_type}")
    
    async def create_alert(
        self,
        alert_type: str,
        category: AlertCategory,
        severity: AlertSeverity,
        title: str,
        message: str,
        source_service: str,
        **kwargs
    ) -> Alert:
        """Create and queue alert for delivery"""
        
        alert = Alert(
            alert_id=f"{source_service}-{datetime.utcnow().timestamp()}",
            alert_type=alert_type,
            category=category,
            severity=severity,
            title=title,
            message=message,
            source_service=source_service,
            timestamp=datetime.utcnow(),
            **kwargs
        )
        
        # Get delivery channels from router
        alert.delivery_channels = self.router.get_delivery_channels(alert)
        
        # Queue for processing
        await self.alert_queue.put(alert)
        self.stats["total_alerts"] += 1
        
        logger.info(f"Alert created: {alert.alert_id} - {alert.title}")
        return alert
    
    async def start_processing(self):
        """Start alert processing loop"""
        if self.is_processing:
            return
        
        self.is_processing = True
        logger.info("Alert processing started")
        
        while self.is_processing:
            try:
                # Get alert from queue with timeout
                alert = await asyncio.wait_for(self.alert_queue.get(), timeout=1.0)
                await self._process_alert(alert)
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.error(f"Error in alert processing loop: {e}")
                await asyncio.sleep(1)
    
    async def stop_processing(self):
        """Stop alert processing"""
        self.is_processing = False
        logger.info("Alert processing stopped")
    
    async def _process_alert(self, alert: Alert):
        """Process individual alert"""
        logger.debug(f"Processing alert: {alert.alert_id}")
        
        alert.status = AlertStatus.PROCESSING
        alert.last_attempt = datetime.utcnow()
        
        # Run custom handler if available
        if alert.alert_type in self.alert_handlers:
            try:
                await self.alert_handlers[alert.alert_type](alert)
            except Exception as e:
                logger.error(f"Custom handler failed for {alert.alert_type}: {e}")
        
        # Deliver through configured channels
        delivery_results = []
        for channel_name in alert.delivery_channels:
            if channel_name in self.channels:
                try:
                    success = await self.channels[channel_name].deliver(alert)
                    delivery_results.append(success)
                except Exception as e:
                    logger.error(f"Alert delivery failed on {channel_name}: {e}")
                    delivery_results.append(False)
            else:
                logger.warning(f"Alert channel not found: {channel_name}")
                delivery_results.append(False)
        
        # Update alert status
        if all(delivery_results):
            alert.status = AlertStatus.DELIVERED
            self.stats["delivered_alerts"] += 1
            logger.info(f"Alert delivered successfully: {alert.alert_id}")
        elif any(delivery_results):
            alert.status = AlertStatus.DELIVERED  # Partial success is still success
            self.stats["delivered_alerts"] += 1
            logger.warning(f"Alert partially delivered: {alert.alert_id}")
        else:
            alert.status = AlertStatus.FAILED
            alert.retry_count += 1
            self.stats["failed_alerts"] += 1
            
            # Retry logic
            if alert.retry_count < 3:
                self.stats["retry_attempts"] += 1
                # Exponential backoff
                retry_delay = 2 ** alert.retry_count
                logger.info(f"Retrying alert {alert.alert_id} in {retry_delay} seconds")
                await asyncio.sleep(retry_delay)
                await self.alert_queue.put(alert)
            else:
                logger.error(f"Alert delivery failed permanently: {alert.alert_id}")
    
    async def create_trading_limit_breach_alert(
        self,
        user_id: int,
        organization_id: int,
        limit_type: str,
        breach_amount: float,
        current_usage: float,
        limit_value: float,
        severity: AlertSeverity = AlertSeverity.ERROR
    ):
        """Create trading limit breach alert"""
        
        return await self.create_alert(
            alert_type="trading_limit_breach",
            category=AlertCategory.TRADING_LIMIT,
            severity=severity,
            title=f"Trading Limit Breached: {limit_type}",
            message=f"User {user_id} exceeded {limit_type} by ₹{breach_amount:,.2f}. "
                   f"Current usage: ₹{current_usage:,.2f}, Limit: ₹{limit_value:,.2f}",
            source_service="user_service",
            user_id=user_id,
            organization_id=organization_id,
            data={
                "limit_type": limit_type,
                "breach_amount": breach_amount,
                "current_usage": current_usage,
                "limit_value": limit_value,
                "breach_percentage": (breach_amount / limit_value) * 100 if limit_value > 0 else 0
            }
        )
    
    async def create_trade_execution_alert(
        self,
        user_id: int,
        trading_account_id: int,
        order_id: str,
        failure_reason: str,
        severity: AlertSeverity = AlertSeverity.WARNING
    ):
        """Create trade execution failure alert"""
        
        return await self.create_alert(
            alert_type="trade_execution_failed",
            category=AlertCategory.TRADE_EXECUTION,
            severity=severity,
            title="Trade Execution Failed",
            message=f"Order {order_id} failed to execute: {failure_reason}",
            source_service="trade_service",
            user_id=user_id,
            trading_account_id=trading_account_id,
            data={
                "order_id": order_id,
                "failure_reason": failure_reason
            }
        )
    
    async def create_system_health_alert(
        self,
        service_name: str,
        component: str,
        error_message: str,
        severity: AlertSeverity = AlertSeverity.ERROR
    ):
        """Create system health alert"""
        
        return await self.create_alert(
            alert_type="service_degraded",
            category=AlertCategory.SYSTEM_HEALTH,
            severity=severity,
            title=f"Service Degraded: {service_name}",
            message=f"Component '{component}' is experiencing issues: {error_message}",
            source_service=service_name,
            data={
                "component": component,
                "error_message": error_message,
                "service": service_name
            }
        )
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get alert statistics"""
        return {
            **self.stats,
            "success_rate": (self.stats["delivered_alerts"] / max(self.stats["total_alerts"], 1)) * 100,
            "channels_registered": list(self.channels.keys()),
            "queue_size": self.alert_queue.qsize()
        }

# Global alert manager instance
_alert_manager: Optional[AlertManager] = None

def init_alert_system(
    email_config: Dict[str, Any] = None,
    slack_webhook: str = None,
    sms_config: Dict[str, Any] = None,
    websocket_manager = None
):
    """Initialize global alert system"""
    global _alert_manager
    
    _alert_manager = AlertManager()
    
    # Register available channels
    if email_config:
        _alert_manager.register_channel(EmailAlertChannel(email_config))
    
    if slack_webhook:
        _alert_manager.register_channel(SlackAlertChannel(slack_webhook))
    
    if sms_config:
        _alert_manager.register_channel(SMSAlertChannel(sms_config))
    
    if websocket_manager:
        _alert_manager.register_channel(WebSocketAlertChannel(websocket_manager))
    
    logger.info("Alert system initialized")

def get_alert_manager() -> AlertManager:
    """Get global alert manager instance"""
    if _alert_manager is None:
        raise RuntimeError("Alert system not initialized. Call init_alert_system() first.")
    return _alert_manager

async def start_alert_processing():
    """Start alert processing"""
    alert_manager = get_alert_manager()
    await alert_manager.start_processing()

async def stop_alert_processing():
    """Stop alert processing"""
    if _alert_manager:
        await _alert_manager.stop_processing()