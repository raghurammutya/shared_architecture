
from sqlalchemy import create_engine, Column,Boolean, Integer, Float,String, Date, DateTime, ForeignKey, UniqueConstraint, Text
from sqlalchemy.ext.declarative import declarative_base
from shared_architecture.utils.custom_types import TimezoneAwareDateTime
Base = declarative_base()
class SymbolUpdateStatus(Base):
    __tablename__ = "symbols_update_status"
    broker_name = Column(String, primary_key=True)
    update_date = Column(TimezoneAwareDateTime(), primary_key=True)
    update_time = Column(TimezoneAwareDateTime())
    