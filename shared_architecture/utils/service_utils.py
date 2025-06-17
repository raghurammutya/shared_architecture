# shared_architecture/utils/service_utils.py

import os
from typing import Optional, Dict, List, Any
from fastapi import FastAPI
from shared_architecture.config.config_loader import config_loader
from shared_architecture.utils.logging_utils import configure_logging, log_info, log_exception
from shared_architecture.connections.connection_manager import connection_manager


async def initialize_all_connections() -> Dict[str, Any]:
    """
    Legacy function for backward compatibility.
    Now uses the new connection manager.
    """
    await connection_manager.initialize()
    return {
        "redis": connection_manager.redis,
        "timescaledb": connection_manager.timescaledb,
        "timescaledb_sync": connection_manager.timescaledb_sync,
        "rabbitmq": connection_manager.rabbitmq,
        "mongodb": connection_manager.mongodb,
    }


async def close_all_connections(connections: Optional[Dict[str, Any]] = None) -> None:
    """
    Legacy function for backward compatibility.
    Now uses the connection manager's close method.
    """
    await connection_manager.close()


def start_service(service_name: str) -> FastAPI:
    """
    Complete service initialization that handles everything in one shot:
    1. FastAPI app creation
    2. Configuration loading  
    3. Logging setup
    4. Metrics setup
    5. Connection initialization with service discovery
    6. App state setup with connections and config
    """
    from fastapi import FastAPI
    from shared_architecture.config import config_loader
    from shared_architecture.utils.logging_utils import configure_logging
    from shared_architecture.utils.prometheus_metrics import setup_metrics

    app = FastAPI(title=service_name)
    
    # Load configuration
    config_loader.load(service_name)
    
    # Setup logging
    configure_logging(service_name)
    
    # Setup metrics
    setup_metrics(app)
    
    # Get deployment environment and determine required services
    deployment_env = os.getenv("DEPLOYMENT_ENV", "development")
    required_services = _get_required_services_for_environment(deployment_env, service_name)
    
    log_info(f"🎯 Service '{service_name}' will require services: {required_services}")
    
    # Register the startup event that initializes everything
    async def startup_event():
        log_info(f"🚀 Initializing all infrastructure for {service_name}...")
        try:
            # Initialize connection manager with environment-specific requirements
            await connection_manager.initialize(required_services=required_services)
            
            # Verify critical connections are working
            if connection_manager.timescaledb:
                # Test the connection with proper SQLAlchemy text
                from sqlalchemy import text
                async with connection_manager.timescaledb() as test_session:
                    await test_session.execute(text("SELECT 1"))
                log_info("✅ TimescaleDB connection verified")
            
            # Perform health check and log status
            health_status = await connection_manager.health_check()
            log_info(f"📊 Service health status: {health_status}")
            
            # Set up app.state.connections with initialized connections
            app.state.connections = {
                "redis": connection_manager.redis,
                "mongodb": connection_manager.mongodb,
                "timescaledb": connection_manager.timescaledb,
                "timescaledb_sync": connection_manager.timescaledb_sync,
                "rabbitmq": connection_manager.rabbitmq,
            }
            
            # Store connection manager reference for easy access
            app.state.connection_manager = connection_manager
            
            log_info(f"✅ Infrastructure initialization complete for {service_name}")
            
        except Exception as e:
            log_exception(f"❌ Infrastructure initialization failed for {service_name}: {e}")
            raise

    # Register startup event with higher priority (runs first)
    app.add_event_handler("startup", startup_event)
    
    # Set up app.state.config immediately (this doesn't need async)
    app.state.config = {
        "common": config_loader.common_config,
        "private": config_loader.private_config,
    }
    
    log_info(f"🎯 Service '{service_name}' created and configured")
    return app


def _get_required_services_for_environment(deployment_env: str, service_name: str) -> List[str]:
    """
    Determine required services based on deployment environment and service type
    """
    # Service-specific requirements
    service_requirements: Dict[str, Dict[str, List[str]]] = {
        "trade_service": {
            "development": ["timescaledb"],
            "production": ["timescaledb", "redis", "rabbitmq"],
            "minimal": ["timescaledb"],
            "full": ["timescaledb", "redis", "rabbitmq", "mongodb"],
            "testing": [],
        },
        "ticker_service": {
            "development": ["timescaledb", "redis"],
            "production": ["timescaledb", "redis", "rabbitmq"],
            "minimal": ["timescaledb"],
            "full": ["timescaledb", "redis", "rabbitmq", "mongodb"],
            "testing": [],
        },
        "user_service": {
            "development": ["timescaledb"],
            "production": ["timescaledb", "redis"],
            "minimal": ["timescaledb"],
            "full": ["timescaledb", "redis", "mongodb"],
            "testing": [],
        }
    }
    
    # Default requirements if service not specifically configured
    default_requirements: Dict[str, List[str]] = {
        "development": ["timescaledb"],
        "production": ["timescaledb", "redis"],
        "minimal": ["timescaledb"],
        "full": ["timescaledb", "redis", "rabbitmq", "mongodb"],
        "testing": [],
    }
    
    # Get requirements for specific service or use defaults
    requirements = service_requirements.get(service_name, default_requirements)
    return requirements.get(deployment_env, requirements["development"])


async def stop_service(service_name: str) -> None:
    """
    Properly stop service and close all connections
    """
    log_info(f"🛑 Stopping service: {service_name}")
    try:
        await connection_manager.close()
        log_info(f"✅ Service {service_name} stopped successfully")
    except Exception as e:
        log_exception(f"❌ Error stopping service {service_name}: {e}")


async def restart_service(service_name: str) -> FastAPI:
    """
    Restart service by stopping and starting again
    """
    await stop_service(service_name)
    return start_service(service_name)


def get_service_health() -> Dict[str, Any]:
    """
    Get current service health status
    """
    import asyncio
    try:
        loop = asyncio.get_event_loop()
        return loop.run_until_complete(connection_manager.health_check())
    except Exception as e:
        return {"error": str(e), "status": "unavailable"}