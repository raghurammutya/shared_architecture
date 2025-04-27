import os
import logging
import psycopg2
from sqlalchemy.orm import sessionmaker,Session
from sqlalchemy import create_engine
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.engine.url import URL
import asyncpg

logging.basicConfig(
 level=logging.INFO,
 format="%(asctime)s - %(levelname)s - %(message)s",
)
logging.getLogger('sqlalchemy.engine').setLevel(logging.WARNING)  # Enable SQLAlchemy logging
logging.getLogger('sqlalchemy.pool').setLevel(logging.WARNING)    # Enable connection pool logging

class TimescaleDBConnection:
  def __init__(self, config: dict):
    """
    Initialize TimescaleDB connection.

    Args:
    config (dict): Configuration dictionary.
    """
    self.config = config #.get("services", {}).get("TickerService", {})  # Adjust service name!
    if not self.config:
        raise ValueError("TimescaleDB configuration not found")
    self.engine = self._create_engine()
    #self.SessionLocal = self._create_session_maker()
    self.connected = self.engine is not None  # Track connection status
    logging.info(f"TimescaleDBConnection initialized with config: {self.config}")


  async def check_timescaledb_health():
      try:
          conn = await asyncpg.connect(
              user=os.getenv("POSTGRES_USER"),
              password=os.getenv("POSTGRES_PASSWORD"),
              database=os.getenv("POSTGRES_DB"),
              host=os.getenv("POSTGRES_HOST"),
              port=int(os.getenv("POSTGRES_PORT")),
          )
          await conn.execute("SELECT 1;")
          await conn.close()
          return {"status": "healthy"}
      except Exception as e:
          return {"status": "unhealthy", "error": str(e)}


  # def _create_engine(self):
  #   """
  #   Creates the SQLAlchemy engine, handling connection errors.
  #   """
  #   db_url = self._get_database_url()
  #   try:
  #     engine = create_engine(
  #       db_url,
  #       pool_size=int(self.config.get("pool_size", 10)),
  #       max_overflow=int(self.config.get("max_overflow", 5)),
  #       pool_timeout=int(self.config.get("pool_timeout", 30)),
  #       pool_recycle=int(self.config.get("pool_recycle", 1800)),
  #     )
  #     engine.connect()  # Try to connect immediately
  #     return engine
  #   except SQLAlchemyError as e:
  #     logging.error(f"Error connecting to TimescaleDB: {e}")
  #     return None  # Return None on failure

  def _create_session_maker(self):
    """
    Creates the SQLAlchemy session maker.
    """
    if self.engine:
      return sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
    else:
      return None

  def _get_database_url(self) -> str:
    """
    Constructs the database URL from configuration.
    """
    return (
      f"postgresql://{self.config.get('postgres_user')}:"
      f"{self.config.get('postgres_password')}@"
      f"{self.config.get('postgres_host')}:"
      f"{self.config.get('postgres_port')}/"
      f"{self.config.get('postgres_database')}"
      )

  def get_session(self):
    """
    Provides a database session if connected, otherwise None.
    """
    if self.engine:
      return Session(self.engine)
    else:
      logging.warning("TimescaleDB session requested, but connection is unavailable.")
      return None

  def is_connected(self):
    """
    Returns True if the connection is established, False otherwise.
    """
    return self.connected

  def close(self):
    """
    Closes the connection.
    """
    if self.engine:
      self.engine.dispose()  # Dispose of the engine
      logging.info("TimescaleDB connection closed.")
    
  def _create_engine(self):
      db_config = self.config #.get("services", {}).get("TickerService", {})
      if not db_config:
          raise ValueError("TimescaleDB configuration not found")

      host = db_config.get("postgres_host")
      port = db_config.get("postgres_port")
      user = db_config.get("postgres_user")
      password = db_config.get("postgres_password")
      database = db_config.get("postgres_database")

      if not all([host, port, user, password, database]):
          raise ValueError("Incomplete TimescaleDB configuration")
      url_str = f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{database}"
      # url = URL.create(
      #     "postgresql+psycopg2",
      #     username=user,
      #     password=password,
      #     host=host,
      #     port=port,
      #     database=database
      # )

      # Log the URL just before creating the engine
      logging.info(f"SQLAlchemy URL: {url_str}")

      engine = create_engine(url_str)
      return engine

  def get_engine(self):
      return self.engine