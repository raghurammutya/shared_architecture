# shared_architecture/mocks/autotrader_mock.py
import random
import time
from typing import Dict, List, Any, Optional
from datetime import datetime

class AutoTraderResponse:
    """Mock AutoTrader response"""
    
    def __init__(self, success: bool = True, result: Any = None, message: str = "Mock response"):
        self._success = success
        self.result = result or {}
        self.message = message
    
    def success(self) -> bool:
        return self._success

class AutoTraderMock:
    """Mock AutoTrader for development and testing"""
    
    SERVER_URL = "mock://api.stocksdeveloper.in"
    
    def __init__(self):
        self.orders = {}  # Store mock orders
        self.order_counter = 1000
    
    @staticmethod
    def create_instance(api_key: str, server_url: str) -> 'AutoTraderMock':
        """Factory method to match real AutoTrader interface"""
        return AutoTraderMock()
    
    def place_regular_order(self, **kwargs) -> AutoTraderResponse:
        """Mock regular order placement"""
        # Simulate network delay
        time.sleep(0.1)
        
        # Simulate occasional failures (5% chance)
        if random.random() < 0.05:
            return AutoTraderResponse(
                success=False,
                result=None,
                message="Mock error: Order rejected by exchange"
            )
        
        order_id = f"MOCK_{self.order_counter}"
        self.order_counter += 1
        
        # Store order details
        self.orders[order_id] = {
            "order_id": order_id,
            "exchange_order_id": f"EX{order_id}",
            "status": "PENDING",
            "created_at": datetime.utcnow(),
            **kwargs
        }
        
        return AutoTraderResponse(
            success=True,
            result={
                "order_id": order_id,
                "exchange_order_id": f"EX{order_id}",
                "status": "PENDING",
                "message": "Order placed successfully"
            }
        )
    
    def place_cover_order(self, **kwargs) -> AutoTraderResponse:
        """Mock cover order placement"""
        return self.place_regular_order(**kwargs)
    
    def place_bracket_order(self, **kwargs) -> AutoTraderResponse:
        """Mock bracket order placement"""
        return self.place_regular_order(**kwargs)
    
    def place_advanced_order(self, **kwargs) -> AutoTraderResponse:
        """Mock advanced order placement"""
        return self.place_regular_order(**kwargs)
    
    def modify_order_by_platform_id(self, **kwargs) -> AutoTraderResponse:
        """Mock order modification"""
        time.sleep(0.1)
        
        platform_id = kwargs.get('platform_id')
        if platform_id in self.orders:
            self.orders[platform_id].update(kwargs)
            return AutoTraderResponse(
                success=True,
                result={"status": "MODIFIED", "order_id": platform_id}
            )
        
        return AutoTraderResponse(
            success=False,
            message=f"Order {platform_id} not found"
        )
    
    def cancel_order_by_platform_id(self, **kwargs) -> AutoTraderResponse:
        """Mock order cancellation"""
        time.sleep(0.1)
        
        platform_id = kwargs.get('platform_id')
        if platform_id in self.orders:
            self.orders[platform_id]['status'] = 'CANCELLED'
            return AutoTraderResponse(
                success=True,
                result={"status": "CANCELLED", "order_id": platform_id}
            )
        
        return AutoTraderResponse(
            success=False,
            message=f"Order {platform_id} not found"
        )
    
    def get_order_status(self, order_id: str) -> AutoTraderResponse:
        """Mock order status check"""
        if order_id in self.orders:
            order = self.orders[order_id]
            
            # Simulate order progression
            age_seconds = (datetime.utcnow() - order['created_at']).total_seconds()
            
            if age_seconds < 2:
                status = "PENDING"
            elif age_seconds < 5:
                status = "OPEN"
            elif age_seconds < 10:
                status = "PARTIALLY_FILLED"
                order['filled_quantity'] = order.get('quantity', 100) // 2
            else:
                status = "COMPLETE"
                order['filled_quantity'] = order.get('quantity', 100)
            
            order['status'] = status
            
            return AutoTraderResponse(
                success=True,
                result={
                    "order_id": order_id,
                    "status": status,
                    "filled_quantity": order.get('filled_quantity', 0),
                    "average_price": order.get('price', 100.0)
                }
            )
        
        return AutoTraderResponse(
            success=False,
            message=f"Order {order_id} not found"
        )
    
    def read_platform_margins(self, pseudo_account: str) -> AutoTraderResponse:
        """Mock margin data"""
        return AutoTraderResponse(
            success=True,
            result=[
                MockMargin("EQUITY", 100000.0, 25000.0),
                MockMargin("COMMODITY", 50000.0, 10000.0)
            ]
        )
    
    def read_platform_positions(self, pseudo_account: str) -> AutoTraderResponse:
        """Mock position data"""
        return AutoTraderResponse(
            success=True,
            result=[
                MockPosition("NSE", "RELIANCE", 100, 2500.0),
                MockPosition("NSE", "INFY", -50, 1500.0)
            ]
        )
    
    def read_platform_holdings(self, pseudo_account: str) -> AutoTraderResponse:
        """Mock holding data"""
        return AutoTraderResponse(
            success=True,
            result=[
                MockHolding("NSE", "RELIANCE", 200, 2400.0),
                MockHolding("NSE", "TCS", 50, 3500.0)
            ]
        )
    
    def read_platform_orders(self, pseudo_account: str) -> AutoTraderResponse:
        """Mock order data"""
        mock_orders = []
        for order_id, order_data in self.orders.items():
            if order_data.get('pseudo_account') == pseudo_account:
                mock_orders.append(MockOrder(order_data))
        
        return AutoTraderResponse(
            success=True,
            result=mock_orders
        )
    
    def square_off_position(self, **kwargs) -> AutoTraderResponse:
        """Mock position square off"""
        return AutoTraderResponse(
            success=True,
            result={"status": "SQUARED_OFF", "order_id": f"MOCK_{self.order_counter}"}
        )
    
    def square_off_portfolio(self, **kwargs) -> AutoTraderResponse:
        """Mock portfolio square off"""
        return AutoTraderResponse(
            success=True,
            result={"status": "SQUARED_OFF", "order_ids": [f"MOCK_{i}" for i in range(self.order_counter, self.order_counter + 5)]}
        )
    
    def cancel_all_orders(self, **kwargs) -> AutoTraderResponse:
        """Mock cancel all orders"""
        cancelled_count = len([o for o in self.orders.values() if o['status'] in ['PENDING', 'OPEN']])
        return AutoTraderResponse(
            success=True,
            result={"status": "CANCELLED", "cancelled_count": cancelled_count}
        )
    
    def cancel_child_orders_by_platform_id(self, **kwargs) -> AutoTraderResponse:
        """Mock cancel child orders"""
        return AutoTraderResponse(
            success=True,
            result={"status": "CANCELLED", "cancelled_count": 2}
        )

# Mock data classes
class MockMargin:
    def __init__(self, category: str, available: float, utilized: float):
        self.category = category
        self.available = available
        self.utilized = utilized
        self.total = available + utilized
        self.funds = available
        self.collateral = 0.0
        self.span = 0.0
        self.exposure = utilized * 0.2
        self.adhoc = 0.0
        self.net = available
        self.payin = 0.0
        self.payout = 0.0
        self.realised_mtm = 0.0
        self.unrealised_mtm = 0.0
        self.stock_broker = "MOCK_BROKER"
        self.trading_account = "MOCK_ACCOUNT"

class MockPosition:
    def __init__(self, exchange: str, symbol: str, quantity: int, avg_price: float):
        self.exchange = exchange
        self.symbol = symbol
        self.net_quantity = quantity
        self.buy_quantity = quantity if quantity > 0 else 0
        self.sell_quantity = -quantity if quantity < 0 else 0
        self.buy_avg_price = avg_price if quantity > 0 else 0
        self.sell_avg_price = avg_price if quantity < 0 else 0
        self.buy_value = self.buy_quantity * self.buy_avg_price
        self.sell_value = self.sell_quantity * self.sell_avg_price
        self.ltp = avg_price * 1.01  # Simulate small price movement
        self.pnl = (self.ltp - avg_price) * quantity
        self.realised_pnl = 0.0
        self.unrealised_pnl = self.pnl
        self.mtm = self.pnl
        self.multiplier = 1
        self.net_value = quantity * self.ltp
        self.overnight_quantity = 0
        self.category = "INTRADAY"
        self.type = "MIS"
        self.platform = "MOCK_PLATFORM"
        self.stock_broker = "MOCK_BROKER"
        self.trading_account = "MOCK_ACCOUNT"
        self.direction = "BUY" if quantity > 0 else "SELL"
        self.state = "OPEN"

class MockHolding:
    def __init__(self, exchange: str, symbol: str, quantity: int, avg_price: float):
        self.exchange = exchange
        self.symbol = symbol
        self.quantity = quantity
        self.avg_price = avg_price
        self.product = "DELIVERY"
        self.isin = f"INE{symbol[:3]}000000"
        self.collateral_qty = 0
        self.t1_qty = 0
        self.collateral_type = ""
        self.pnl = (avg_price * 1.02 - avg_price) * quantity  # Simulate 2% profit
        self.haircut = 0.1
        self.instrument_token = hash(symbol) % 1000000
        self.stock_broker = "MOCK_BROKER"
        self.platform = "MOCK_PLATFORM"
        self.ltp = avg_price * 1.02
        self.currentValue = self.ltp * quantity
        self.totalQty = quantity

class MockOrder:
    def __init__(self, order_data: Dict):
        self.__dict__.update(order_data)
        # Ensure all required fields exist
        self.exchange_time = datetime.utcnow()
        self.platform_time = datetime.utcnow()
        self.modified_time = None
        self.filled_quantity = order_data.get('filled_quantity', 0)
        self.pending_quantity = order_data.get('quantity', 100) - self.filled_quantity
        self.average_price = order_data.get('price', 100.0)
        self.status_message = ""
        self.validity = "DAY"
        self.amo = False