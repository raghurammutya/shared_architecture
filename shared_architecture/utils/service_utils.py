from fastapi import FastAPI
from shared_architecture.config.config_loader import ConfigLoader
from shared_architecture.utils.logging_utils import configure_logging, log_info
from shared_architecture.connections import (
    get_redis_client,
    get_timescaledb_session,
    get_rabbitmq_client,
    get_mongo_client,
    RedisClusterClient,
    TimescaleDBClient,
    RabbitMQClient,
    MongoDBClient,
)


async def initialize_all_connections() -> dict:
    return {
        "redis": get_redis_client(),
        "timescaledb": get_timescaledb_session(),
        "rabbitmq": get_rabbitmq_client(),
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
    config_loader = ConfigLoader(service_name)
    configure_logging(service_name)
    log_info(f"Starting service: {service_name}")

    app = FastAPI(
        title=config_loader.config.get("PROJECT_NAME", service_name),
        openapi_url=f"{config_loader.config.get('API_V1_STR', '/api/v1')}/openapi.json"
    )
    app.state.settings = config_loader.config

    async def on_startup():
        app.state.connections = await initialize_all_connections()
        log_info("Connections initialized successfully.")

    async def on_shutdown():
        await close_all_connections(app.state.connections)
        log_info("Connections closed successfully.")

    app.add_event_handler("startup", on_startup)
    app.add_event_handler("shutdown", on_shutdown)

    return app


def stop_service(service_name: str) -> None:
    log_info(f"Stopping service: {service_name}")


def restart_service(service_name: str) -> FastAPI:
    stop_service(service_name)
    return start_service(service_name)
