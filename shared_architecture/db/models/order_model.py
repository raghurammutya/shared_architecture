# shared_architecture/db/models/order_model.py

from sqlalchemy import Column, Integer, Float, String, Boolean, DateTime, ForeignKey
from shared_architecture.db.base import Base
from datetime import datetime
from sqlalchemy.ext.declarative import declared_attr

class OrderModel(Base):
    __tablename__ = 'orders'
    __table_args__ = {'schema': 'tradingdb'}  # Add schema specification
    
    id = Column(Integer, primary_key=True)
    amo = Column(Boolean)
    average_price = Column(Float)
    client_id = Column(String)
    disclosed_quantity = Column(Integer)
    exchange = Column(String)
    exchange_order_id = Column(String)
    exchange_time = Column(DateTime(timezone=True))
    filled_quantity = Column(Integer)
    independent_exchange = Column(String, nullable=True)
    independent_symbol = Column(String, nullable=True)
    modified_time = Column(DateTime(timezone=True), nullable=True)
    nest_request_id = Column(String, nullable=True)
    order_type = Column(String)
    parent_order_id = Column(Integer, nullable=True)
    pending_quantity = Column(Integer)
    platform = Column(String)
    platform_time = Column(DateTime(timezone=True))
    price = Column(Float)
    pseudo_account = Column(String)
    publisher_id = Column(String, nullable=True)
    status = Column(String)
    status_message = Column(String, nullable=True)
    stock_broker = Column(String)
    symbol = Column(String)
    trade_type = Column(String)
    trading_account = Column(String)
    trigger_price = Column(Float, nullable=True)
    validity = Column(String)
    variety = Column(String, nullable=False)
    timestamp = Column(DateTime(timezone=True), default=datetime.utcnow)
    instrument_key = Column(String, ForeignKey('tradingdb.symbols.instrument_key'))  # Add schema to FK
    strategy_id = Column(String)
    transition_type = Column(String, default='NONE')
    
    # Required fields
    quantity = Column(Integer, nullable=False)
    product_type = Column(String)
    target = Column(Float, nullable=True)
    stoploss = Column(Float, nullable=True)
    trailing_stoploss = Column(Float, nullable=True)
    position_category = Column(String, nullable=True)
    position_type = Column(String, nullable=True)
    comments = Column(String, nullable=True)
    
    def to_dict(self):
        """Convert OrderModel instance to dictionary for JSON serialization"""
        result = {}
        
        # Basic fields that are always present
        basic_fields = [
            'id', 'amo', 'average_price', 'client_id', 'disclosed_quantity',
            'exchange', 'exchange_order_id', 'filled_quantity', 'independent_exchange',
            'independent_symbol', 'nest_request_id', 'order_type', 'parent_order_id',
            'pending_quantity', 'platform', 'price', 'pseudo_account', 'publisher_id',
            'status', 'status_message', 'stock_broker', 'symbol', 'trade_type',
            'trading_account', 'trigger_price', 'validity', 'variety',
            'instrument_key', 'strategy_id', 'quantity'
        ]
        
        for field in basic_fields:
            if hasattr(self, field):
                value = getattr(self, field)
                result[field] = value
        
        # Handle datetime fields specially
        datetime_fields = ['exchange_time', 'modified_time', 'platform_time', 'timestamp']
        for field in datetime_fields:
            if hasattr(self, field):
                value = getattr(self, field)
                result[field] = value.isoformat() if value else None
        
        # Handle optional fields that might not exist
        optional_fields = [
            'target', 'stoploss', 'trailing_stoploss', 'position_category',
            'position_type', 'comments', 'transition_type'
        ]
        
        for field in optional_fields:
            if hasattr(self, field):
                value = getattr(self, field)
                if value is not None:
                    result[field] = str(value) if hasattr(value, '__str__') else value
        
        return result