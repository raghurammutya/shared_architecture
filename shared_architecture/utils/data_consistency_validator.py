# shared_architecture/utils/data_consistency_validator.py
import logging
from typing import List, Dict, Tuple, Optional, Set
from decimal import Decimal, ROUND_HALF_UP
from sqlalchemy.orm import Session
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class ConsistencyIssue:
    """Represents a data consistency issue"""
    issue_type: str
    severity: str  # CRITICAL, HIGH, MEDIUM, LOW
    instrument_key: str
    organization_id: str
    pseudo_account: str
    description: str
    expected_value: Optional[float] = None
    actual_value: Optional[float] = None
    strategies_involved: Optional[List[str]] = None
    
    def to_dict(self) -> Dict:
        return {
            'issue_type': self.issue_type,
            'severity': self.severity,
            'instrument_key': self.instrument_key,
            'organization_id': self.organization_id,
            'pseudo_account': self.pseudo_account,
            'description': self.description,
            'expected_value': self.expected_value,
            'actual_value': self.actual_value,
            'strategies_involved': self.strategies_involved
        }

@dataclass
class InstrumentData:
    """Consolidated data for an instrument across strategies"""
    instrument_key: str
    blanket_quantity: int
    blanket_avg_price: float
    blanket_total_value: float
    strategy_data: Dict[str, Dict]  # strategy_id -> {quantity, avg_price, total_value}
    
    def get_strategy_total_quantity(self) -> int:
        """Sum of quantities across all strategies"""
        return sum(data['quantity'] for data in self.strategy_data.values())
    
    def get_strategy_weighted_avg_price(self) -> float:
        """Weighted average price across strategies"""
        total_value = sum(data['total_value'] for data in self.strategy_data.values())
        total_quantity = self.get_strategy_total_quantity()
        
        if total_quantity == 0:
            return 0.0
        
        return total_value / total_quantity

class DataConsistencyValidator:
    """
    Validates consistency between blanket datasets and strategy-specific datasets.
    
    Key Validations:
    1. Quantity consistency: Sum of strategy quantities = blanket quantity
    2. Price consistency: Weighted average of strategy prices = blanket average price
    3. Value consistency: Sum of strategy values = blanket value
    4. No orphaned data: All strategy data has corresponding blanket data
    5. Symbol/instrument_key consistency: Proper conversions maintained
    """
    
    def __init__(self, db: Session):
        self.db = db
        self.tolerance = Decimal('0.01')  # 1 paisa tolerance for price differences
    
    def validate_account_consistency(
        self, 
        organization_id: str, 
        pseudo_account: str,
        data_types: List[str] = None
    ) -> List[ConsistencyIssue]:
        """
        Validate consistency for all data types for an account.
        
        Args:
            organization_id: Organization ID
            pseudo_account: Trading account
            data_types: List of data types to validate ['positions', 'holdings', 'orders']
        
        Returns:
            List of consistency issues found
        """
        if data_types is None:
            data_types = ['positions', 'holdings', 'orders']
        
        issues = []
        
        for data_type in data_types:
            try:
                if data_type == 'positions':
                    issues.extend(self._validate_positions_consistency(organization_id, pseudo_account))
                elif data_type == 'holdings':
                    issues.extend(self._validate_holdings_consistency(organization_id, pseudo_account))
                elif data_type == 'orders':
                    issues.extend(self._validate_orders_consistency(organization_id, pseudo_account))
                    
            except Exception as e:
                logger.error(f"Error validating {data_type} consistency: {e}")
                issues.append(ConsistencyIssue(
                    issue_type=f"{data_type.upper()}_VALIDATION_ERROR",
                    severity="HIGH",
                    instrument_key="UNKNOWN",
                    organization_id=organization_id,
                    pseudo_account=pseudo_account,
                    description=f"Failed to validate {data_type}: {str(e)}"
                ))
        
        return issues
    
    def _validate_positions_consistency(self, organization_id: str, pseudo_account: str) -> List[ConsistencyIssue]:
        """Validate position data consistency"""
        from shared_architecture.db.models.position_model import PositionModel
        
        issues = []
        
        # Get all positions for this account
        all_positions = self.db.query(PositionModel).filter_by(pseudo_account=pseudo_account).all()
        
        # Group by instrument_key
        instrument_data = self._group_positions_by_instrument(all_positions)
        
        for instrument_key, data in instrument_data.items():
            issues.extend(self._validate_instrument_position_consistency(
                organization_id, pseudo_account, instrument_key, data
            ))
        
        return issues
    
    def _validate_holdings_consistency(self, organization_id: str, pseudo_account: str) -> List[ConsistencyIssue]:
        """Validate holding data consistency"""
        from shared_architecture.db.models.holding_model import HoldingModel
        
        issues = []
        
        # Get all holdings for this account
        all_holdings = self.db.query(HoldingModel).filter_by(pseudo_account=pseudo_account).all()
        
        # Group by instrument_key
        instrument_data = self._group_holdings_by_instrument(all_holdings)
        
        for instrument_key, data in instrument_data.items():
            issues.extend(self._validate_instrument_holding_consistency(
                organization_id, pseudo_account, instrument_key, data
            ))
        
        return issues
    
    def _validate_orders_consistency(self, organization_id: str, pseudo_account: str) -> List[ConsistencyIssue]:
        """Validate order data consistency"""
        from shared_architecture.db.models.order_model import OrderModel
        
        issues = []
        
        # Get all orders for this account
        all_orders = self.db.query(OrderModel).filter_by(pseudo_account=pseudo_account).all()
        
        # Group by instrument_key and trade_type
        instrument_data = self._group_orders_by_instrument(all_orders)
        
        for key, data in instrument_data.items():
            instrument_key, trade_type = key
            issues.extend(self._validate_instrument_order_consistency(
                organization_id, pseudo_account, instrument_key, trade_type, data
            ))
        
        return issues
    
    def _group_positions_by_instrument(self, positions: List) -> Dict[str, InstrumentData]:
        """Group positions by instrument_key"""
        grouped = {}
        
        for position in positions:
            instrument_key = position.instrument_key
            if not instrument_key:
                continue
                
            if instrument_key not in grouped:
                grouped[instrument_key] = {
                    'blanket': None,
                    'strategies': {}
                }
            
            if not position.strategy_id or position.strategy_id == 'default':
                # This is blanket data
                grouped[instrument_key]['blanket'] = {
                    'net_quantity': position.net_quantity or 0,
                    'buy_quantity': position.buy_quantity or 0,
                    'sell_quantity': position.sell_quantity or 0,
                    'buy_avg_price': position.buy_avg_price or 0.0,
                    'sell_avg_price': position.sell_avg_price or 0.0,
                    'buy_value': position.buy_value or 0.0,
                    'sell_value': position.sell_value or 0.0
                }
            else:
                # This is strategy data
                grouped[instrument_key]['strategies'][position.strategy_id] = {
                    'net_quantity': position.net_quantity or 0,
                    'buy_quantity': position.buy_quantity or 0,
                    'sell_quantity': position.sell_quantity or 0,
                    'buy_avg_price': position.buy_avg_price or 0.0,
                    'sell_avg_price': position.sell_avg_price or 0.0,
                    'buy_value': position.buy_value or 0.0,
                    'sell_value': position.sell_value or 0.0
                }
        
        return grouped
    
    def _group_holdings_by_instrument(self, holdings: List) -> Dict[str, InstrumentData]:
        """Group holdings by instrument_key"""
        grouped = {}
        
        for holding in holdings:
            instrument_key = holding.instrument_key
            if not instrument_key:
                continue
                
            if instrument_key not in grouped:
                grouped[instrument_key] = {
                    'blanket': None,
                    'strategies': {}
                }
            
            if not holding.strategy_id or holding.strategy_id == 'default':
                # This is blanket data
                grouped[instrument_key]['blanket'] = {
                    'quantity': holding.quantity or 0,
                    'avg_price': holding.avg_price or 0.0,
                    'total_value': (holding.quantity or 0) * (holding.avg_price or 0.0)
                }
            else:
                # This is strategy data
                total_value = (holding.quantity or 0) * (holding.avg_price or 0.0)
                grouped[instrument_key]['strategies'][holding.strategy_id] = {
                    'quantity': holding.quantity or 0,
                    'avg_price': holding.avg_price or 0.0,
                    'total_value': total_value
                }
        
        return grouped
    
    def _group_orders_by_instrument(self, orders: List) -> Dict[Tuple[str, str], Dict]:
        """Group orders by instrument_key and trade_type"""
        grouped = {}
        
        for order in orders:
            instrument_key = order.instrument_key
            trade_type = order.trade_type
            
            if not instrument_key or not trade_type:
                continue
                
            key = (instrument_key, trade_type)
            
            if key not in grouped:
                grouped[key] = {
                    'blanket': {'total_quantity': 0, 'total_value': 0.0},
                    'strategies': {}
                }
            
            quantity = order.quantity or 0
            price = order.price or 0.0
            value = quantity * price
            
            if not order.strategy_id or order.strategy_id == 'default':
                # This is blanket data
                grouped[key]['blanket']['total_quantity'] += quantity
                grouped[key]['blanket']['total_value'] += value
            else:
                # This is strategy data
                if order.strategy_id not in grouped[key]['strategies']:
                    grouped[key]['strategies'][order.strategy_id] = {
                        'total_quantity': 0,
                        'total_value': 0.0
                    }
                
                grouped[key]['strategies'][order.strategy_id]['total_quantity'] += quantity
                grouped[key]['strategies'][order.strategy_id]['total_value'] += value
        
        return grouped
    
    def _validate_instrument_position_consistency(
        self, 
        organization_id: str, 
        pseudo_account: str, 
        instrument_key: str, 
        data: Dict
    ) -> List[ConsistencyIssue]:
        """Validate consistency for a single instrument's positions"""
        issues = []
        
        blanket = data.get('blanket')
        strategies = data.get('strategies', {})
        
        if not blanket and not strategies:
            return issues
        
        if not blanket and strategies:
            # Strategy data exists but no blanket data
            issues.append(ConsistencyIssue(
                issue_type="MISSING_BLANKET_POSITION",
                severity="HIGH",
                instrument_key=instrument_key,
                organization_id=organization_id,
                pseudo_account=pseudo_account,
                description=f"Strategy positions exist but no blanket position for {instrument_key}",
                strategies_involved=list(strategies.keys())
            ))
            return issues
        
        if blanket and not strategies:
            # Only blanket data exists - this is okay
            return issues
        
        # Both exist - validate consistency
        
        # Validate net quantity
        blanket_net_qty = blanket['net_quantity']
        strategy_net_qty = sum(s['net_quantity'] for s in strategies.values())
        
        if blanket_net_qty != strategy_net_qty:
            issues.append(ConsistencyIssue(
                issue_type="NET_QUANTITY_MISMATCH",
                severity="CRITICAL",
                instrument_key=instrument_key,
                organization_id=organization_id,
                pseudo_account=pseudo_account,
                description=f"Net quantity mismatch: blanket={blanket_net_qty}, strategies_sum={strategy_net_qty}",
                expected_value=float(blanket_net_qty),
                actual_value=float(strategy_net_qty),
                strategies_involved=list(strategies.keys())
            ))
        
        # Validate buy quantities and values
        blanket_buy_qty = blanket['buy_quantity']
        strategy_buy_qty = sum(s['buy_quantity'] for s in strategies.values())
        
        if blanket_buy_qty != strategy_buy_qty:
            issues.append(ConsistencyIssue(
                issue_type="BUY_QUANTITY_MISMATCH",
                severity="HIGH",
                instrument_key=instrument_key,
                organization_id=organization_id,
                pseudo_account=pseudo_account,
                description=f"Buy quantity mismatch: blanket={blanket_buy_qty}, strategies_sum={strategy_buy_qty}",
                expected_value=float(blanket_buy_qty),
                actual_value=float(strategy_buy_qty),
                strategies_involved=list(strategies.keys())
            ))
        
        # Validate buy value and average price
        if blanket_buy_qty > 0:
            blanket_buy_value = blanket['buy_value']
            strategy_buy_value = sum(s['buy_value'] for s in strategies.values())
            
            if abs(blanket_buy_value - strategy_buy_value) > float(self.tolerance):
                issues.append(ConsistencyIssue(
                    issue_type="BUY_VALUE_MISMATCH",
                    severity="HIGH",
                    instrument_key=instrument_key,
                    organization_id=organization_id,
                    pseudo_account=pseudo_account,
                    description=f"Buy value mismatch: blanket={blanket_buy_value}, strategies_sum={strategy_buy_value}",
                    expected_value=blanket_buy_value,
                    actual_value=strategy_buy_value,
                    strategies_involved=list(strategies.keys())
                ))
        
        return issues
    
    def _validate_instrument_holding_consistency(
        self, 
        organization_id: str, 
        pseudo_account: str, 
        instrument_key: str, 
        data: Dict
    ) -> List[ConsistencyIssue]:
        """Validate consistency for a single instrument's holdings"""
        issues = []
        
        blanket = data.get('blanket')
        strategies = data.get('strategies', {})
        
        if not blanket and not strategies:
            return issues
        
        if not blanket and strategies:
            issues.append(ConsistencyIssue(
                issue_type="MISSING_BLANKET_HOLDING",
                severity="HIGH",
                instrument_key=instrument_key,
                organization_id=organization_id,
                pseudo_account=pseudo_account,
                description=f"Strategy holdings exist but no blanket holding for {instrument_key}",
                strategies_involved=list(strategies.keys())
            ))
            return issues
        
        if blanket and not strategies:
            return issues
        
        # Validate quantity consistency
        blanket_qty = blanket['quantity']
        strategy_qty = sum(s['quantity'] for s in strategies.values())
        
        if blanket_qty != strategy_qty:
            issues.append(ConsistencyIssue(
                issue_type="HOLDING_QUANTITY_MISMATCH",
                severity="CRITICAL",
                instrument_key=instrument_key,
                organization_id=organization_id,
                pseudo_account=pseudo_account,
                description=f"Holding quantity mismatch: blanket={blanket_qty}, strategies_sum={strategy_qty}",
                expected_value=float(blanket_qty),
                actual_value=float(strategy_qty),
                strategies_involved=list(strategies.keys())
            ))
        
        # Validate weighted average price
        if strategy_qty > 0:
            blanket_avg_price = blanket['avg_price']
            strategy_total_value = sum(s['total_value'] for s in strategies.values())
            strategy_weighted_avg = strategy_total_value / strategy_qty
            
            if abs(blanket_avg_price - strategy_weighted_avg) > float(self.tolerance):
                issues.append(ConsistencyIssue(
                    issue_type="HOLDING_PRICE_MISMATCH",
                    severity="HIGH",
                    instrument_key=instrument_key,
                    organization_id=organization_id,
                    pseudo_account=pseudo_account,
                    description=f"Holding average price mismatch: blanket={blanket_avg_price}, weighted_avg={strategy_weighted_avg}",
                    expected_value=blanket_avg_price,
                    actual_value=strategy_weighted_avg,
                    strategies_involved=list(strategies.keys())
                ))
        
        return issues
    
    def _validate_instrument_order_consistency(
        self, 
        organization_id: str, 
        pseudo_account: str, 
        instrument_key: str, 
        trade_type: str,
        data: Dict
    ) -> List[ConsistencyIssue]:
        """Validate consistency for a single instrument's orders"""
        issues = []
        
        blanket = data.get('blanket')
        strategies = data.get('strategies', {})
        
        if not blanket and not strategies:
            return issues
        
        # For orders, we might have strategy data without blanket data (new orders)
        # This is acceptable, so we only validate when both exist
        
        if blanket and strategies:
            blanket_qty = blanket['total_quantity']
            strategy_qty = sum(s['total_quantity'] for s in strategies.values())
            
            if blanket_qty != strategy_qty:
                issues.append(ConsistencyIssue(
                    issue_type="ORDER_QUANTITY_MISMATCH",
                    severity="MEDIUM",
                    instrument_key=instrument_key,
                    organization_id=organization_id,
                    pseudo_account=pseudo_account,
                    description=f"Order quantity mismatch for {trade_type}: blanket={blanket_qty}, strategies_sum={strategy_qty}",
                    expected_value=float(blanket_qty),
                    actual_value=float(strategy_qty),
                    strategies_involved=list(strategies.keys())
                ))
        
        return issues
    
    def validate_strategy_retagging(
        self,
        organization_id: str,
        pseudo_account: str,
        retagging_request: Dict
    ) -> Tuple[bool, List[str]]:
        """
        Validate a strategy retagging request before execution.
        
        Args:
            retagging_request: {
                'source_strategy_id': 'strategy1',
                'target_strategy_id': 'strategy2',
                'allocations': [
                    {
                        'instrument_key': 'NSE@RELIANCE@equities',
                        'data_type': 'position',
                        'quantity': 50,
                        'price': 1000.0
                    }
                ]
            }
        
        Returns:
            (is_valid, list_of_errors)
        """
        errors = []
        
        try:
            allocations = retagging_request.get('allocations', [])
            
            for allocation in allocations:
                instrument_key = allocation['instrument_key']
                data_type = allocation['data_type']
                requested_qty = allocation['quantity']
                requested_price = allocation.get('price')
                
                # Validate based on data type
                if data_type == 'position':
                    errors.extend(self._validate_position_retagging(
                        organization_id, pseudo_account, instrument_key,
                        requested_qty, requested_price, retagging_request['source_strategy_id']
                    ))
                elif data_type == 'holding':
                    errors.extend(self._validate_holding_retagging(
                        organization_id, pseudo_account, instrument_key,
                        requested_qty, requested_price, retagging_request['source_strategy_id']
                    ))
        
        except Exception as e:
            errors.append(f"Validation error: {str(e)}")
        
        return len(errors) == 0, errors
    
    def _validate_position_retagging(
        self,
        organization_id: str,
        pseudo_account: str,
        instrument_key: str,
        requested_qty: int,
        requested_price: Optional[float],
        source_strategy_id: str
    ) -> List[str]:
        """Validate position retagging request"""
        from shared_architecture.db.models.position_model import PositionModel
        
        errors = []
        
        # Get source position
        position = self.db.query(PositionModel).filter_by(
            pseudo_account=pseudo_account,
            instrument_key=instrument_key,
            strategy_id=source_strategy_id
        ).first()
        
        if not position:
            errors.append(f"No position found for {instrument_key} in strategy {source_strategy_id}")
            return errors
        
        # Check quantity availability
        available_qty = abs(position.net_quantity or 0)
        if requested_qty > available_qty:
            errors.append(
                f"Requested quantity {requested_qty} exceeds available {available_qty} "
                f"for {instrument_key} in strategy {source_strategy_id}"
            )
        
        # Check price consistency if provided
        if requested_price:
            actual_avg_price = position.buy_avg_price if position.net_quantity > 0 else position.sell_avg_price
            if abs(actual_avg_price - requested_price) > float(self.tolerance):
                errors.append(
                    f"Price mismatch for {instrument_key}: "
                    f"requested={requested_price}, actual_avg={actual_avg_price}"
                )
        
        return errors
    
    def _validate_holding_retagging(
        self,
        organization_id: str,
        pseudo_account: str,
        instrument_key: str,
        requested_qty: int,
        requested_price: Optional[float],
        source_strategy_id: str
    ) -> List[str]:
        """Validate holding retagging request"""
        from shared_architecture.db.models.holding_model import HoldingModel
        
        errors = []
        
        # Get source holding
        holding = self.db.query(HoldingModel).filter_by(
            pseudo_account=pseudo_account,
            instrument_key=instrument_key,
            strategy_id=source_strategy_id
        ).first()
        
        if not holding:
            errors.append(f"No holding found for {instrument_key} in strategy {source_strategy_id}")
            return errors
        
        # Check quantity availability
        available_qty = holding.quantity or 0
        if requested_qty > available_qty:
            errors.append(
                f"Requested quantity {requested_qty} exceeds available {available_qty} "
                f"for {instrument_key} in strategy {source_strategy_id}"
            )
        
        # Check price consistency if provided
        if requested_price:
            actual_avg_price = holding.avg_price or 0.0
            if abs(actual_avg_price - requested_price) > float(self.tolerance):
                errors.append(
                    f"Price mismatch for {instrument_key}: "
                    f"requested={requested_price}, actual_avg={actual_avg_price}"
                )
        
        return errors