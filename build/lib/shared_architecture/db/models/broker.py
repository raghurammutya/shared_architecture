from sqlalchemy import create_engine, Column,Boolean, Integer, Float,String, Date, DateTime, ForeignKey, UniqueConstraint, Text
from sqlalchemy.ext.declarative import declarative_base
import datetime 
from shared_architecture.utils.custom_types import TimezoneAwareDateTime
Base = declarative_base()

class Broker(Base):
    __tablename__ = 'brokers'
    __table_args__ = {'schema': 'tradingdb'}  
    id = Column(Integer, primary_key=True)
    broker_name = Column(Text)
    login_url = Column(Text)
    api_key = Column(Text)
    api_secret = Column(Text)
    username = Column(Text)
    password = Column(Text)
    totp_key = Column(Text)
    session_key = Column(Text)
    session_key_date = Column(TimezoneAwareDateTime())
    symbol_url = Column(Text)
    status = Column(Text)
    session_starttime = Column(TimezoneAwareDateTime()) # Using DateTime for precise time
    session_token = Column(Text)
    live_status = Column(Text)
    subscription_limit = Column(Integer)
    daily_api_limit = Column(Integer)
    minute_api_limit = Column(Integer)
    records_per_api_requests = Column(Integer)
    last_api_call_time = Column(TimezoneAwareDateTime(), default=datetime.datetime.now)
    minute_api_requests = Column(Integer, default=0)

    # Unique constraint
    __table_args__ = (UniqueConstraint('broker_name', 'username', name='uix_broker_username'),)


    def __repr__(self):
        return f"<Broker(broker_name='{self.broker_name}', username='{self.username}')>"