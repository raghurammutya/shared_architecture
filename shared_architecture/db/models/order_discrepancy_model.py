# shared_architecture/db/models/order_discrepancy_model.py
from sqlalchemy import Column, Integer, String, DateTime, Text, Boolean, Float
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()

class OrderDiscrepancyModel(Base):
    """
    Tracks discrepancies between AutoTrader operations and database state.
    Used for reconciliation when AutoTrader succeeds but DB operations fail.
    """
    __tablename__ = 'order_discrepancies'
    
    id = Column(Integer, primary_key=True)
    
    # Identifiers
    organization_id = Column(String, nullable=False)
    pseudo_account = Column(String, nullable=False)
    strategy_id = Column(String)
    
    # Order details
    order_id = Column(Integer, nullable=True)  # Our internal order ID (if created)
    autotrader_order_id = Column(String, nullable=True)  # AutoTrader's order ID
    exchange_order_id = Column(String, nullable=True)  # Exchange order ID
    
    # Operation details
    operation_type = Column(String, nullable=False)  # PLACE, MODIFY, CANCEL, SQUARE_OFF
    discrepancy_type = Column(String, nullable=False)  # DB_SAVE_FAILED, ORDER_NOT_FOUND, STATUS_MISMATCH
    
    # Original request data
    original_request = Column(Text)  # JSON string of original request
    autotrader_response = Column(Text)  # JSON string of AutoTrader response
    
    # Error details
    error_message = Column(Text)
    error_traceback = Column(Text, nullable=True)
    
    # Status tracking
    status = Column(String, default='PENDING')  # PENDING, RESOLVED, FAILED
    resolution_attempts = Column(Integer, default=0)
    max_attempts = Column(Integer, default=3)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    last_attempt = Column(DateTime, default=datetime.utcnow)
    resolved_at = Column(DateTime, nullable=True)
    
    # Manual review flags
    requires_manual_review = Column(Boolean, default=False)
    manual_review_notes = Column(Text, nullable=True)
    reviewed_by = Column(String, nullable=True)
    
    # Financial impact
    potential_loss = Column(Float, default=0.0)  # Estimated financial impact
    severity = Column(String, default='MEDIUM')  # LOW, MEDIUM, HIGH, CRITICAL
    
    def mark_resolved(self, resolution_notes: str = None):
        """Mark discrepancy as resolved"""
        self.status = 'RESOLVED'
        self.resolved_at = datetime.utcnow()
        if resolution_notes:
            self.manual_review_notes = resolution_notes
    
    def increment_attempt(self):
        """Increment resolution attempt counter"""
        self.resolution_attempts += 1
        self.last_attempt = datetime.utcnow()
        
        # Mark for manual review if max attempts reached
        if self.resolution_attempts >= self.max_attempts:
            self.requires_manual_review = True
    
    def to_dict(self):
        """Convert to dictionary for serialization"""
        return {
            'id': self.id,
            'organization_id': self.organization_id,
            'pseudo_account': self.pseudo_account,
            'strategy_id': self.strategy_id,
            'order_id': self.order_id,
            'autotrader_order_id': self.autotrader_order_id,
            'exchange_order_id': self.exchange_order_id,
            'operation_type': self.operation_type,
            'discrepancy_type': self.discrepancy_type,
            'error_message': self.error_message,
            'status': self.status,
            'resolution_attempts': self.resolution_attempts,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'resolved_at': self.resolved_at.isoformat() if self.resolved_at else None,
            'severity': self.severity,
            'requires_manual_review': self.requires_manual_review
        }