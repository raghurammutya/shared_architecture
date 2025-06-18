# shared_architecture/db/models/organization.py

from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Boolean, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from shared_architecture.db.base import Base

class Organization(Base):
    """
    Organization/Group model with API key management
    An organization represents a trading group with shared API access
    """
    __tablename__ = "organizations"
    __table_args__ = {'schema': 'tradingdb'}
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    
    # API Key management (hashed for security)
    api_key_hash = Column(String, unique=True, nullable=False, index=True)
    api_key_visible = Column(String, nullable=False)  # Only show first 8 and last 4 chars
    api_key_created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Ownership structure
    owner_id = Column(Integer, ForeignKey("tradingdb.users.id"), nullable=False, index=True)
    backup_owner_id = Column(Integer, ForeignKey("tradingdb.users.id"), nullable=True, index=True)
    
    # Status and timestamps
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    owner = relationship("User", foreign_keys=[owner_id], back_populates="owned_organizations")
    backup_owner = relationship("User", foreign_keys=[backup_owner_id], back_populates="backup_organizations")
    
    trading_accounts = relationship("TradingAccount", back_populates="organization", cascade="all, delete-orphan")
    account_permissions = relationship("TradingAccountPermission", back_populates="organization", cascade="all, delete-orphan")
    
    @property
    def total_accounts(self):
        """Get total number of trading accounts"""
        return len(self.trading_accounts)
    
    @property
    def active_accounts(self):
        """Get active trading accounts"""
        return [acc for acc in self.trading_accounts if acc.is_active]
    
    @property
    def masked_api_key(self):
        """Return masked API key for display"""
        return self.api_key_visible