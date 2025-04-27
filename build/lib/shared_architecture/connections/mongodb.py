import os
import logging
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure
import pymongo
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)

class MongoDBConnection:
    _client: MongoClient | None = None  # Class-level client

    def __init__(self, config: dict):
        """
        Initializes the MongoDB connection (or reuses existing).

        Args:
            config (dict): Configuration dictionary containing MongoDB settings.
        """
        self.config = config
        self.db = self._get_database()
        self.connected = self._client is not None  # Track connection status
        logging.info(f"MongoDBConnection initialized (or reused) with config: {self.config}")

    @classmethod
    def _get_client(cls, config: dict) -> MongoClient | None:
        """
        Gets or creates the MongoClient instance (singleton-like).
        """
        if cls._client is None:
            try:
                mongo_uri = config.get("mongo_uri")
                if mongo_uri:
                    cls._client = MongoClient(mongo_uri, serverSelectionTimeoutMS=5000)  # Add timeout
                else:
                    cls._client = MongoClient(
                        host=config.get("mongo_host", "localhost"),
                        port=config.get("mongo_port", 27017),
                        serverSelectionTimeoutMS=5000,
                    )
                    # Corrected: Build URI without username/password if they're not provided
                    # if config.get("mongo_user") and config.get("mongo_password"):
                    #     cls._client = MongoClient(
                    #         host=config.get("mongo_host"),
                    #         port=config.get("mongo_port"),
                    #         username=config.get("mongo_user","tradmin"),
                    #         password=config.get("mongo_password","tradpass"),
                    #         authSource=config.get("mongo_auth_source", "admin"),
                    #         serverSelectionTimeoutMS=5000,  # Add timeout
                    #     )
                    # else:
                    #     cls._client = MongoClient(
                    #         host=config.get("mongo_host", "localhost"),
                    #         port=config.get("mongo_port", 27017),
                    #         serverSelectionTimeoutMS=5000,
                    #     )

                cls._client.admin.command('ping')  # Test the connection
                logging.info("MongoDB connection successful.")
            except ConnectionFailure as e:
                logging.error(f"Error connecting to MongoDB: {e}")
                cls._client = None  # Set client to None on failure
        return cls._client


    def check_mongo_health():
        try:
            uri = f"mongodb://{os.getenv('MONGO_USER')}:{os.getenv('MONGO_PASSWORD')}@{os.getenv('MONGO_HOST')}:{os.getenv('MONGO_PORT')}/"
            client = pymongo.MongoClient(uri, serverSelectionTimeoutMS=2000)
            client.admin.command("ping")
            return {"status": "healthy"}
        except Exception as e:
            return {"status": "unhealthy", "error": str(e)}
    def _get_database(self):
        """
        Gets the MongoDB database instance.
        """
        client = self._get_client(self.config)
        if client:
            return client[self.config.get("mongo_database", "test")]  # Default to "test" DB
        else:
            return None

    def get_database(self):
        """
        Returns the MongoDB database instance (or None if not connected).
        """
        return self.db

    def is_connected(self):
        """
        Returns True if the connection is established, False otherwise.
        """
        return self.connected

    def close_connection(self):
        """
        Closes the MongoClient instance (if it was created here).
        """
        if self._client is not None:
            self._client.close()
            logging.info("MongoDB connection closed.")
            MongoDBConnection._client = None  # Reset the class-level client