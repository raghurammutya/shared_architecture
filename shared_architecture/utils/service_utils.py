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
    from fastapi import FastAPI
    from shared_architecture.config import config_loader
    from shared_architecture.utils.logging_utils import configure_logging
    from shared_architecture.utils.prometheus_metrics import setup_metrics
    from shared_architecture.connections.connection_manager import connection_manager

    app = FastAPI(title=service_name)
    config_loader.load(service_name)
    configure_logging(service_name)
    setup_metrics(app)
    # Await connection initialization
    async def startup_event():
        await connection_manager.initialize()

    app.add_event_handler("startup", startup_event)

    app.state.connections = {
        "redis": connection_manager.redis,
        "mongodb": connection_manager.mongodb,
        "timescaledb": connection_manager.timescaledb,
        "rabbitmq": connection_manager.rabbitmq,
    }
    return app


def stop_service(service_name: str) -> None:
    log_info(f"Stopping service: {service_name}")


async def restart_service(service_name: str) -> FastAPI:
    stop_service(service_name)
    return start_service(service_name)
