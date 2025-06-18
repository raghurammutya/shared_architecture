# shared_architecture/db/models/trading_account_permission.py

from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Boolean, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from shared_architecture.db.base import Base
import enum

class PermissionType(enum.Enum):
    """Types of permissions for trading account access"""
    
    # READ PERMISSIONS
    VIEW_POSITIONS = "view_positions"
    VIEW_ORDERS = "view_orders"
    VIEW_TRADES = "view_trades"
    VIEW_BALANCE = "view_balance"
    VIEW_PNL = "view_pnl"
    VIEW_ANALYTICS = "view_analytics"
    VIEW_STRATEGIES = "view_strategies"
    VIEW_PORTFOLIO = "view_portfolio"
    FULL_READ = "full_read"  # All view permissions
    
    # ORDER MANAGEMENT PERMISSIONS
    PLACE_ORDERS = "place_orders"           # Create new orders
    MODIFY_ORDERS = "modify_orders"         # Modify existing orders
    CANCEL_ORDERS = "cancel_orders"         # Cancel pending orders
    SQUARE_OFF_POSITIONS = "square_off_positions"  # Close positions
    
    # STRATEGY MANAGEMENT PERMISSIONS
    CREATE_STRATEGY = "create_strategy"     # Create new strategies
    MODIFY_STRATEGY = "modify_strategy"     # Modify existing strategies
    ADJUST_STRATEGY = "adjust_strategy"     # Adjust strategy parameters
    SQUARE_OFF_STRATEGY = "square_off_strategy"  # Close entire strategy
    DELETE_STRATEGY = "delete_strategy"     # Delete strategies
    
    # PORTFOLIO MANAGEMENT PERMISSIONS
    SQUARE_OFF_PORTFOLIO = "square_off_portfolio"  # Close entire portfolio
    MANAGE_PORTFOLIO = "manage_portfolio"   # Full portfolio management
    
    # RISK MANAGEMENT PERMISSIONS
    SET_RISK_LIMITS = "set_risk_limits"     # Set position/loss limits
    OVERRIDE_RISK_LIMITS = "override_risk_limits"  # Override risk controls
    
    # BULK OPERATIONS
    BULK_OPERATIONS = "bulk_operations"     # Mass operations across positions
    
    # ADMINISTRATIVE PERMISSIONS
    FULL_TRADING = "full_trading"           # All trading permissions
    ADMIN_TRADING = "admin_trading"         # All permissions including admin

class TradingAccountPermission(Base):
    """
    Fine-grained permissions for users to access specific trading account data
    Allows organization owners to grant specific users access to specific accounts
    """
    __tablename__ = "trading_account_permissions"
    __table_args__ = {'schema': 'tradingdb'}
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Core relationships
    user_id = Column(Integer, ForeignKey("tradingdb.users.id"), nullable=False, index=True)
    trading_account_id = Column(Integer, ForeignKey("tradingdb.trading_accounts.id"), nullable=False, index=True)
    organization_id = Column(Integer, ForeignKey("tradingdb.organizations.id"), nullable=False, index=True)
    
    # Permission details
    permission_type = Column(Enum(PermissionType), nullable=False)
    
    # Grant details
    granted_by_id = Column(Integer, ForeignKey("tradingdb.users.id"), nullable=False)  # Who granted this permission
    granted_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=True)  # Optional expiration
    
    # Status
    is_active = Column(Boolean, default=True, nullable=False)
    revoked_at = Column(DateTime(timezone=True), nullable=True)
    revoked_by_id = Column(Integer, ForeignKey("tradingdb.users.id"), nullable=True)
    
    # Additional metadata
    notes = Column(String, nullable=True)  # Why was this permission granted
    
    # Relationships
    user = relationship("User", foreign_keys=[user_id], back_populates="trading_account_permissions")
    trading_account = relationship("TradingAccount", back_populates="permissions")
    organization = relationship("Organization", back_populates="account_permissions")
    granted_by = relationship("User", foreign_keys=[granted_by_id])
    revoked_by = relationship("User", foreign_keys=[revoked_by_id])
    
    @property
    def is_expired(self):
        """Check if permission has expired"""
        if not self.expires_at:
            return False
        return func.now() > self.expires_at
    
    @property
    def is_valid(self):
        """Check if permission is currently valid"""
        return self.is_active and not self.is_expired and not self.revoked_at