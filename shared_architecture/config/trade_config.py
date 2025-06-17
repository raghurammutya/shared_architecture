# shared_architecture/config/trade_config.py
import os
from typing import Dict, Any, Optional, List, Union
from dataclasses import dataclass, field
from enum import Enum
import json
from pathlib import Path

from shared_architecture.exceptions.trade_exceptions import ConfigurationException, ErrorContext

class Environment(Enum):
    """Deployment environments"""
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"
    TESTING = "testing"

class FeatureFlag(Enum):
    """Feature flags for gradual rollout"""
    ENHANCED_TRADE_SERVICE = "enhanced_trade_service"
    DATA_CONSISTENCY_VALIDATION = "data_consistency_validation"
    ORDER_MONITORING = "order_monitoring"
    STRATEGY_RETAGGING = "strategy_retagging"
    CIRCUIT_BREAKER = "circuit_breaker"
    PERFORMANCE_MONITORING = "performance_monitoring"
    AUDIT_LOGGING = "audit_logging"

@dataclass
class DatabaseConfig:
    """Database configuration"""
    host: str = "localhost"
    port: int = 5432
    database: str = "trade_service"
    username: str = ""
    password: str = ""
    pool_size: int = 20
    max_overflow: int = 30
    pool_timeout: int = 30
    pool_recycle: int = 3600
    echo: bool = False
    
    def get_connection_string(self, include_password: bool = True) -> str:
        """Get database connection string"""
        password_part = f":{self.password}" if include_password and self.password else ""
        return f"postgresql://{self.username}{password_part}@{self.host}:{self.port}/{self.database}"

@dataclass
class RedisConfig:
    """Redis configuration"""
    host: str = "localhost"
    port: int = 6379
    database: int = 0
    password: Optional[str] = None
    max_connections: int = 50
    health_check_interval: int = 30
    socket_timeout: int = 5
    socket_connect_timeout: int = 5
    retry_on_timeout: bool = True
    
    def get_connection_string(self, include_password: bool = True) -> str:
        """Get Redis connection string"""
        password_part = f":{self.password}@" if include_password and self.password else ""
        return f"redis://{password_part}{self.host}:{self.port}/{self.database}"

@dataclass
class AutoTraderConfig:
    """AutoTrader API configuration"""
    server_url: str = "https://api.stocksdeveloper.in"
    timeout: int = 30
    max_retries: int = 3
    retry_delay: float = 1.0
    retry_exponential_base: float = 2.0
    connection_pool_size: int = 10
    connection_pool_max_size: int = 20
    rate_limit_per_minute: int = 100
    circuit_breaker_failure_threshold: int = 5
    circuit_breaker_recovery_timeout: int = 60
    circuit_breaker_expected_exception: str = "AutoTraderException"

@dataclass
class RateLimitConfig:
    """Rate limiting configuration"""
    requests_per_minute: int = 60
    requests_per_hour: int = 1000
    requests_per_day: int = 10000
    burst_allowance: int = 10
    window_size: int = 60  # seconds
    cleanup_interval: int = 300  # seconds
    redis_key_prefix: str = "rate_limit"
    redis_key_ttl: int = 3600  # seconds

@dataclass
class MonitoringConfig:
    """Monitoring and observability configuration"""
    enable_metrics: bool = True
    enable_tracing: bool = True
    enable_profiling: bool = False
    metrics_port: int = 9090
    health_check_interval: int = 30
    performance_threshold_ms: int = 1000
    error_rate_threshold: float = 0.05
    alert_webhook_url: Optional[str] = None
    log_level: str = "INFO"
    correlation_id_header: str = "X-Correlation-ID"

@dataclass
class SecurityConfig:
    """Security configuration"""
    enable_api_key_validation: bool = True
    enable_input_sanitization: bool = True
    enable_audit_logging: bool = True
    max_request_size: int = 1024 * 1024  # 1MB
    allowed_hosts: List[str] = field(default_factory=lambda: ["*"])
    cors_origins: List[str] = field(default_factory=lambda: ["*"])
    api_key_rotation_days: int = 90
    session_timeout_minutes: int = 60
    max_login_attempts: int = 5
    lockout_duration_minutes: int = 15

@dataclass
class CeleryConfig:
    """Celery configuration"""
    broker_url: str = "redis://localhost:6379/0"
    result_backend: str = "redis://localhost:6379/0"
    task_serializer: str = "json"
    result_serializer: str = "json"
    accept_content: List[str] = field(default_factory=lambda: ["json"])
    task_acks_late: bool = True
    worker_prefetch_multiplier: int = 1
    task_default_retry_delay: int = 5
    task_max_retries: int = 3
    timezone: str = "UTC"
    enable_utc: bool = True

@dataclass
class TradeServiceConfig:
    """Main trade service configuration"""
    environment: Environment = Environment.DEVELOPMENT
    service_name: str = "trade_service"
    service_version: str = "1.0.0"
    debug: bool = False
    
    # Component configurations
    database: DatabaseConfig = field(default_factory=DatabaseConfig)
    redis: RedisConfig = field(default_factory=RedisConfig)
    autotrader: AutoTraderConfig = field(default_factory=AutoTraderConfig)
    rate_limiting: RateLimitConfig = field(default_factory=RateLimitConfig)
    monitoring: MonitoringConfig = field(default_factory=MonitoringConfig)
    security: SecurityConfig = field(default_factory=SecurityConfig)
    celery: CeleryConfig = field(default_factory=CeleryConfig)
    
    # Feature flags
    feature_flags: Dict[str, bool] = field(default_factory=lambda: {
        FeatureFlag.ENHANCED_TRADE_SERVICE.value: True,
        FeatureFlag.DATA_CONSISTENCY_VALIDATION.value: True,
        FeatureFlag.ORDER_MONITORING.value: True,
        FeatureFlag.STRATEGY_RETAGGING.value: True,
        FeatureFlag.CIRCUIT_BREAKER.value: True,
        FeatureFlag.PERFORMANCE_MONITORING.value: True,
        FeatureFlag.AUDIT_LOGGING.value: True,
    })
    
    # Trading limits
    max_order_quantity: int = 999999
    max_order_value: float = 10000000.0
    min_order_value: float = 1.0
    max_daily_orders: int = 1000
    max_orders_per_minute: int = 10
    
    # Data consistency settings
    consistency_check_interval: int = 300  # seconds
    consistency_tolerance: float = 0.01  # 1% tolerance
    auto_fix_minor_issues: bool = False
    
    def __post_init__(self):
        """Validate configuration after initialization"""
        self._validate_config()
    
    def _validate_config(self):
        """Validate configuration values"""
        errors = []
        
        # Validate environment
        if not isinstance(self.environment, Environment):
            errors.append("Invalid environment value")
        
        # Validate database config
        if not self.database.host:
            errors.append("Database host is required")
        if not self.database.username:
            errors.append("Database username is required")
        if self.database.port <= 0 or self.database.port > 65535:
            errors.append("Database port must be between 1 and 65535")
        
        # Validate Redis config
        if not self.redis.host:
            errors.append("Redis host is required")
        if self.redis.port <= 0 or self.redis.port > 65535:
            errors.append("Redis port must be between 1 and 65535")
        
        # Validate AutoTrader config
        if not self.autotrader.server_url:
            errors.append("AutoTrader server URL is required")
        if self.autotrader.timeout <= 0:
            errors.append("AutoTrader timeout must be positive")
        
        # Validate trading limits
        if self.max_order_quantity <= 0:
            errors.append("Max order quantity must be positive")
        if self.max_order_value <= 0:
            errors.append("Max order value must be positive")
        if self.min_order_value <= 0:
            errors.append("Min order value must be positive")
        if self.min_order_value >= self.max_order_value:
            errors.append("Min order value must be less than max order value")
        
        if errors:
            raise ConfigurationException(
                f"Configuration validation failed: {'; '.join(errors)}",
                context=ErrorContext(additional_data={"validation_errors": errors})
            )
    
    def is_feature_enabled(self, feature: Union[FeatureFlag, str]) -> bool:
        """Check if a feature flag is enabled"""
        feature_name = feature.value if isinstance(feature, FeatureFlag) else feature
        return self.feature_flags.get(feature_name, False)
    
    def enable_feature(self, feature: Union[FeatureFlag, str]):
        """Enable a feature flag"""
        feature_name = feature.value if isinstance(feature, FeatureFlag) else feature
        self.feature_flags[feature_name] = True
    
    def disable_feature(self, feature: Union[FeatureFlag, str]):
        """Disable a feature flag"""
        feature_name = feature.value if isinstance(feature, FeatureFlag) else feature
        self.feature_flags[feature_name] = False
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary"""
        def convert_value(value):
            if hasattr(value, '__dict__'):
                return {k: convert_value(v) for k, v in value.__dict__.items()}
            elif isinstance(value, Enum):
                return value.value
            elif isinstance(value, list):
                return [convert_value(item) for item in value]
            elif isinstance(value, dict):
                return {k: convert_value(v) for k, v in value.items()}
            else:
                return value
        
        return convert_value(self)
    
    def get_sensitive_config(self) -> Dict[str, str]:
        """Get configuration with sensitive values masked"""
        config_dict = self.to_dict()
        
        # Mask sensitive values
        if 'database' in config_dict and 'password' in config_dict['database']:
            config_dict['database']['password'] = "***MASKED***"
        if 'redis' in config_dict and 'password' in config_dict['redis']:
            config_dict['redis']['password'] = "***MASKED***"
        
        return config_dict

class ConfigurationManager:
    """Configuration manager with environment-specific loading"""
    
    def __init__(self, config_dir: str = None):
        self.config_dir = Path(config_dir) if config_dir else Path(__file__).parent
        self.config: Optional[TradeServiceConfig] = None
    
    def load_config(self, environment: Union[Environment, str] = None) -> TradeServiceConfig:
        """Load configuration for specified environment"""
        env = self._determine_environment(environment)
        
        # Start with default configuration
        config = TradeServiceConfig(environment=env)
        
        # Load environment-specific overrides
        config = self._load_environment_config(config, env)
        
        # Load from environment variables
        config = self._load_from_environment_variables(config)
        
        # Final validation
        config._validate_config()
        
        self.config = config
        return config
    
    def _determine_environment(self, environment: Union[Environment, str] = None) -> Environment:
        """Determine the current environment"""
        if environment:
            if isinstance(environment, str):
                try:
                    return Environment(environment.lower())
                except ValueError:
                    raise ConfigurationException(f"Invalid environment: {environment}")
            return environment
        
        # Check environment variable
        env_var = os.getenv("ENVIRONMENT", os.getenv("ENV", "development")).lower()
        try:
            return Environment(env_var)
        except ValueError:
            return Environment.DEVELOPMENT
    
    def _load_environment_config(self, config: TradeServiceConfig, env: Environment) -> TradeServiceConfig:
        """Load environment-specific configuration files"""
        config_files = [
            self.config_dir / "config.json",
            self.config_dir / f"config.{env.value}.json",
            self.config_dir / "local.config.json",  # For local overrides
        ]
        
        for config_file in config_files:
            if config_file.exists():
                try:
                    with open(config_file, 'r') as f:
                        file_config = json.load(f)
                    config = self._merge_config(config, file_config)
                except Exception as e:
                    raise ConfigurationException(
                        f"Failed to load config file {config_file}: {str(e)}",
                        config_key=str(config_file)
                    )
        
        return config
    
    def _load_from_environment_variables(self, config: TradeServiceConfig) -> TradeServiceConfig:
        """Load configuration from environment variables"""
        env_mappings = {
            # Database
            "DB_HOST": ("database", "host"),
            "DB_PORT": ("database", "port"),
            "DB_NAME": ("database", "database"),
            "DB_USER": ("database", "username"),
            "DB_PASSWORD": ("database", "password"),
            "DB_POOL_SIZE": ("database", "pool_size"),
            
            # Redis
            "REDIS_HOST": ("redis", "host"),
            "REDIS_PORT": ("redis", "port"),
            "REDIS_DB": ("redis", "database"),
            "REDIS_PASSWORD": ("redis", "password"),
            
            # AutoTrader
            "AUTOTRADER_URL": ("autotrader", "server_url"),
            "AUTOTRADER_TIMEOUT": ("autotrader", "timeout"),
            
            # Service
            "SERVICE_NAME": (None, "service_name"),
            "SERVICE_VERSION": (None, "service_version"),
            "DEBUG": (None, "debug"),
            
            # Monitoring
            "LOG_LEVEL": ("monitoring", "log_level"),
            "METRICS_ENABLED": ("monitoring", "enable_metrics"),
        }
        
        for env_var, (section, key) in env_mappings.items():
            value = os.getenv(env_var)
            if value is not None:
                try:
                    # Convert value to appropriate type
                    if key in ["port", "pool_size", "database", "timeout"]:
                        value = int(value)
                    elif key in ["debug", "enable_metrics", "enable_tracing"]:
                        value = value.lower() in ("true", "1", "yes", "on")
                    
                    # Set the value
                    if section:
                        section_obj = getattr(config, section)
                        setattr(section_obj, key, value)
                    else:
                        setattr(config, key, value)
                        
                except (ValueError, AttributeError) as e:
                    raise ConfigurationException(
                        f"Invalid environment variable {env_var}={value}: {str(e)}",
                        config_key=env_var
                    )
        
        return config
    
    def _merge_config(self, base_config: TradeServiceConfig, override_config: Dict[str, Any]) -> TradeServiceConfig:
        """Merge override configuration into base configuration"""
        for key, value in override_config.items():
            if hasattr(base_config, key):
                current_value = getattr(base_config, key)
                if hasattr(current_value, '__dict__') and isinstance(value, dict):
                    # Merge nested configuration objects
                    for nested_key, nested_value in value.items():
                        if hasattr(current_value, nested_key):
                            setattr(current_value, nested_key, nested_value)
                else:
                    setattr(base_config, key, value)
        
        return base_config
    
    def save_config(self, config: TradeServiceConfig, filename: str = None):
        """Save configuration to file"""
        if not filename:
            filename = f"config.{config.environment.value}.json"
        
        config_file = self.config_dir / filename
        
        try:
            with open(config_file, 'w') as f:
                json.dump(config.get_sensitive_config(), f, indent=2)
        except Exception as e:
            raise ConfigurationException(
                f"Failed to save config to {config_file}: {str(e)}",
                config_key=str(config_file)
            )

# Global configuration instance
_config_manager = ConfigurationManager()
_current_config: Optional[TradeServiceConfig] = None

def get_config() -> TradeServiceConfig:
    """Get the current configuration instance"""
    global _current_config
    if _current_config is None:
        _current_config = _config_manager.load_config()
    return _current_config

def reload_config(environment: Union[Environment, str] = None) -> TradeServiceConfig:
    """Reload configuration"""
    global _current_config
    _current_config = _config_manager.load_config(environment)
    return _current_config

def is_feature_enabled(feature: Union[FeatureFlag, str]) -> bool:
    """Check if a feature is enabled in current configuration"""
    return get_config().is_feature_enabled(feature)

def get_database_config() -> DatabaseConfig:
    """Get database configuration"""
    return get_config().database

def get_redis_config() -> RedisConfig:
    """Get Redis configuration"""
    return get_config().redis

def get_autotrader_config() -> AutoTraderConfig:
    """Get AutoTrader configuration"""
    return get_config().autotrader

def get_monitoring_config() -> MonitoringConfig:
    """Get monitoring configuration"""
    return get_config().monitoring

def get_security_config() -> SecurityConfig:
    """Get security configuration"""
    return get_config().security