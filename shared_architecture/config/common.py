"""
Common Configuration Module

This module provides shared configurations used across services.
Configurations are dynamically loaded from environment variables, allowing for
flexibility in different environments
"""
import os
import logging

logging.basicConfig(
level=logging.INFO,
format="%(asctime)s - %(levelname)s - %(message)s",
)

# Shared global configuration
shared_config = {
    "DATABASE_HOST": os.getenv("DATABASE_HOST", "localhost"),
    "DATABASE_PORT": os.getenv("DATABASE_PORT", "5432"),
    "POSTGRES_HOST": os.getenv("POSTGRES_HOST", "localhost"),
    "POSTGRES_PORT": os.getenv("POSTGRES_PORT", "5432"),
    }

# Helper to retrieve specific configurations
def get_shared_config() -> dict:
    """
    Returns the shared configuration after logging.
    """
    logging.info("Retrieving Shared Config:")
    for key, value in shared_config.items():
        logging.info(f" {key}: {value} (Source: env or default)")
    return shared_config