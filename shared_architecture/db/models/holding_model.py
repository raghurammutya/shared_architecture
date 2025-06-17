# shared_architecture/db/models/holding_model.py

from sqlalchemy import Column, Integer, Float, String, DateTime, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime
from shared_architecture.db.base import Base

class HoldingModel(Base):
    __tablename__ = 'holdings'
    __table_args__ = {'schema': 'tradingdb'}  # Add schema specification
    
    id = Column(Integer, primary_key=True)
    pseudo_account = Column(String)
    trading_account = Column(String)
    exchange = Column(String)
    symbol = Column(String)
    quantity = Column(Integer)
    product = Column(String)
    isin = Column(String)
    collateral_qty = Column(Integer)
    t1_qty = Column(Integer)
    collateral_type = Column(String)
    pnl = Column(Float)
    haircut = Column(Float)
    avg_price = Column(Float)
    instrument_token = Column(Integer)
    stock_broker = Column(String)
    platform = Column(String)
    ltp = Column(Float)
    
    # Fix column names to match database (lowercase)
    current_value = Column(Float, name='currentvalue')  # Database has lowercase
    total_qty = Column(Integer, name='totalqty')        # Database has lowercase
    
    timestamp = Column(DateTime(timezone=True), default=datetime.utcnow)
    instrument_key = Column(String, ForeignKey('tradingdb.symbols.instrument_key'))  # Add schema to FK
    strategy_id = Column(String)
    source_strategy_id = Column(String, nullable=True)