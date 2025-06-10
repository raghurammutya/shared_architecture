from fastapi import FastAPI
from shared_architecture.config.config_loader import ConfigLoader
from shared_architecture.utils.logging_utils import configure_logging, log_info
from shared_architecture.connections import (
    get_redis_client,
    get_timescaledb_session,
    get_rabbitmq_connection,
    get_mongo_client
)


async def initialize_all_connections() -> dict:
    return {
        "redis": get_redis_client(),
        "timescaledb": get_timescaledb_session(),
        "rabbitmq": get_rabbitmq_connection(),
        "mongodb": get_mongo_client(),
    }


async def close_all_connections(connections: dict) -> None:
    if redis := connections.get("redis"):
        await redis.close()
    if timescaledb := connections.get("timescaledb"):
        await timescaledb.close()
    if rabbitmq := connections.get("rabbitmq"):
        await rabbitmq.close()
    if mongodb := connections.get("mongodb"):
        await mongodb.close()


def start_service(service_name: str) -> FastAPI:
    """
    Complete service initialization that handles everything in one shot:
    1. FastAPI app creation
    2. Configuration loading  
    3. Logging setup
    4. Metrics setup
    5. Connection initialization
    6. App state setup with connections and config
    """
    from fastapi import FastAPI
    from shared_architecture.config import config_loader
    from shared_architecture.utils.logging_utils import configure_logging
    from shared_architecture.utils.prometheus_metrics import setup_metrics
    from shared_architecture.connections.connection_manager import connection_manager

    app = FastAPI(title=service_name)
    
    # Load configuration
    config_loader.load(service_name)
    
    # Setup logging
    configure_logging(service_name)
    
    # Setup metrics
    setup_metrics(app)
    
    # Register the startup event that initializes everything
    async def startup_event():
        log_info(f"🚀 Initializing all infrastructure for {service_name}...")
        try:
            # Initialize connection manager
            await connection_manager.initialize()
            
            # Verify connections are working
            if connection_manager.timescaledb:
                # Test the connection with proper SQLAlchemy text
                from sqlalchemy import text
                async with connection_manager.timescaledb() as test_session:
                    await test_session.execute(text("SELECT 1"))
                log_info("TimescaleDB connection verified")
            
            # Set up app.state.connections with initialized connections
            app.state.connections = {
                "redis": connection_manager.redis,
                "mongodb": connection_manager.mongodb,
                "timescaledb": connection_manager.timescaledb,
                "rabbitmq": connection_manager.rabbitmq,
            }
            
            log_info(f"✅ Infrastructure initialization complete for {service_name}")
            
        except Exception as e:
            log_info(f"❌ Infrastructure initialization failed for {service_name}: {e}")
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


def stop_service(service_name: str) -> None:
    log_info(f"Stopping service: {service_name}")


async def restart_service(service_name: str) -> FastAPI:
    stop_service(service_name)
    return start_service(service_name)