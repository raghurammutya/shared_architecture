from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# In-memory SQLite database for testing (no persistence)
DATABASE_URL = "sqlite:///:memory:"

class MockTimescaleDBClient:
    def __init__(self):
        self.engine = create_engine(DATABASE_URL, echo=False)
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)

    def get_session(self):
        return self.SessionLocal()

    def close(self):
        self.engine.dispose()


# Singleton
_mock_timescaledb_client = MockTimescaleDBClient()

def get_timescaledb_session():
    return _mock_timescaledb_client.get_session()
