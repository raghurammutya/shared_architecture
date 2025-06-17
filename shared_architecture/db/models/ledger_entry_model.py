from sqlalchemy import Column, Integer, Float, String, Date, DateTime, Text, DECIMAL
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime
from sqlalchemy import Column, Integer, Float, String, Date, DateTime, Text, Enum
from shared_architecture.enums import ChargeCategory, TransactionType, BrokerName
from shared_architecture.db.base import Base

class LedgerEntryModel(Base):
    __tablename__ = 'ledger_entries'
    __table_args__ = {'schema': 'tradingdb'}
    
    id = Column(Integer, primary_key=True)
    pseudo_account = Column(String, nullable=False)
    
    # Core Transaction Details
    transaction_date = Column(Date, nullable=False)
    posting_date = Column(Date)
    transaction_type = Column(Enum(TransactionType), nullable=False)
    particulars = Column(Text, nullable=False)
    
    # Financial Impact
    debit_amount = Column(Float, default=0.0)
    credit_amount = Column(Float, default=0.0)
    net_balance = Column(Float)
    
    # Categorization
    cost_center = Column(String)
    voucher_type = Column(String)
    charge_category = Column(Enum(ChargeCategory))
    charge_subcategory = Column(String)
    
    # Reference Data
    reference_order_id = Column(String)
    reference_trade_id = Column(String)
    exchange = Column(String)
    segment = Column(String)
    
    # Broker Specific
    broker_name = Column(Enum(BrokerName), nullable=False)
    broker_reference = Column(String)
    
    # Source & Processing
    source_file = Column(String)
    raw_data = Column(Text)  # Store as JSON string
    processed_at = Column(DateTime, default=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)