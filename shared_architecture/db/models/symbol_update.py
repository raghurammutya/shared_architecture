
from sqlalchemy import create_engine, Column,Boolean, Integer, Float,String, Date, DateTime, ForeignKey, UniqueConstraint, Text
from sqlalchemy.ext.declarative import declarative_base
from shared_architecture.db.base import Base
class SymbolUpdateStatus(Base):
    __tablename__ = "symbols_update_status"
    __table_args__ = {'schema': 'tradingdb'}
    broker_name = Column(String, primary_key=True)
    update_date = Column(DateTime(timezone=True), primary_key=True)
    update_time = Column(DateTime(timezone=True))
    