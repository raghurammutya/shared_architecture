from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine

Base = declarative_base()
engine = create_engine("postgresql://user:password@localhost/dbname")  # Replace with your DB connection
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)