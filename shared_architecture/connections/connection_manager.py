# shared_architecture/connections/connection_manager.py

import logging
from sqlalchemy import text
from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession
import os
import asyncio
from typing import Dict, List, Optional
from shared_architecture.connections.redis_client import get_redis_client
from shared_architecture.connections.mongodb_client import get_mongo_client
from shared_architecture.connections.timescaledb_client import (
    get_timescaledb_session,
    get_sync_timescaledb_session,
)
from shared_architecture.connections.rabbitmq_client import get_rabbitmq_connection
from shared_architecture.connections.service_discovery import service_discovery

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Centralized connection manager with service discovery and health checking"""
    
    def __init__(self):
        self.redis = None
        self.mongodb = None
        self.timescaledb = None
        self.timescaledb_sync = None
        self.rabbitmq = None
        self._testing_mode = os.getenv("TESTING") == "true"
        self._initialized = False
        
    async def initialize(self, required_services: Optional[List[str]] = None):
        """
        Initialize all connections with configurable required services
        
        Args:
            required_services: List of service names that must succeed for initialization to pass.
                              If None, defaults to ['timescaledb'] (critical services only)
        """
        if self._initialized:
            logger.info("Connection manager already initialized")
            return
            
        if required_services is None:
            required_services = ['timescaledb']  # Only TimescaleDB is critical by default
            
        logger.info(f"Initializing connection manager in {service_discovery.environment.value} environment")
        logger.info(f"Required services: {required_services}")
        
        failed_services = {}
        successful_services = []

        # Initialize Redis connection
        await self._initialize_redis(failed_services, successful_services)
        
        # Initialize MongoDB connection
        await self._initialize_mongodb(failed_services, successful_services)
        
        # Initialize TimescaleDB connections
        await self._initialize_timescaledb(failed_services, successful_services)
        
        # Initialize RabbitMQ connection
        await self._initialize_rabbitmq(failed_services, successful_services)
        
        # Check if critical services are available
        self._validate_initialization(failed_services, successful_services, required_services)
        self._initialized = True
        
    async def _initialize_redis(self, failed_services: Dict, successful_services: List):
        """Initialize Redis connection"""
        try:
            self.redis = get_redis_client()
            if self.redis:
                # Test Redis connection
                await self.redis.ping()
                logger.info("✅ Redis connection successful")
                successful_services.append("redis")
            else:
                raise Exception("Redis client returned None")
        except Exception as e:
            logger.error("❌ Redis connection failed: %s", e)
            self.redis = None
            failed_services["redis"] = str(e)

    async def _initialize_mongodb(self, failed_services: Dict, successful_services: List):
        """Initialize MongoDB connection"""
        try:
            self.mongodb = get_mongo_client()
            await asyncio.wait_for(self.mongodb.admin.command("ping"), timeout=5.0)
            logger.info("✅ MongoDB connection successful")
            successful_services.append("mongodb")
        except Exception as e:
            logger.error("❌ MongoDB connection failed: %s", e)
            self.mongodb = None
            failed_services["mongodb"] = str(e)

    async def _initialize_timescaledb(self, failed_services: Dict, successful_services: List):
        """Initialize TimescaleDB connections (both async and sync)"""
        # Async TimescaleDB
        try:
            self.timescaledb = get_timescaledb_session()
            async with self.timescaledb() as session:
                await session.execute(text("SELECT 1"))
            logger.info("✅ TimescaleDB (async) connection successful")
            successful_services.append("timescaledb_async")
        except Exception as e:
            logger.error("❌ TimescaleDB (async) connection failed: %s", e)
            self.timescaledb = None
            failed_services["timescaledb_async"] = str(e)

        # Sync TimescaleDB
        try:
            self.timescaledb_sync = get_sync_timescaledb_session()
            # Test sync connection
            with self.timescaledb_sync() as session:
                session.execute(text("SELECT 1"))
            logger.info("✅ TimescaleDB (sync) connection successful")
            successful_services.append("timescaledb_sync")
        except Exception as e:
            logger.error("❌ TimescaleDB (sync) connection failed: %s", e)
            self.timescaledb_sync = None
            failed_services["timescaledb_sync"] = str(e)

    async def _initialize_rabbitmq(self, failed_services: Dict, successful_services: List):
        """Initialize RabbitMQ connection"""
        try:
            self.rabbitmq = await get_rabbitmq_connection()
            # Test connection
            channel = await self.rabbitmq.channel()
            await channel.close()
            logger.info("✅ RabbitMQ connection successful")
            successful_services.append("rabbitmq")
        except Exception as e:
            logger.error("❌ RabbitMQ connection failed: %s", e)
            self.rabbitmq = None
            failed_services["rabbitmq"] = str(e)

    def _validate_initialization(self, failed_services: Dict, successful_services: List, required_services: List):
        """Validate that required services are available"""
        logger.info(f"Successful connections: {successful_services}")
        if failed_services:
            logger.warning(f"Failed connections: {failed_services}")

        # Check if any required services failed
        failed_required = []
        for required_service in required_services:
            service_available = False
            
            # Check if the required service or any variant is available
            if required_service == "timescaledb":
                service_available = "timescaledb_async" in successful_services or "timescaledb_sync" in successful_services
            else:
                service_available = required_service in successful_services
                
            if not service_available:
                failed_required.append(required_service)

        # Fail initialization if critical services are down (unless in testing mode)
        if failed_required and not self._testing_mode:
            raise RuntimeError(f"🚨 Startup failed: Required services unavailable: {', '.join(failed_required)}")
        elif failed_required and self._testing_mode:
            logger.warning(f"⚠️ Testing mode: Required services failed but continuing: {', '.join(failed_required)}")

    async def health_check(self) -> Dict[str, Dict[str, str]]:
        """Perform health check on all connections"""
        health_status = {}
        
        # Check Redis
        try:
            if self.redis:
                await self.redis.ping()
                health_status["redis"] = {"status": "healthy", "message": "Connection OK"}
            else:
                health_status["redis"] = {"status": "unavailable", "message": "Redis not initialized"}
        except Exception as e:
            health_status["redis"] = {"status": "unhealthy", "message": str(e)}

        # Check MongoDB
        try:
            if self.mongodb:
                await asyncio.wait_for(self.mongodb.admin.command("ping"), timeout=3.0)
                health_status["mongodb"] = {"status": "healthy", "message": "Connection OK"}
            else:
                health_status["mongodb"] = {"status": "unavailable", "message": "MongoDB not initialized"}
        except Exception as e:
            health_status["mongodb"] = {"status": "unhealthy", "message": str(e)}

        # Check TimescaleDB (async)
        try:
            if self.timescaledb:
                async with self.timescaledb() as session:
                    await session.execute(text("SELECT 1"))
                health_status["timescaledb_async"] = {"status": "healthy", "message": "Connection OK"}
            else:
                health_status["timescaledb_async"] = {"status": "unavailable", "message": "TimescaleDB async not initialized"}
        except Exception as e:
            health_status["timescaledb_async"] = {"status": "unhealthy", "message": str(e)}

        # Check TimescaleDB (sync)
        try:
            if self.timescaledb_sync:
                with self.timescaledb_sync() as session:
                    session.execute(text("SELECT 1"))
                health_status["timescaledb_sync"] = {"status": "healthy", "message": "Connection OK"}
            else:
                health_status["timescaledb_sync"] = {"status": "unavailable", "message": "TimescaleDB sync not initialized"}
        except Exception as e:
            health_status["timescaledb_sync"] = {"status": "unhealthy", "message": str(e)}

        # Check RabbitMQ
        try:
            if self.rabbitmq:
                if not self.rabbitmq.is_closed:
                    health_status["rabbitmq"] = {"status": "healthy", "message": "Connection OK"}
                else:
                    health_status["rabbitmq"] = {"status": "unhealthy", "message": "Connection closed"}
            else:
                health_status["rabbitmq"] = {"status": "unavailable", "message": "RabbitMQ not initialized"}
        except Exception as e:
            health_status["rabbitmq"] = {"status": "unhealthy", "message": str(e)}

        return health_status

    def get_sync_timescaledb_session(self):
        """Return the session factory for sync TimescaleDB"""
        if not self.timescaledb_sync:
            raise RuntimeError("Sync TimescaleDB session not initialized")
        return self.timescaledb_sync

    def get_async_timescaledb_session(self):
        """Return the session factory for async TimescaleDB"""
        if not self.timescaledb:
            raise RuntimeError("Async TimescaleDB session not initialized")
        return self.timescaledb

    def get_redis_connection(self):
        """Return Redis connection"""
        if not self.redis:
            raise RuntimeError("Redis connection not initialized")
        return self.redis

    async def get_redis_connection_async(self):
        """Return async Redis connection"""
        if not self.redis:
            raise RuntimeError("Redis connection not initialized")
        return self.redis
    
    def get_rabbitmq_connection(self):
        """Return RabbitMQ connection or None if not available"""
        if not self.rabbitmq:
            logger.debug("RabbitMQ connection not available")
            return None
        return self.rabbitmq

    def get_mongo_connection(self):
        """Return MongoDB connection or None if not available"""
        if not self.mongodb:
            logger.debug("MongoDB connection not available")
            return None
        return self.mongodb

    async def close(self):
        """Close all connections gracefully"""
        logger.info("Closing all connections...")
        
        if self.redis:
            try:
                await self.redis.aclose()
                logger.info("✅ Redis connection closed")
            except Exception as e:
                logger.error(f"Error closing Redis connection: {e}")

        if self.rabbitmq:
            try:
                await self.rabbitmq.close()
                logger.info("✅ RabbitMQ connection closed")
            except Exception as e:
                logger.error(f"Error closing RabbitMQ connection: {e}")

        if self.mongodb:
            try:
                self.mongodb.close()
                logger.info("✅ MongoDB connection closed")
            except Exception as e:
                logger.error(f"Error closing MongoDB connection: {e}")

        # Note: SQLAlchemy engines are closed automatically when the process ends
        logger.info("✅ All connections closed")
        self._initialized = False


# Global connection manager instance
connection_manager = ConnectionManager()