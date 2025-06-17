from sqlalchemy import Column, Integer, String, DateTime, Text, Float, Boolean, JSON
from sqlalchemy.sql import func
from shared_architecture.db.base import Base
from shared_architecture.enums import StrategyStatus, StrategyType

class StrategyModel(Base):
    __tablename__ = 'strategies'
    __table_args__ = {'schema': 'tradingdb'}
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    strategy_id = Column(String(50), nullable=False, unique=True, index=True)
    strategy_name = Column(String(200), nullable=False)
    pseudo_account = Column(String(100), nullable=False, index=True)
    organization_id = Column(String(100), nullable=False, index=True)
    
    # Strategy Configuration
    strategy_type = Column(String(50), nullable=False, default=StrategyType.MANUAL.value)
    status = Column(String(20), nullable=False, default=StrategyStatus.ACTIVE.value)
    description = Column(Text)
    
    # Risk Management
    max_loss_amount = Column(Float, default=0.0)
    max_profit_amount = Column(Float, default=0.0)
    max_positions = Column(Integer, default=10)
    
    # Strategy Metadata
    tags = Column(JSON, default=list)  # List of tags for categorization
    configuration = Column(JSON, default=dict)  # Strategy-specific config
    
    # Performance Tracking
    total_pnl = Column(Float, default=0.0)
    realized_pnl = Column(Float, default=0.0)
    unrealized_pnl = Column(Float, default=0.0)
    total_margin_used = Column(Float, default=0.0)
    
    # Counts
    active_positions_count = Column(Integer, default=0)
    total_orders_count = Column(Integer, default=0)
    active_orders_count = Column(Integer, default=0)
    holdings_count = Column(Integer, default=0)
    
    # Auto Square-off Settings
    auto_square_off_enabled = Column(Boolean, default=False)
    square_off_time = Column(String(8))  # Format: "15:20:00"
    
    # Audit Fields
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)
    created_by = Column(String(100))
    last_modified_by = Column(String(100))
    
    # Strategy Lifecycle
    started_at = Column(DateTime)
    ended_at = Column(DateTime)
    squared_off_at = Column(DateTime)
    
    def __repr__(self):
        return f"<Strategy(id={self.strategy_id}, name={self.strategy_name}, status={self.status})>"
    
    def to_dict(self):
        return {
            'strategy_id': self.strategy_id,
            'strategy_name': self.strategy_name,
            'pseudo_account': self.pseudo_account,
            'organization_id': self.organization_id,
            'strategy_type': self.strategy_type,
            'status': self.status,
            'description': self.description,
            'max_loss_amount': self.max_loss_amount,
            'max_profit_amount': self.max_profit_amount,
            'max_positions': self.max_positions,
            'tags': self.tags,
            'configuration': self.configuration,
            'total_pnl': self.total_pnl,
            'realized_pnl': self.realized_pnl,
            'unrealized_pnl': self.unrealized_pnl,
            'total_margin_used': self.total_margin_used,
            'active_positions_count': self.active_positions_count,
            'total_orders_count': self.total_orders_count,
            'active_orders_count': self.active_orders_count,
            'holdings_count': self.holdings_count,
            'auto_square_off_enabled': self.auto_square_off_enabled,
            'square_off_time': self.square_off_time,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'ended_at': self.ended_at.isoformat() if self.ended_at else None,
            'squared_off_at': self.squared_off_at.isoformat() if self.squared_off_at else None
        }