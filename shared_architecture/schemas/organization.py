# shared_architecture/schemas/organization.py

from pydantic import BaseModel, validator
from typing import List, Optional
from datetime import datetime

class OrganizationCreateSchema(BaseModel):
    name: str
    description: Optional[str] = None
    api_key: str
    backup_owner_id: Optional[int] = None
    
    @validator('name')
    def validate_name(cls, v):
        if not v or len(v.strip()) < 3:
            raise ValueError('Organization name must be at least 3 characters')
        return v.strip()
    
    @validator('api_key')
    def validate_api_key(cls, v):
        if not v or len(v.strip()) < 10:
            raise ValueError('API key must be at least 10 characters')
        return v.strip()

class OrganizationUpdateSchema(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    api_key: Optional[str] = None
    backup_owner_id: Optional[int] = None
    is_active: Optional[bool] = None
    
    @validator('name')
    def validate_name(cls, v):
        if v is not None and len(v.strip()) < 3:
            raise ValueError('Organization name must be at least 3 characters')
        return v.strip() if v else None

class OrganizationResponseSchema(BaseModel):
    id: int
    name: str
    description: Optional[str]
    masked_api_key: str
    owner_id: int
    backup_owner_id: Optional[int]
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime]
    total_accounts: int
    
    class Config:
        from_attributes = True

class TradingAccountImportSchema(BaseModel):
    """Schema for selecting trading accounts to import"""
    selected_login_ids: List[str]
    
    @validator('selected_login_ids')
    def validate_selection(cls, v):
        if not v:
            raise ValueError('At least one trading account must be selected')
        return v

class TradingAccountResponseSchema(BaseModel):
    id: int
    login_id: str
    pseudo_acc_name: str
    broker: str
    platform: str
    system_id: int
    system_id_of_pseudo_acc: int
    license_expiry_date: Optional[str]
    license_days_left: Optional[int]
    is_live: bool
    organization_id: int
    assigned_user_id: Optional[int]
    is_active: bool
    imported_at: datetime
    account_identifier: str
    is_license_expired: bool
    
    class Config:
        from_attributes = True

class TradingAccountAssignmentSchema(BaseModel):
    user_id: int
    trading_account_ids: List[int]
    
    @validator('trading_account_ids')
    def validate_accounts(cls, v):
        if not v:
            raise ValueError('At least one trading account must be specified')
        return v