# shared_architecture/db/models/margin_model.py

from sqlalchemy import UniqueConstraint, Column, Integer, Float, String, Boolean, DateTime, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from shared_architecture.db.base import Base

class MarginModel(Base):
    __tablename__ = 'margins'
    __table_args__ = (
        UniqueConstraint('pseudo_account', 'category', 'margin_date'),
        {'schema': 'tradingdb'}  # Add schema specification
    )
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('tradingdb.users.id'))  # Add schema to FK
    adhoc = Column(Float)
    available = Column(Float)
    category = Column(String)
    collateral = Column(Float)
    exposure = Column(Float)
    funds = Column(Float)
    net = Column(Float)
    payin = Column(Float)
    payout = Column(Float)
    pseudo_account = Column(String)
    realised_mtm = Column(Float)
    span = Column(Float)
    stock_broker = Column(String)
    total = Column(Float)
    trading_account = Column(String)
    unrealised_mtm = Column(Float)
    utilized = Column(Float)
    active = Column(Boolean, default=True)
    margin_date = Column(DateTime(timezone=True))
    # instrument_key removed - margins are account-level, not instrument-specific