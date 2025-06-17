# shared_architecture/alerting/alert_manager.py
"""
Comprehensive alerting and notification system for trade service.
Monitors metrics, health, and system state to trigger appropriate alerts.
"""

import asyncio
import time
import json
import smtplib
import httpx
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List, Callable, Union
from dataclasses import dataclass, field, asdict
from enum import Enum
from email.mime.text import MimeText
from email.mime.multipart import MimeMultipart
import threading

from shared_architecture.utils.enhanced_logging import get_logger
from shared_architecture.monitoring.metrics_collector import MetricsCollector
from shared_architecture.monitoring.health_checker import HealthChecker, HealthStatus

logger = get_logger(__name__)

class AlertSeverity(Enum):
    """Alert severity levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class AlertStatus(Enum):
    """Alert status."""
    ACTIVE = "active"
    RESOLVED = "resolved"
    SUPPRESSED = "suppressed"
    ACKNOWLEDGED = "acknowledged"

class NotificationChannel(Enum):
    """Notification channels."""
    EMAIL = "email"
    SLACK = "slack"
    WEBHOOK = "webhook"
    SMS = "sms"
    PAGERDUTY = "pagerduty"

@dataclass
class AlertRule:
    """Definition of an alert rule."""
    name: str
    description: str
    condition: str  # Condition expression
    severity: AlertSeverity
    evaluation_interval: int = 60  # Seconds
    for_duration: int = 300  # Seconds - how long condition must be true
    labels: Dict[str, str] = field(default_factory=dict)
    annotations: Dict[str, str] = field(default_factory=dict)
    enabled: bool = True
    notification_channels: List[NotificationChannel] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)

@dataclass
class Alert:
    """An active or resolved alert."""
    id: str
    rule_name: str
    severity: AlertSeverity
    status: AlertStatus
    message: str
    started_at: datetime
    resolved_at: Optional[datetime] = None
    acknowledged_at: Optional[datetime] = None
    acknowledged_by: Optional[str] = None
    labels: Dict[str, str] = field(default_factory=dict)
    annotations: Dict[str, str] = field(default_factory=dict)
    notification_count: int = 0
    last_notification: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        result = asdict(self)
        result['severity'] = self.severity.value
        result['status'] = self.status.value
        result['started_at'] = self.started_at.isoformat()
        result['resolved_at'] = self.resolved_at.isoformat() if self.resolved_at else None
        result['acknowledged_at'] = self.acknowledged_at.isoformat() if self.acknowledged_at else None
        result['last_notification'] = self.last_notification.isoformat() if self.last_notification else None
        return result

@dataclass
class NotificationConfig:
    """Configuration for notification channels."""
    email: Optional[Dict[str, Any]] = None
    slack: Optional[Dict[str, Any]] = None
    webhook: Optional[Dict[str, Any]] = None
    sms: Optional[Dict[str, Any]] = None
    pagerduty: Optional[Dict[str, Any]] = None

class AlertEvaluator:
    """Evaluates alert conditions against metrics and system state."""
    
    def __init__(self, metrics_collector: MetricsCollector, health_checker: HealthChecker):
        self.metrics_collector = metrics_collector
        self.health_checker = health_checker
        self.logger = get_logger(__name__)
    
    async def evaluate_condition(self, condition: str, context: Dict[str, Any] = None) -> bool:
        """
        Evaluate an alert condition.
        
        Conditions can reference:
        - metric(name, tags) - get latest metric value
        - health(component) - get health status
        - rate(metric, window) - get rate of change
        - avg(metric, window) - get average over time window
        """
        try:
            # Create evaluation context
            eval_context = {
                'metric': self._get_metric_value,
                'health': self._get_health_status,
                'rate': self._get_metric_rate,
                'avg': self._get_metric_average,
                'time': time.time(),
                'datetime': datetime.utcnow(),
                **(context or {})
            }
            
            # Evaluate condition
            result = eval(condition, {"__builtins__": {}}, eval_context)
            return bool(result)
            
        except Exception as e:
            self.logger.error(f"Error evaluating condition '{condition}': {e}", exc_info=True)
            return False
    
    def _get_metric_value(self, name: str, tags: Dict[str, str] = None) -> float:
        """Get latest metric value."""
        metric_series = self.metrics_collector.get_metric(name, tags)
        if metric_series and metric_series.points:
            return float(metric_series.points[-1].value)
        return 0.0
    
    async def _get_health_status(self, component: str = None) -> bool:
        """Get health status (True = healthy, False = unhealthy)."""
        if component:
            result = await self.health_checker.get_component_health(component)
            return result.status == HealthStatus.HEALTHY if result else False
        else:
            system_health = await self.health_checker.check_all()
            return system_health.overall_status == HealthStatus.HEALTHY
    
    def _get_metric_rate(self, name: str, window_minutes: int = 5, tags: Dict[str, str] = None) -> float:
        """Get rate of change for a metric."""
        metric_series = self.metrics_collector.get_metric(name, tags)
        if not metric_series or len(metric_series.points) < 2:
            return 0.0
        
        cutoff = datetime.utcnow() - timedelta(minutes=window_minutes)
        recent_points = metric_series.get_since(cutoff)
        
        if len(recent_points) < 2:
            return 0.0
        
        # Calculate rate between first and last points
        first_point = recent_points[0]
        last_point = recent_points[-1]
        
        time_diff = (last_point.timestamp - first_point.timestamp).total_seconds()
        if time_diff > 0:
            return (last_point.value - first_point.value) / time_diff
        
        return 0.0
    
    def _get_metric_average(self, name: str, window_minutes: int = 5, tags: Dict[str, str] = None) -> float:
        """Get average metric value over time window."""
        metric_series = self.metrics_collector.get_metric(name, tags)
        if not metric_series:
            return 0.0
        
        cutoff = datetime.utcnow() - timedelta(minutes=window_minutes)
        recent_points = metric_series.get_since(cutoff)
        
        if not recent_points:
            return 0.0
        
        return sum(point.value for point in recent_points) / len(recent_points)

class NotificationSender:
    """Sends notifications through various channels."""
    
    def __init__(self, config: NotificationConfig):
        self.config = config
        self.logger = get_logger(__name__)
    
    async def send_notification(self, alert: Alert, channels: List[NotificationChannel]):
        """Send notification through specified channels."""
        tasks = []
        
        for channel in channels:
            if channel == NotificationChannel.EMAIL and self.config.email:
                tasks.append(self._send_email(alert))
            elif channel == NotificationChannel.SLACK and self.config.slack:
                tasks.append(self._send_slack(alert))
            elif channel == NotificationChannel.WEBHOOK and self.config.webhook:
                tasks.append(self._send_webhook(alert))
            elif channel == NotificationChannel.SMS and self.config.sms:
                tasks.append(self._send_sms(alert))
            elif channel == NotificationChannel.PAGERDUTY and self.config.pagerduty:
                tasks.append(self._send_pagerduty(alert))
        
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
    
    async def _send_email(self, alert: Alert):
        """Send email notification."""
        try:
            config = self.config.email
            
            msg = MimeMultipart()
            msg['From'] = config['from_address']
            msg['To'] = ', '.join(config['to_addresses'])
            msg['Subject'] = f"[{alert.severity.value.upper()}] {alert.rule_name}"
            
            # Create HTML body
            html_body = f"""
            <html>
            <body>
                <h2>Alert: {alert.rule_name}</h2>
                <p><strong>Severity:</strong> {alert.severity.value.upper()}</p>
                <p><strong>Status:</strong> {alert.status.value}</p>
                <p><strong>Started:</strong> {alert.started_at.isoformat()}</p>
                <p><strong>Message:</strong> {alert.message}</p>
                
                <h3>Labels:</h3>
                <ul>
                    {''.join(f'<li>{k}: {v}</li>' for k, v in alert.labels.items())}
                </ul>
                
                <h3>Annotations:</h3>
                <ul>
                    {''.join(f'<li>{k}: {v}</li>' for k, v in alert.annotations.items())}
                </ul>
            </body>
            </html>
            """
            
            msg.attach(MimeText(html_body, 'html'))
            
            # Send email
            with smtplib.SMTP(config['smtp_server'], config['smtp_port']) as server:
                if config.get('use_tls'):
                    server.starttls()
                if config.get('username'):
                    server.login(config['username'], config['password'])
                server.send_message(msg)
            
            self.logger.info(f"Email notification sent for alert: {alert.rule_name}")
            
        except Exception as e:
            self.logger.error(f"Failed to send email notification: {e}", exc_info=True)
    
    async def _send_slack(self, alert: Alert):
        """Send Slack notification."""
        try:
            config = self.config.slack
            
            # Determine color based on severity
            color_map = {
                AlertSeverity.LOW: "#36a64f",
                AlertSeverity.MEDIUM: "#ff9500",
                AlertSeverity.HIGH: "#ff4500",
                AlertSeverity.CRITICAL: "#ff0000"
            }
            
            payload = {
                "channel": config['channel'],
                "username": config.get('username', 'Trade Service Alerts'),
                "icon_emoji": config.get('icon_emoji', ':warning:'),
                "attachments": [
                    {
                        "color": color_map.get(alert.severity, "#cccccc"),
                        "title": f"Alert: {alert.rule_name}",
                        "text": alert.message,
                        "fields": [
                            {"title": "Severity", "value": alert.severity.value.upper(), "short": True},
                            {"title": "Status", "value": alert.status.value, "short": True},
                            {"title": "Started", "value": alert.started_at.isoformat(), "short": False}
                        ],
                        "footer": "Trade Service",
                        "ts": int(alert.started_at.timestamp())
                    }
                ]
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    config['webhook_url'],
                    json=payload,
                    timeout=10
                )
                response.raise_for_status()
            
            self.logger.info(f"Slack notification sent for alert: {alert.rule_name}")
            
        except Exception as e:
            self.logger.error(f"Failed to send Slack notification: {e}", exc_info=True)
    
    async def _send_webhook(self, alert: Alert):
        """Send webhook notification."""
        try:
            config = self.config.webhook
            
            payload = {
                "alert": alert.to_dict(),
                "timestamp": datetime.utcnow().isoformat(),
                "service": "trade_service"
            }
            
            headers = config.get('headers', {})
            headers['Content-Type'] = 'application/json'
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    config['url'],
                    json=payload,
                    headers=headers,
                    timeout=30
                )
                response.raise_for_status()
            
            self.logger.info(f"Webhook notification sent for alert: {alert.rule_name}")
            
        except Exception as e:
            self.logger.error(f"Failed to send webhook notification: {e}", exc_info=True)
    
    async def _send_sms(self, alert: Alert):
        """Send SMS notification."""
        # Implementation would depend on SMS provider (Twilio, AWS SNS, etc.)
        self.logger.info(f"SMS notification not implemented for alert: {alert.rule_name}")
    
    async def _send_pagerduty(self, alert: Alert):
        """Send PagerDuty notification."""
        try:
            config = self.config.pagerduty
            
            payload = {
                "routing_key": config['routing_key'],
                "event_action": "trigger" if alert.status == AlertStatus.ACTIVE else "resolve",
                "dedup_key": f"trade_service_{alert.rule_name}",
                "payload": {
                    "summary": f"{alert.severity.value.upper()}: {alert.rule_name}",
                    "source": "trade_service",
                    "severity": alert.severity.value,
                    "custom_details": {
                        "message": alert.message,
                        "labels": alert.labels,
                        "annotations": alert.annotations,
                        "started_at": alert.started_at.isoformat()
                    }
                }
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "https://events.pagerduty.com/v2/enqueue",
                    json=payload,
                    timeout=30
                )
                response.raise_for_status()
            
            self.logger.info(f"PagerDuty notification sent for alert: {alert.rule_name}")
            
        except Exception as e:
            self.logger.error(f"Failed to send PagerDuty notification: {e}", exc_info=True)

class AlertManager:
    """Main alert manager that coordinates rule evaluation and notifications."""
    
    def __init__(self, notification_config: NotificationConfig):
        self.rules: Dict[str, AlertRule] = {}
        self.active_alerts: Dict[str, Alert] = {}
        self.alert_history: List[Alert] = []
        self.evaluator = AlertEvaluator(
            MetricsCollector.get_instance(),
            HealthChecker()  # Would be injected in real implementation
        )
        self.notification_sender = NotificationSender(notification_config)
        self.logger = get_logger(__name__)
        
        # Background task
        self._evaluation_task: Optional[asyncio.Task] = None
        self._should_stop = False
        self._lock = threading.Lock()
    
    def add_rule(self, rule: AlertRule):
        """Add an alert rule."""
        with self._lock:
            self.rules[rule.name] = rule
        self.logger.info(f"Added alert rule: {rule.name}")
    
    def remove_rule(self, rule_name: str):
        """Remove an alert rule."""
        with self._lock:
            if rule_name in self.rules:
                del self.rules[rule_name]
                # Resolve any active alerts for this rule
                self._resolve_alerts_for_rule(rule_name)
        self.logger.info(f"Removed alert rule: {rule_name}")
    
    def get_rule(self, rule_name: str) -> Optional[AlertRule]:
        """Get an alert rule."""
        return self.rules.get(rule_name)
    
    def get_all_rules(self) -> Dict[str, AlertRule]:
        """Get all alert rules."""
        return self.rules.copy()
    
    def get_active_alerts(self) -> Dict[str, Alert]:
        """Get all active alerts."""
        return self.active_alerts.copy()
    
    def get_alert_history(self, limit: int = 100) -> List[Alert]:
        """Get alert history."""
        return self.alert_history[-limit:]
    
    def acknowledge_alert(self, alert_id: str, acknowledged_by: str):
        """Acknowledge an alert."""
        if alert_id in self.active_alerts:
            alert = self.active_alerts[alert_id]
            alert.status = AlertStatus.ACKNOWLEDGED
            alert.acknowledged_at = datetime.utcnow()
            alert.acknowledged_by = acknowledged_by
            self.logger.info(f"Alert acknowledged: {alert.rule_name} by {acknowledged_by}")
    
    def resolve_alert(self, alert_id: str):
        """Manually resolve an alert."""
        if alert_id in self.active_alerts:
            alert = self.active_alerts[alert_id]
            alert.status = AlertStatus.RESOLVED
            alert.resolved_at = datetime.utcnow()
            
            # Move to history
            self.alert_history.append(alert)
            del self.active_alerts[alert_id]
            
            self.logger.info(f"Alert manually resolved: {alert.rule_name}")
    
    def start_evaluation(self):
        """Start the alert evaluation loop."""
        if self._evaluation_task is None:
            self._should_stop = False
            self._evaluation_task = asyncio.create_task(self._evaluation_loop())
            self.logger.info("Alert evaluation started")
    
    def stop_evaluation(self):
        """Stop the alert evaluation loop."""
        self._should_stop = True
        if self._evaluation_task:
            self._evaluation_task.cancel()
            self._evaluation_task = None
        self.logger.info("Alert evaluation stopped")
    
    async def _evaluation_loop(self):
        """Main evaluation loop."""
        while not self._should_stop:
            try:
                await self._evaluate_all_rules()
                await asyncio.sleep(30)  # Evaluate every 30 seconds
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in alert evaluation loop: {e}", exc_info=True)
                await asyncio.sleep(60)  # Wait longer on error
    
    async def _evaluate_all_rules(self):
        """Evaluate all alert rules."""
        for rule in self.rules.values():
            if not rule.enabled:
                continue
            
            try:
                await self._evaluate_rule(rule)
            except Exception as e:
                self.logger.error(f"Error evaluating rule {rule.name}: {e}", exc_info=True)
    
    async def _evaluate_rule(self, rule: AlertRule):
        """Evaluate a single alert rule."""
        # Check if condition is true
        condition_met = await self.evaluator.evaluate_condition(rule.condition)
        
        # Check if we have an active alert for this rule
        existing_alert = None
        for alert in self.active_alerts.values():
            if alert.rule_name == rule.name:
                existing_alert = alert
                break
        
        if condition_met:
            if not existing_alert:
                # Check if condition has been true for required duration
                # For simplicity, we'll create the alert immediately
                # In a real implementation, you'd track condition state over time
                await self._create_alert(rule)
            else:
                # Alert already exists, check if we need to send notifications
                await self._check_notification_schedule(existing_alert, rule)
        else:
            if existing_alert:
                # Condition no longer met, resolve alert
                await self._resolve_alert(existing_alert)
    
    async def _create_alert(self, rule: AlertRule):
        """Create a new alert."""
        alert_id = f"{rule.name}_{int(time.time())}"
        
        alert = Alert(
            id=alert_id,
            rule_name=rule.name,
            severity=rule.severity,
            status=AlertStatus.ACTIVE,
            message=rule.annotations.get('summary', f"Alert condition met for {rule.name}"),
            started_at=datetime.utcnow(),
            labels=rule.labels.copy(),
            annotations=rule.annotations.copy()
        )
        
        self.active_alerts[alert_id] = alert
        
        # Send initial notification
        await self.notification_sender.send_notification(alert, rule.notification_channels)
        alert.notification_count = 1
        alert.last_notification = datetime.utcnow()
        
        self.logger.warning(
            f"Alert created: {rule.name}",
            alert_id=alert_id,
            severity=rule.severity.value,
            message=alert.message
        )
    
    async def _resolve_alert(self, alert: Alert):
        """Resolve an alert."""
        alert.status = AlertStatus.RESOLVED
        alert.resolved_at = datetime.utcnow()
        
        # Move to history
        self.alert_history.append(alert)
        del self.active_alerts[alert.id]
        
        # Send resolution notification
        rule = self.rules.get(alert.rule_name)
        if rule:
            await self.notification_sender.send_notification(alert, rule.notification_channels)
        
        self.logger.info(f"Alert resolved: {alert.rule_name}")
    
    async def _check_notification_schedule(self, alert: Alert, rule: AlertRule):
        """Check if we should send repeat notifications."""
        if alert.status == AlertStatus.ACKNOWLEDGED:
            return  # Don't send notifications for acknowledged alerts
        
        # Send notifications every hour for high/critical alerts
        notification_interval = timedelta(hours=1)
        if rule.severity in [AlertSeverity.HIGH, AlertSeverity.CRITICAL]:
            notification_interval = timedelta(minutes=30)
        
        if (alert.last_notification is None or 
            datetime.utcnow() - alert.last_notification >= notification_interval):
            
            await self.notification_sender.send_notification(alert, rule.notification_channels)
            alert.notification_count += 1
            alert.last_notification = datetime.utcnow()
    
    def _resolve_alerts_for_rule(self, rule_name: str):
        """Resolve all active alerts for a rule."""
        alerts_to_resolve = [
            alert for alert in self.active_alerts.values()
            if alert.rule_name == rule_name
        ]
        
        for alert in alerts_to_resolve:
            alert.status = AlertStatus.RESOLVED
            alert.resolved_at = datetime.utcnow()
            self.alert_history.append(alert)
            del self.active_alerts[alert.id]

# Predefined alert rules for common scenarios
def create_default_alert_rules() -> List[AlertRule]:
    """Create default alert rules for trade service."""
    rules = []
    
    # High error rate
    rules.append(AlertRule(
        name="high_error_rate",
        description="Error rate exceeds 5% over 5 minutes",
        condition="rate('trade_errors_total', 5) / rate('trade_api_requests_total', 5) > 0.05",
        severity=AlertSeverity.HIGH,
        evaluation_interval=60,
        for_duration=300,
        labels={"service": "trade_service", "type": "error_rate"},
        annotations={"summary": "High error rate detected"},
        notification_channels=[NotificationChannel.SLACK, NotificationChannel.EMAIL]
    ))
    
    # Database connectivity
    rules.append(AlertRule(
        name="database_unhealthy",
        description="Database health check failing",
        condition="not health('database')",
        severity=AlertSeverity.CRITICAL,
        evaluation_interval=30,
        for_duration=60,
        labels={"service": "trade_service", "component": "database"},
        annotations={"summary": "Database is unhealthy"},
        notification_channels=[NotificationChannel.PAGERDUTY, NotificationChannel.EMAIL]
    ))
    
    # High response time
    rules.append(AlertRule(
        name="high_response_time",
        description="API response time exceeds 2 seconds",
        condition="avg('trade_api_response_duration', 5) > 2000",
        severity=AlertSeverity.MEDIUM,
        evaluation_interval=60,
        for_duration=300,
        labels={"service": "trade_service", "type": "performance"},
        annotations={"summary": "High API response time"},
        notification_channels=[NotificationChannel.SLACK]
    ))
    
    # Circuit breaker open
    rules.append(AlertRule(
        name="circuit_breaker_open",
        description="Circuit breaker is open",
        condition="metric('circuit_breaker_state') == 2",
        severity=AlertSeverity.HIGH,
        evaluation_interval=30,
        for_duration=60,
        labels={"service": "trade_service", "type": "circuit_breaker"},
        annotations={"summary": "Circuit breaker is open"},
        notification_channels=[NotificationChannel.SLACK, NotificationChannel.EMAIL]
    ))
    
    return rules

# Global alert manager (would be configured in application startup)
_alert_manager: Optional[AlertManager] = None

def get_alert_manager() -> Optional[AlertManager]:
    """Get the global alert manager instance."""
    return _alert_manager

def setup_alert_manager(notification_config: NotificationConfig) -> AlertManager:
    """Setup the global alert manager."""
    global _alert_manager
    _alert_manager = AlertManager(notification_config)
    
    # Add default rules
    for rule in create_default_alert_rules():
        _alert_manager.add_rule(rule)
    
    return _alert_manager