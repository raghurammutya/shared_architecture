import os

# Import Real or Mock Clients Based on USE_MOCKS
USE_MOCKS = os.getenv("USE_MOCKS", "false").lower() == "true"

if USE_MOCKS:
    from shared_architecture.mocks import (
        redis_client as redis_mod,
        timescaledb_client as tsdb_mod,
        rabbitmq_client as rabbitmq_mod,
        mongodb_client as mongo_mod,
    )
else:
    from shared_architecture.connections import (
        redis_client as redis_mod,
        timescaledb_client as tsdb_mod,
        rabbitmq_client as rabbitmq_mod,
        mongodb_client as mongo_mod,
    )


class ConnectionManager:
    def __init__(self):
        self.redis_client = redis_mod.get_redis_client()
        self.timescaledb_client = tsdb_mod
        self.rabbitmq_client = rabbitmq_mod.get_rabbitmq_client()
        self.mongo_client = mongo_mod.get_mongo_client()

    def get_all_connections(self):
        """
        Returns all connections as a dictionary.
        """
        return {
            "redis": self.redis_client,
            "timescaledb": self.timescaledb_client,
            "rabbitmq": self.rabbitmq_client,
            "mongodb": self.mongo_client,
        }
    def _check_timescaledb(self):
        try:
            with self.create_timescaledb_session() as session:
                session.execute("SELECT 1")
            return True
        except Exception:
            return False

    def _check_rabbitmq(self):
        return self.rabbitmq_client.connection.is_open

    def _check_mongodb(self):
        try:
            self.mongo_client.db.command('ping')
            return True
        except Exception:
            return False
    def create_timescaledb_session(self):
        """
        Returns a SQLAlchemy session from the TimescaleDB client.
        """
        return self.timescaledb_client.get_timescaledb_session()

    def shutdown_connections(self):
        """
        Safely closes all connection resources.
        """
        if hasattr(self.redis_client, 'close'):
            self.redis_client.close()
        if hasattr(self.rabbitmq_client, 'close'):
            self.rabbitmq_client.close()
        if hasattr(self.mongo_client, 'close'):
            self.mongo_client.close()
        # TimescaleDB engine does not need shutdown per session, managed per session lifecycle

    def health_check(self):
        return {
            "redis": self.redis_client.health_check(),
            "timescaledb": self._check_timescaledb(),
            "rabbitmq": self._check_rabbitmq(),
            "mongodb": self._check_mongodb()
        }
# Singleton instance
connection_manager = ConnectionManager()
