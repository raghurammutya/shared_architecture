# app/utils/redis_data_manager.py
import json
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
import asyncio
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

class RedisDataManager:
    """Manages storage and retrieval of trading data in Redis with strategy support and cluster compatibility"""
    
    def __init__(self, redis_client: Optional[Any] = None, db_session: Optional[Session] = None):
        self.redis = redis_client
        self.db = db_session
        self._enabled = redis_client is not None
        self.ttl = 86400  # 24 hours default TTL
        self._is_cluster = self._detect_cluster_mode()
        
        if not self._enabled:
            logger.warning("RedisDataManager initialized without Redis - caching disabled")
        elif self._is_cluster:
            logger.info("RedisDataManager initialized with Redis cluster support")
        else:
            logger.info("RedisDataManager initialized with single Redis instance")
    
    def _detect_cluster_mode(self) -> bool:
        """Detect if Redis client is in cluster mode"""
        if not self.redis:
            return False
        
        try:
            # Check if it's a RedisCluster instance
            return hasattr(self.redis, 'startup_nodes') or 'RedisCluster' in str(type(self.redis))
        except Exception:
            return False
    
    # Key generation methods
    def _get_org_key(self, organization_id: str) -> str:
        """Get base key for organization"""
        return f"trade_data:{organization_id}"
    
    def _get_account_key(self, organization_id: str, pseudo_account: str) -> str:
        """Get base key for account"""
        return f"{self._get_org_key(organization_id)}:{pseudo_account}"
    
    def _get_strategy_key(self, organization_id: str, pseudo_account: str, strategy_id: str) -> str:
        """Get base key for strategy"""
        return f"{self._get_account_key(organization_id, pseudo_account)}:strategies:{strategy_id}"
    
    def _get_data_key(self, organization_id: str, pseudo_account: str, data_type: str, strategy_id: Optional[str] = None) -> str:
        """Get key for specific data type (positions, holdings, orders, margins)"""
        if strategy_id:
            return f"{self._get_strategy_key(organization_id, pseudo_account, strategy_id)}:{data_type}"
        else:
            return f"{self._get_account_key(organization_id, pseudo_account)}:{data_type}"
    
    # Storage methods
    def store_positions(self, organization_id: str, pseudo_account: str, positions: List, strategy_id: Optional[str] = None) -> bool:
        """Store positions data in Redis (cluster-compatible)"""
        if not self._enabled or not self.redis:
            return False
        
        try:
            key = self._get_data_key(organization_id, pseudo_account, "positions", strategy_id)
            
            # Convert positions to JSON-serializable format
            positions_data = []
            for pos in positions:
                pos_dict = pos if isinstance(pos, dict) else self._model_to_dict(pos)
                # Ensure datetime fields are serialized
                pos_dict = self._serialize_datetime_fields(pos_dict)
                positions_data.append(pos_dict)
            
            # Store as JSON string (sync operation, works with both single Redis and cluster)
            self.redis.setex(
                key, 
                self.ttl, 
                json.dumps(positions_data)
            )
            
            # Also store instrument-wise for quick lookups
            if strategy_id:
                for pos in positions_data:
                    instrument_key = pos.get('instrument_key')
                    if instrument_key:
                        inst_key = f"{key}:by_instrument:{instrument_key}"
                        self.redis.setex(inst_key, self.ttl, json.dumps(pos))
            
            logger.info(f"Stored {len(positions)} positions for {pseudo_account} (strategy: {strategy_id})")
            return True
            
        except Exception as e:
            logger.error(f"Failed to store positions: {e}")
            return False
    
    def store_holdings(self, organization_id: str, pseudo_account: str, holdings: List, strategy_id: Optional[str] = None) -> bool:
        """Store holdings data in Redis (cluster-compatible)"""
        if not self._enabled or not self.redis:
            return False
        
        try:
            key = self._get_data_key(organization_id, pseudo_account, "holdings", strategy_id)
            
            holdings_data = []
            for holding in holdings:
                holding_dict = holding if isinstance(holding, dict) else self._model_to_dict(holding)
                holding_dict = self._serialize_datetime_fields(holding_dict)
                holdings_data.append(holding_dict)
            
            self.redis.setex(key, self.ttl, json.dumps(holdings_data))
            
            # Store instrument-wise
            if strategy_id:
                for holding in holdings_data:
                    instrument_key = holding.get('instrument_key')
                    if instrument_key:
                        inst_key = f"{key}:by_instrument:{instrument_key}"
                        self.redis.setex(inst_key, self.ttl, json.dumps(holding))
            
            logger.info(f"Stored {len(holdings)} holdings for {pseudo_account} (strategy: {strategy_id})")
            return True
            
        except Exception as e:
            logger.error(f"Failed to store holdings: {e}")
            return False
    
    def store_orders(self, organization_id: str, pseudo_account: str, orders: List, strategy_id: Optional[str] = None) -> bool:
        """Store orders data in Redis (cluster-compatible)"""
        if not self._enabled or not self.redis:
            return False
        
        try:
            key = self._get_data_key(organization_id, pseudo_account, "orders", strategy_id)
            
            orders_data = []
            for order in orders:
                order_dict = order if isinstance(order, dict) else self._model_to_dict(order)
                order_dict = self._serialize_datetime_fields(order_dict)
                orders_data.append(order_dict)
            
            self.redis.setex(key, self.ttl, json.dumps(orders_data))
            
            # Store by status for quick filtering
            status_groups = {}
            for order in orders_data:
                status = order.get('status', 'UNKNOWN')
                if status not in status_groups:
                    status_groups[status] = []
                status_groups[status].append(order)
            
            for status, status_orders in status_groups.items():
                status_key = f"{key}:by_status:{status}"
                self.redis.setex(status_key, self.ttl, json.dumps(status_orders))
            
            logger.info(f"Stored {len(orders)} orders for {pseudo_account} (strategy: {strategy_id})")
            return True
            
        except Exception as e:
            logger.error(f"Failed to store orders: {e}")
            return False
    
    def store_margins(self, organization_id: str, pseudo_account: str, margins: List, strategy_id: Optional[str] = None) -> bool:
        """Store margins data in Redis (cluster-compatible)"""
        if not self._enabled or not self.redis:
            return False
        
        try:
            key = self._get_data_key(organization_id, pseudo_account, "margins", strategy_id)
            
            margins_data = []
            for margin in margins:
                margin_dict = margin if isinstance(margin, dict) else self._model_to_dict(margin)
                margin_dict = self._serialize_datetime_fields(margin_dict)
                margins_data.append(margin_dict)
            
            self.redis.setex(key, self.ttl, json.dumps(margins_data))
            
            logger.info(f"Stored {len(margins)} margins for {pseudo_account} (strategy: {strategy_id})")
            return True
            
        except Exception as e:
            logger.error(f"Failed to store margins: {e}")
            return False
    
    # Retrieval methods
    async def get_positions(self, organization_id: str, pseudo_account: str, strategy_id: Optional[str] = None) -> List[Dict]:
        """Get positions from Redis with database fallback"""
        if not self._enabled or not self.redis:
            return await self._get_positions_from_db(pseudo_account, strategy_id)
        
        try:
            key = self._get_data_key(organization_id, pseudo_account, "positions", strategy_id)
            data = await self.redis.get(key)
            
            if data:
                return json.loads(data)
            
            # Fallback to database if Redis is empty
            logger.info(f"Redis cache miss for positions, falling back to database for {pseudo_account}")
            db_data = await self._get_positions_from_db(pseudo_account, strategy_id)
            
            # Store in Redis for next time
            if db_data:
                self.store_positions(organization_id, pseudo_account, db_data, strategy_id)
            
            return db_data
            
        except Exception as e:
            logger.error(f"Failed to get positions from Redis: {e}, falling back to database")
            return await self._get_positions_from_db(pseudo_account, strategy_id)
    
    async def get_holdings(self, organization_id: str, pseudo_account: str, strategy_id: Optional[str] = None) -> List[Dict]:
        """Get holdings from Redis with database fallback"""
        if not self._enabled or not self.redis:
            return await self._get_holdings_from_db(pseudo_account, strategy_id)
        
        try:
            key = self._get_data_key(organization_id, pseudo_account, "holdings", strategy_id)
            data = await self.redis.get(key)
            
            if data:
                return json.loads(data)
            
            # Fallback to database if Redis is empty
            logger.info(f"Redis cache miss for holdings, falling back to database for {pseudo_account}")
            db_data = await self._get_holdings_from_db(pseudo_account, strategy_id)
            
            # Store in Redis for next time
            if db_data:
                self.store_holdings(organization_id, pseudo_account, db_data, strategy_id)
            
            return db_data
            
        except Exception as e:
            logger.error(f"Failed to get holdings from Redis: {e}, falling back to database")
            return await self._get_holdings_from_db(pseudo_account, strategy_id)
    
    async def get_orders(self, organization_id: str, pseudo_account: str, strategy_id: Optional[str] = None, status: Optional[str] = None) -> List[Dict]:
        """Get orders from Redis with database fallback, optionally filtered by status"""
        if not self._enabled or not self.redis:
            return await self._get_orders_from_db(pseudo_account, strategy_id, status)
        
        try:
            if status:
                key = f"{self._get_data_key(organization_id, pseudo_account, 'orders', strategy_id)}:by_status:{status}"
            else:
                key = self._get_data_key(organization_id, pseudo_account, "orders", strategy_id)
            
            data = await self.redis.get(key)
            
            if data:
                return json.loads(data)
            
            # Fallback to database if Redis is empty
            logger.info(f"Redis cache miss for orders, falling back to database for {pseudo_account}")
            db_data = await self._get_orders_from_db(pseudo_account, strategy_id, status)
            
            # Store in Redis for next time (without status filter for general caching)
            if db_data and not status:
                self.store_orders(organization_id, pseudo_account, db_data, strategy_id)
            
            return db_data
            
        except Exception as e:
            logger.error(f"Failed to get orders from Redis: {e}, falling back to database")
            return await self._get_orders_from_db(pseudo_account, strategy_id, status)
    
    async def get_margins(self, organization_id: str, pseudo_account: str, strategy_id: Optional[str] = None) -> List[Dict]:
        """Get margins from Redis with database fallback"""
        if not self._enabled or not self.redis:
            return await self._get_margins_from_db(pseudo_account, strategy_id)
        
        try:
            key = self._get_data_key(organization_id, pseudo_account, "margins", strategy_id)
            data = await self.redis.get(key)
            
            if data:
                return json.loads(data)
            
            # Fallback to database if Redis is empty
            logger.info(f"Redis cache miss for margins, falling back to database for {pseudo_account}")
            db_data = await self._get_margins_from_db(pseudo_account, strategy_id)
            
            # Store in Redis for next time
            if db_data:
                self.store_margins(organization_id, pseudo_account, db_data, strategy_id)
            
            return db_data
            
        except Exception as e:
            logger.error(f"Failed to get margins from Redis: {e}, falling back to database")
            return await self._get_margins_from_db(pseudo_account, strategy_id)
    
    # Strategy management
    async def get_all_strategies(self, organization_id: str, pseudo_account: str) -> List[str]:
        """Get list of all strategies for an account"""
        if not self._enabled or not self.redis:
            return []
        
        try:
            pattern = f"{self._get_account_key(organization_id, pseudo_account)}:strategies:*"
            keys = []
            async for key in self.redis.scan_iter(match=pattern):
                # Extract strategy_id from key
                strategy_id = key.decode().split(':strategies:')[-1].split(':')[0]
                if strategy_id not in keys:
                    keys.append(strategy_id)
            return keys
            
        except Exception as e:
            logger.error(f"Failed to get strategies: {e}")
            return []
    
    async def store_strategy_metadata(self, organization_id: str, pseudo_account: str, strategy_id: str, metadata: Dict) -> bool:
        """Store strategy metadata"""
        if not self._enabled or not self.redis:
            return False
        
        try:
            key = f"{self._get_strategy_key(organization_id, pseudo_account, strategy_id)}:metadata"
            metadata['updated_at'] = datetime.utcnow().isoformat()
            await self.redis.setex(key, self.ttl, json.dumps(metadata))
            return True
            
        except Exception as e:
            logger.error(f"Failed to store strategy metadata: {e}")
            return False
    
    async def get_strategy_metadata(self, organization_id: str, pseudo_account: str, strategy_id: str) -> Optional[Dict]:
        """Get strategy metadata"""
        if not self._enabled or not self.redis:
            return None
        
        try:
            key = f"{self._get_strategy_key(organization_id, pseudo_account, strategy_id)}:metadata"
            data = await self.redis.get(key)
            
            if data:
                return json.loads(data)
            return None
            
        except Exception as e:
            logger.error(f"Failed to get strategy metadata: {e}")
            return None
    
    # Aggregation methods
    async def get_account_summary(self, organization_id: str, pseudo_account: str) -> Dict:
        """Get summary of all data for an account"""
        if not self._enabled or not self.redis:
            return {}
        
        try:
            summary = {
                'positions': await self.get_positions(organization_id, pseudo_account),
                'holdings': await self.get_holdings(organization_id, pseudo_account),
                'orders': await self.get_orders(organization_id, pseudo_account),
                'margins': await self.get_margins(organization_id, pseudo_account),
                'strategies': await self.get_all_strategies(organization_id, pseudo_account)
            }
            
            # Add strategy-wise data
            strategy_data = {}
            for strategy_id in summary['strategies']:
                strategy_data[strategy_id] = {
                    'metadata': await self.get_strategy_metadata(organization_id, pseudo_account, strategy_id),
                    'positions': await self.get_positions(organization_id, pseudo_account, strategy_id),
                    'holdings': await self.get_holdings(organization_id, pseudo_account, strategy_id),
                    'orders': await self.get_orders(organization_id, pseudo_account, strategy_id),
                    'margins': await self.get_margins(organization_id, pseudo_account, strategy_id)
                }
            
            summary['strategy_data'] = strategy_data
            return summary
            
        except Exception as e:
            logger.error(f"Failed to get account summary: {e}")
            return {}
    
    # Helper methods
    def _model_to_dict(self, model: Any) -> Dict:
        """Convert SQLAlchemy model to dictionary"""
        if hasattr(model, '__dict__'):
            data = {}
            for key, value in model.__dict__.items():
                if not key.startswith('_'):
                    data[key] = value
            return data
        return {}
    
    def _serialize_datetime_fields(self, data: Dict) -> Dict:
        """Convert datetime objects to ISO format strings"""
        for key, value in data.items():
            if isinstance(value, datetime):
                data[key] = value.isoformat()
        return data
    
    async def clear_account_data(self, organization_id: str, pseudo_account: str) -> bool:
        """Clear all cached data for an account"""
        if not self._enabled or not self.redis:
            return False
        
        try:
            pattern = f"{self._get_account_key(organization_id, pseudo_account)}:*"
            cursor = 0
            while True:
                cursor, keys = await self.redis.scan(cursor, match=pattern, count=100)
                if keys:
                    await self.redis.delete(*keys)
                if cursor == 0:
                    break
            
            logger.info(f"Cleared all data for {pseudo_account}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to clear account data: {e}")
            return False
    
    async def invalidate_strategy_data(self, organization_id: str, pseudo_account: str, strategy_id: str) -> bool:
        """Invalidate all cached data for a specific strategy"""
        if not self._enabled or not self.redis:
            return False
        
        try:
            pattern = f"{self._get_strategy_key(organization_id, pseudo_account, strategy_id)}:*"
            cursor = 0
            while True:
                cursor, keys = await self.redis.scan(cursor, match=pattern, count=100)
                if keys:
                    await self.redis.delete(*keys)
                if cursor == 0:
                    break
            
            logger.info(f"Invalidated data for strategy {strategy_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to invalidate strategy data: {e}")
            return False
    
    # Database fallback methods
    async def _get_positions_from_db(self, pseudo_account: str, strategy_id: Optional[str] = None) -> List[Dict]:
        """Get positions from database"""
        if not self.db:
            return []
        
        try:
            from shared_architecture.db.models.position_model import PositionModel
            query = self.db.query(PositionModel).filter_by(pseudo_account=pseudo_account)
            if strategy_id:
                query = query.filter_by(strategy_id=strategy_id)
            
            positions = query.all()
            return [self._model_to_dict(pos) for pos in positions]
        except Exception as e:
            logger.error(f"Failed to get positions from database: {e}")
            return []
    
    async def _get_holdings_from_db(self, pseudo_account: str, strategy_id: Optional[str] = None) -> List[Dict]:
        """Get holdings from database"""
        if not self.db:
            return []
        
        try:
            from shared_architecture.db.models.holding_model import HoldingModel
            query = self.db.query(HoldingModel).filter_by(pseudo_account=pseudo_account)
            if strategy_id:
                query = query.filter_by(strategy_id=strategy_id)
            
            holdings = query.all()
            return [self._model_to_dict(holding) for holding in holdings]
        except Exception as e:
            logger.error(f"Failed to get holdings from database: {e}")
            return []
    
    async def _get_orders_from_db(self, pseudo_account: str, strategy_id: Optional[str] = None, status: Optional[str] = None) -> List[Dict]:
        """Get orders from database"""
        if not self.db:
            return []
        
        try:
            from shared_architecture.db.models.order_model import OrderModel
            query = self.db.query(OrderModel).filter_by(pseudo_account=pseudo_account)
            if strategy_id:
                query = query.filter_by(strategy_id=strategy_id)
            if status:
                query = query.filter_by(status=status)
            
            orders = query.all()
            return [self._model_to_dict(order) for order in orders]
        except Exception as e:
            logger.error(f"Failed to get orders from database: {e}")
            return []
    
    async def _get_margins_from_db(self, pseudo_account: str, strategy_id: Optional[str] = None) -> List[Dict]:
        """Get margins from database"""
        if not self.db:
            return []
        
        try:
            from shared_architecture.db.models.margin_model import MarginModel
            query = self.db.query(MarginModel).filter_by(pseudo_account=pseudo_account)
            if strategy_id:
                query = query.filter_by(strategy_id=strategy_id)
            
            margins = query.all()
            return [self._model_to_dict(margin) for margin in margins]
        except Exception as e:
            logger.error(f"Failed to get margins from database: {e}")
            return []