# shared_architecture/schemas/trading_account_permission.py

from pydantic import BaseModel, validator
from typing import List, Optional
from datetime import datetime
from ..db.models.trading_account_permission import PermissionType

class TradingAccountPermissionCreateSchema(BaseModel):
    user_id: int
    trading_account_id: int
    permission_type: PermissionType
    expires_at: Optional[datetime] = None
    notes: Optional[str] = None
    
    @validator('notes')
    def validate_notes(cls, v):
        if v and len(v) > 500:
            raise ValueError('Notes cannot exceed 500 characters')
        return v

class TradingAccountPermissionUpdateSchema(BaseModel):
    permission_type: Optional[PermissionType] = None
    expires_at: Optional[datetime] = None
    is_active: Optional[bool] = None
    notes: Optional[str] = None
    
    @validator('notes')
    def validate_notes(cls, v):
        if v and len(v) > 500:
            raise ValueError('Notes cannot exceed 500 characters')
        return v

class TradingAccountPermissionResponseSchema(BaseModel):
    id: int
    user_id: int
    trading_account_id: int
    organization_id: int
    permission_type: PermissionType
    granted_by_id: int
    granted_at: datetime
    expires_at: Optional[datetime]
    is_active: bool
    revoked_at: Optional[datetime]
    revoked_by_id: Optional[int]
    notes: Optional[str]
    is_expired: bool
    is_valid: bool
    
    class Config:
        from_attributes = True

class BulkPermissionGrantSchema(BaseModel):
    """Schema for granting permissions to multiple users for multiple accounts"""
    user_ids: List[int]
    trading_account_ids: List[int]
    permission_types: List[PermissionType]
    expires_at: Optional[datetime] = None
    notes: Optional[str] = None
    
    @validator('user_ids')
    def validate_users(cls, v):
        if not v:
            raise ValueError('At least one user must be specified')
        return v
    
    @validator('trading_account_ids')
    def validate_accounts(cls, v):
        if not v:
            raise ValueError('At least one trading account must be specified')
        return v
    
    @validator('permission_types')
    def validate_permissions(cls, v):
        if not v:
            raise ValueError('At least one permission type must be specified')
        return v