from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime, date
from decimal import Decimal
from shared_architecture.enums import ChargeCategory, TransactionType, BrokerName

class LedgerEntrySchema(BaseModel):
    id: Optional[int] = None
    pseudo_account: str
    transaction_date: date
    posting_date: Optional[date] = None
    transaction_type: TransactionType
    particulars: str
    debit_amount: Optional[float] = 0.0
    credit_amount: Optional[float] = 0.0
    net_balance: Optional[float] = None
    cost_center: Optional[str] = None
    voucher_type: Optional[str] = None
    charge_category: Optional[ChargeCategory] = None
    charge_subcategory: Optional[str] = None
    exchange: Optional[str] = None
    segment: Optional[str] = None
    broker_name: BrokerName
    source_file: Optional[str] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class LedgerUploadResponse(BaseModel):
    total_entries: int
    processed_entries: int
    skipped_entries: int
    date_range: dict
    message: str