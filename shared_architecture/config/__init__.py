"""
Shared configuration initialization for Stocksblitz microservices.

This module unifies access to:
- Config loader (Kubernetes ConfigMap + environment fallback)
- Global settings (timezone, currency, locale)
- Secrets manager
- Validators
"""

from .config_loader import ConfigLoader, config_loader
from .global_settings import DEFAULT_CURRENCY, DEFAULT_TIMEZONE, DEFAULT_LOCALE
from .secrets_manager import get_secret
from .validators import validate_required_keys

__all__ = [
    "ConfigLoader",
    "config_loader",
    "DEFAULT_CURRENCY",
    "DEFAULT_TIMEZONE",
    "DEFAULT_LOCALE",
    "get_secret",
    "validate_required_keys"
]
