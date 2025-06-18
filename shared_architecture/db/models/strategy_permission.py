# shared_architecture/db/models/strategy_permission.py

from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Boolean, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from shared_architecture.db.base import Base
import enum

class StrategyPermissionType(enum.Enum):
    """Types of permissions for strategy access"""
    
    # READ PERMISSIONS
    VIEW_STRATEGY = "view_strategy"                    # View strategy details
    VIEW_POSITIONS = "view_positions"                  # View strategy positions
    VIEW_ORDERS = "view_orders"                        # View strategy orders  
    VIEW_HOLDINGS = "view_holdings"                    # View strategy holdings
    VIEW_MARGINS = "view_margins"                      # View strategy margins
    VIEW_PNL = "view_pnl"                             # View strategy P&L
    VIEW_ANALYTICS = "view_analytics"                  # View strategy analytics
    
    # STRATEGY MANAGEMENT PERMISSIONS
    MODIFY_STRATEGY = "modify_strategy"                # Modify strategy parameters
    START_STRATEGY = "start_strategy"                  # Start/activate strategy
    PAUSE_STRATEGY = "pause_strategy"                  # Pause strategy
    STOP_STRATEGY = "stop_strategy"                    # Stop strategy
    SQUARE_OFF_STRATEGY = "square_off_strategy"        # Square off all strategy positions
    DELETE_STRATEGY = "delete_strategy"                # Delete strategy
    
    # TRADING PERMISSIONS WITHIN STRATEGY
    PLACE_ORDERS = "place_orders"                      # Place orders within strategy
    MODIFY_ORDERS = "modify_orders"                    # Modify strategy orders
    CANCEL_ORDERS = "cancel_orders"                    # Cancel strategy orders
    SQUARE_OFF_POSITIONS = "square_off_positions"      # Square off individual positions
    
    # RISK MANAGEMENT PERMISSIONS
    SET_RISK_LIMITS = "set_risk_limits"               # Set strategy risk limits
    OVERRIDE_RISK_LIMITS = "override_risk_limits"     # Override strategy risk limits
    
    # ADMINISTRATIVE PERMISSIONS
    MANAGE_STRATEGY_PERMISSIONS = "manage_strategy_permissions"  # Grant/revoke strategy access
    FULL_STRATEGY_ACCESS = "full_strategy_access"     # All strategy permissions

class StrategyPermission(Base):
    """
    Fine-grained permissions for users to access specific strategies
    Allows strategy-level access control within trading accounts
    """
    __tablename__ = "strategy_permissions"
    __table_args__ = {'schema': 'tradingdb'}
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Core relationships
    user_id = Column(Integer, ForeignKey("tradingdb.users.id"), nullable=False, index=True)
    strategy_id = Column(Integer, ForeignKey("tradingdb.strategies.id"), nullable=False, index=True)
    trading_account_id = Column(Integer, ForeignKey("tradingdb.trading_accounts.id"), nullable=False, index=True)
    organization_id = Column(Integer, ForeignKey("tradingdb.organizations.id"), nullable=False, index=True)
    
    # Permission details
    permission_type = Column(Enum(StrategyPermissionType), nullable=False)
    
    # Grant details
    granted_by_id = Column(Integer, ForeignKey("tradingdb.users.id"), nullable=False)
    granted_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=True)
    
    # Status
    is_active = Column(Boolean, default=True, nullable=False)
    revoked_at = Column(DateTime(timezone=True), nullable=True)
    revoked_by_id = Column(Integer, ForeignKey("tradingdb.users.id"), nullable=True)
    
    # Additional metadata
    notes = Column(String, nullable=True)
    
    # Relationships
    user = relationship("User", foreign_keys=[user_id])
    strategy = relationship("Strategy", back_populates="permissions")
    trading_account = relationship("TradingAccount")
    organization = relationship("Organization")
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