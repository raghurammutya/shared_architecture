from sqlalchemy import Column, Integer, String, ForeignKey, Enum
from sqlalchemy.orm import relationship
from .group import Group
from shared_architecture.db.base import Base
from shared_architecture.enums import UserRole


class User(Base):
    __tablename__ = "users" # type: ignore
    __table_args__ = {'schema': 'tradingdb'}
    id = Column(Integer, primary_key=True, index=True)
    first_name = Column(String)
    last_name = Column(String)
    email = Column(String, unique=True)
    phone_number = Column(String, unique=True)
    group_id = Column(Integer, ForeignKey("tradingdb.groups.id"))
    group = relationship("Group", back_populates="members", foreign_keys=[group_id])
    role = Column(Enum(UserRole), default=UserRole.VIEWER)
    
    # Legacy trading accounts relationship (for backward compatibility)
    trading_accounts = relationship("TradingAccount", back_populates="user")
    
    # New organization and trading account relationships
    owned_organizations = relationship("Organization", foreign_keys="Organization.owner_id", back_populates="owner")
    backup_organizations = relationship("Organization", foreign_keys="Organization.backup_owner_id", back_populates="backup_owner")
    assigned_trading_accounts = relationship("TradingAccount", back_populates="assigned_user")
    trading_account_permissions = relationship("TradingAccountPermission", foreign_keys="TradingAccountPermission.user_id", back_populates="user")
    
    @property
    def accessible_trading_accounts(self):
        """Get all trading accounts this user can access (owned + permitted)"""
        accounts = list(self.assigned_trading_accounts)
        
        # Add accounts with explicit permissions
        for permission in self.trading_account_permissions:
            if permission.is_valid and permission.trading_account not in accounts:
                accounts.append(permission.trading_account)
        
        return accounts
    
    @property
    def is_organization_owner(self):
        """Check if user owns any organizations"""
        return len(self.owned_organizations) > 0
    
    @property
    def is_organization_backup_owner(self):
        """Check if user is backup owner of any organizations"""
        return len(self.backup_organizations) > 0
