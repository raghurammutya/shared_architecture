from motor.motor_asyncio import AsyncIOMotorClient
from shared_architecture.config.config_loader import config_loader


def get_mongo_client() -> AsyncIOMotorClient:
    mongo_host = config_loader.get("MONGODB_HOST", "mongo", scope="common")
    mongo_port = config_loader.get("MONGODB_PORT", 27017, scope="common")
    mongo_user = config_loader.get("MONGODB_USER", None, scope="common")
    mongo_password = config_loader.get("MONGODB_PASSWORD", None, scope="common")
    mongo_auth_source = config_loader.get("MONGODB_AUTH_SOURCE", "admin", scope="common")

    if mongo_user and mongo_password:
        uri = f"mongodb://{mongo_user}:{mongo_password}@{mongo_host}:{mongo_port}/?authSource={mongo_auth_source}"
    else:
        uri = f"mongodb://{mongo_host}:{mongo_port}"

    return AsyncIOMotorClient(uri)
