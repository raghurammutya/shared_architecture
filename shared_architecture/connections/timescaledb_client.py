
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from shared_architecture.config.config_loader import config_loader

env = config_loader.get("ENVIRONMENT", "dev").lower()
db_host = "localhost" if env == "dev" else config_loader.get("TIMESCALEDB_HOST", "timescaledb")
db_port = config_loader.get("TIMESCALEDB_PORT", 5432)
db_name = config_loader.get("POSTGRES_DB", "stocksblitz")
db_user = config_loader.get("POSTGRES_USER", "postgres")
db_pass = config_loader.get("POSTGRES_PASSWORD", "password")

DATABASE_URL = f"postgresql://{db_user}:{db_pass}@{db_host}:{db_port}/{db_name}"
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_timescaledb_session():
    return SessionLocal()
