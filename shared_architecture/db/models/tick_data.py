from sqlalchemy import Column, TIMESTAMP, Text, Double, BigInteger, Date,DateTime
from sqlalchemy.ext.declarative import declarative_base
from shared_architecture.db.base import Base

class TickData(Base):
    __tablename__ = 'tick_data'
    __table_args__ = {'schema': 'tradingdb'}
    time = Column(TIMESTAMP(timezone=True), primary_key=True, nullable=False)
    instrument_key = Column(Text, primary_key=True, nullable=False)
    interval = Column(Text, primary_key=True, nullable=False)

    open = Column(DateTime(timezone=True))
    high = Column(DateTime(timezone=True))
    low = Column(DateTime(timezone=True))
    close = Column(DateTime(timezone=True))
    volume = Column(BigInteger)
    oi = Column(BigInteger)
    expirydate = Column(DateTime(timezone=True))
    option_type = Column(Text)
    strikeprice = Column(Double)
    
    # Greeks data columns
    greeks_open_IV = Column(Double)
    greeks_open_delta = Column(Double)
    greeks_open_gamma = Column(Double)
    greeks_open_theta = Column(Double)
    greeks_open_rho = Column(Double)
    greeks_open_vega = Column(Double)

    greeks_high_IV = Column(Double)
    greeks_high_delta = Column(Double)
    greeks_high_gamma = Column(Double)
    greeks_high_theta = Column(Double)
    greeks_high_rho = Column(Double)
    greeks_high_vega = Column(Double)

    greeks_low_IV = Column(Double)
    greeks_low_delta = Column(Double)
    greeks_low_gamma = Column(Double)
    greeks_low_theta = Column(Double)
    greeks_low_rho = Column(Double)
    greeks_low_vega = Column(Double)

    greeks_close_IV = Column(Double)
    greeks_close_delta = Column(Double)
    greeks_close_gamma = Column(Double)
    greeks_close_theta = Column(Double)
    greeks_close_rho = Column(Double)
    greeks_close_vega = Column(Double)