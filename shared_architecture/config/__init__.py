"""
Configuration Package Initialization

This module initializes the shared_architecture.config package. It exposes
functions and configurations such as shared_config and service_config to be
used across services.
"""

from .common import shared_config, get_shared_config
from .secrets import get_secret, decode_secret, validate_secrets

# Optional scoped configuration
try:
    from .scoped import get_scoped_config
except ImportError:
    get_scoped_config = None

__all__ = [
    "shared_config", 
    "get_shared_config", 
    "get_secret", 
    "decode_secret", 
    "validate_secrets", 
    "get_scoped_config",
    "get_service_configs"
]

# Add a blank line at the end for PEP 8 compliance
