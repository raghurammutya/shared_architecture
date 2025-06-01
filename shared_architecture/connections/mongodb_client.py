
from pymongo import MongoClient
from shared_architecture.config.config_loader import config_loader

env = config_loader.get("ENVIRONMENT", "dev").lower()
mongo_uri = "mongodb://localhost:27017" if env == "dev" else config_loader.get("MONGODB_URI")

def get_mongo_client():
    return MongoClient(mongo_uri)
