# shared_architecture/db/models/position_model.py

from sqlalchemy import Column, Integer, Float, String, DateTime, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

from shared_architecture.db.base import Base

class PositionModel(Base):
    __tablename__ = 'positions'
    __table_args__ = {'schema': 'tradingdb'}  # Add schema specification
    
    id = Column(Integer, primary_key=True)
    account_id = Column(String)
    atPnl = Column(Float, name='atpnl')# Keep the original column name
    buy_avg_price = Column(Float)
    buy_quantity = Column(Integer)
    buy_value = Column(Float)
    category = Column(String)
    direction = Column(String)
    exchange = Column(String)
    independent_exchange = Column(String, nullable=True)
    independent_symbol = Column(String, nullable=True)
    ltp = Column(Float)
    mtm = Column(Float)
    multiplier = Column(Integer)
    net_quantity = Column(Integer)
    net_value = Column(Float)
    overnight_quantity = Column(Integer)
    platform = Column(String)
    pnl = Column(Float)
    pseudo_account = Column(String)
    realised_pnl = Column(Float)
    sell_avg_price = Column(Float)
    sell_quantity = Column(Integer)
    sell_value = Column(Float)
    state = Column(String)
    stock_broker = Column(String)
    symbol = Column(String)
    trading_account = Column(String)
    type = Column(String)
    unrealised_pnl = Column(Float)
    timestamp = Column(DateTime(timezone=True), default=datetime.utcnow)
    instrument_key = Column(String, ForeignKey('tradingdb.symbols.instrument_key'))  # Add schema to FK
    strategy_id = Column(String)
    source_strategy_id = Column(String, nullable=True)
    
    # Add property to access atPnl as at_pnl for compatibility
    @property
    def at_pnl(self):
        return self.atPnl
    
    @at_pnl.setter
    def at_pnl(self, value):
        self.atPnl = value