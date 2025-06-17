# shared_architecture/resilience/rate_limiter.py
"""
Advanced rate limiting implementation with multiple algorithms and Redis backend.
Provides protection against abuse and ensures fair resource usage.
"""

import asyncio
import time
import redis
import json
import hashlib
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List, Tuple, Union, Callable
from dataclasses import dataclass, asdict
from enum import Enum
from abc import ABC, abstractmethod

from shared_architecture.utils.enhanced_logging import get_logger
from shared_architecture.monitoring.metrics_collector import MetricsCollector, trade_metrics

logger = get_logger(__name__)

class RateLimitAlgorithm(Enum):
    """Rate limiting algorithms."""
    TOKEN_BUCKET = "token_bucket"
    SLIDING_WINDOW = "sliding_window"
    FIXED_WINDOW = "fixed_window"
    LEAKY_BUCKET = "leaky_bucket"

@dataclass
class RateLimitConfig:
    """Configuration for rate limiting."""
    requests_per_window: int  # Number of requests allowed per window
    window_size: int  # Window size in seconds
    algorithm: RateLimitAlgorithm = RateLimitAlgorithm.SLIDING_WINDOW
    burst_requests: Optional[int] = None  # For token bucket, allows bursts
    leak_rate: Optional[float] = None  # For leaky bucket, requests per second
    name: str = "rate_limiter"
    redis_key_prefix: str = "rate_limit"

@dataclass
class RateLimitResult:
    """Result of a rate limit check."""
    allowed: bool
    remaining: int
    reset_time: datetime
    retry_after: Optional[int] = None  # Seconds to wait before retrying
    total_requests: int = 0
    window_start: Optional[datetime] = None

class RateLimitExceededError(Exception):
    """Exception raised when rate limit is exceeded."""
    def __init__(self, message: str, result: RateLimitResult):
        super().__init__(message)
        self.result = result

class BaseRateLimiter(ABC):
    """Base class for rate limiters."""
    
    def __init__(self, config: RateLimitConfig, redis_client: Optional[redis.Redis] = None):
        self.config = config
        self.redis_client = redis_client
        self.logger = get_logger(f"rate_limiter.{config.name}")
        
        # Metrics
        self.metrics_collector = MetricsCollector.get_instance()
        self.requests_counter = self.metrics_collector.counter(
            "rate_limit_requests_total",
            "Total requests processed by rate limiter",
            tags={"limiter": config.name}
        )
        self.allowed_counter = self.metrics_collector.counter(
            "rate_limit_allowed_total",
            "Total requests allowed by rate limiter",
            tags={"limiter": config.name}
        )
        self.blocked_counter = self.metrics_collector.counter(
            "rate_limit_blocked_total",
            "Total requests blocked by rate limiter",
            tags={"limiter": config.name}
        )
        self.remaining_gauge = self.metrics_collector.gauge(
            "rate_limit_remaining",
            "Remaining requests in current window",
            tags={"limiter": config.name}
        )
    
    @abstractmethod
    async def check_rate_limit(self, key: str) -> RateLimitResult:
        """Check if request is within rate limit."""
        pass
    
    def _get_redis_key(self, key: str) -> str:
        """Generate Redis key for the rate limiter."""
        return f"{self.config.redis_key_prefix}:{self.config.name}:{key}"

class SlidingWindowRateLimiter(BaseRateLimiter):
    """Sliding window rate limiter using Redis sorted sets."""
    
    async def check_rate_limit(self, key: str) -> RateLimitResult:
        """Check rate limit using sliding window algorithm."""
        self.requests_counter.increment(tags={"limiter": self.config.name})
        
        if not self.redis_client:
            # Fallback to allowing requests if Redis is not available
            self.logger.warning("Redis not available, allowing request")
            self.allowed_counter.increment(tags={"limiter": self.config.name})
            return RateLimitResult(
                allowed=True,
                remaining=self.config.requests_per_window - 1,
                reset_time=datetime.utcnow() + timedelta(seconds=self.config.window_size)
            )
        
        redis_key = self._get_redis_key(key)
        current_time = time.time()
        window_start = current_time - self.config.window_size
        
        try:
            # Use Redis pipeline for atomic operations
            pipe = self.redis_client.pipeline()
            
            # Remove old entries outside the window
            pipe.zremrangebyscore(redis_key, 0, window_start)
            
            # Count current requests in window
            pipe.zcard(redis_key)
            
            # Add current request
            pipe.zadd(redis_key, {str(current_time): current_time})
            
            # Set expiration
            pipe.expire(redis_key, self.config.window_size + 1)
            
            results = pipe.execute()
            current_count = results[1]
            
            # Check if limit exceeded
            if current_count >= self.config.requests_per_window:
                # Remove the request we just added
                self.redis_client.zrem(redis_key, str(current_time))
                
                self.blocked_counter.increment(tags={"limiter": self.config.name})
                self.remaining_gauge.set(0, tags={"limiter": self.config.name})
                
                # Calculate retry after
                oldest_in_window = self.redis_client.zrange(redis_key, 0, 0, withscores=True)
                retry_after = None
                if oldest_in_window:
                    oldest_time = oldest_in_window[0][1]
                    retry_after = int(oldest_time + self.config.window_size - current_time + 1)
                
                return RateLimitResult(
                    allowed=False,
                    remaining=0,
                    reset_time=datetime.fromtimestamp(current_time + self.config.window_size),
                    retry_after=retry_after,
                    total_requests=current_count,
                    window_start=datetime.fromtimestamp(window_start)
                )
            
            # Request allowed
            remaining = self.config.requests_per_window - current_count - 1
            self.allowed_counter.increment(tags={"limiter": self.config.name})
            self.remaining_gauge.set(remaining, tags={"limiter": self.config.name})
            
            return RateLimitResult(
                allowed=True,
                remaining=remaining,
                reset_time=datetime.fromtimestamp(current_time + self.config.window_size),
                total_requests=current_count + 1,
                window_start=datetime.fromtimestamp(window_start)
            )
            
        except Exception as e:
            self.logger.error(f"Redis error in rate limiter: {e}", exc_info=True)
            # Fallback to allowing requests on Redis errors
            self.allowed_counter.increment(tags={"limiter": self.config.name})
            return RateLimitResult(
                allowed=True,
                remaining=self.config.requests_per_window - 1,
                reset_time=datetime.utcnow() + timedelta(seconds=self.config.window_size)
            )

class TokenBucketRateLimiter(BaseRateLimiter):
    """Token bucket rate limiter using Redis."""
    
    def __init__(self, config: RateLimitConfig, redis_client: Optional[redis.Redis] = None):
        super().__init__(config, redis_client)
        # For token bucket, burst_requests is the bucket capacity
        self.bucket_capacity = config.burst_requests or config.requests_per_window
        # Refill rate is requests per window divided by window size
        self.refill_rate = config.requests_per_window / config.window_size
    
    async def check_rate_limit(self, key: str) -> RateLimitResult:
        """Check rate limit using token bucket algorithm."""
        self.requests_counter.increment(tags={"limiter": self.config.name})
        
        if not self.redis_client:
            self.allowed_counter.increment(tags={"limiter": self.config.name})
            return RateLimitResult(
                allowed=True,
                remaining=self.bucket_capacity - 1,
                reset_time=datetime.utcnow() + timedelta(seconds=self.config.window_size)
            )
        
        redis_key = self._get_redis_key(key)
        current_time = time.time()
        
        try:
            # Lua script for atomic token bucket operations
            lua_script = """
            local key = KEYS[1]
            local capacity = tonumber(ARGV[1])
            local refill_rate = tonumber(ARGV[2])
            local current_time = tonumber(ARGV[3])
            local tokens_requested = tonumber(ARGV[4])
            
            local bucket = redis.call('HMGET', key, 'tokens', 'last_refill')
            local tokens = tonumber(bucket[1]) or capacity
            local last_refill = tonumber(bucket[2]) or current_time
            
            -- Calculate tokens to add based on time elapsed
            local time_elapsed = current_time - last_refill
            local tokens_to_add = time_elapsed * refill_rate
            tokens = math.min(capacity, tokens + tokens_to_add)
            
            -- Check if enough tokens available
            if tokens >= tokens_requested then
                tokens = tokens - tokens_requested
                redis.call('HMSET', key, 'tokens', tokens, 'last_refill', current_time)
                redis.call('EXPIRE', key, 3600)  -- 1 hour expiration
                return {1, tokens, current_time}  -- allowed, remaining tokens, last_refill
            else
                redis.call('HMSET', key, 'tokens', tokens, 'last_refill', current_time)
                redis.call('EXPIRE', key, 3600)
                return {0, tokens, current_time}  -- not allowed, remaining tokens, last_refill
            end
            """
            
            result = self.redis_client.eval(
                lua_script,
                1,
                redis_key,
                self.bucket_capacity,
                self.refill_rate,
                current_time,
                1  # requesting 1 token
            )
            
            allowed = bool(result[0])
            remaining_tokens = int(result[1])
            
            if allowed:
                self.allowed_counter.increment(tags={"limiter": self.config.name})
                self.remaining_gauge.set(remaining_tokens, tags={"limiter": self.config.name})
                
                return RateLimitResult(
                    allowed=True,
                    remaining=remaining_tokens,
                    reset_time=datetime.fromtimestamp(current_time + self.config.window_size)
                )
            else:
                self.blocked_counter.increment(tags={"limiter": self.config.name})
                self.remaining_gauge.set(0, tags={"limiter": self.config.name})
                
                # Calculate when next token will be available
                time_for_token = 1.0 / self.refill_rate
                retry_after = int(time_for_token) + 1
                
                return RateLimitResult(
                    allowed=False,
                    remaining=0,
                    reset_time=datetime.fromtimestamp(current_time + time_for_token),
                    retry_after=retry_after
                )
                
        except Exception as e:
            self.logger.error(f"Redis error in token bucket rate limiter: {e}", exc_info=True)
            self.allowed_counter.increment(tags={"limiter": self.config.name})
            return RateLimitResult(
                allowed=True,
                remaining=self.bucket_capacity - 1,
                reset_time=datetime.utcnow() + timedelta(seconds=self.config.window_size)
            )

class FixedWindowRateLimiter(BaseRateLimiter):
    """Fixed window rate limiter using Redis."""
    
    async def check_rate_limit(self, key: str) -> RateLimitResult:
        """Check rate limit using fixed window algorithm."""
        self.requests_counter.increment(tags={"limiter": self.config.name})
        
        if not self.redis_client:
            self.allowed_counter.increment(tags={"limiter": self.config.name})
            return RateLimitResult(
                allowed=True,
                remaining=self.config.requests_per_window - 1,
                reset_time=datetime.utcnow() + timedelta(seconds=self.config.window_size)
            )
        
        current_time = int(time.time())
        window_start = (current_time // self.config.window_size) * self.config.window_size
        redis_key = f"{self._get_redis_key(key)}:{window_start}"
        
        try:
            # Atomic increment and check
            pipe = self.redis_client.pipeline()
            pipe.incr(redis_key)
            pipe.expire(redis_key, self.config.window_size)
            results = pipe.execute()
            
            current_count = results[0]
            
            if current_count > self.config.requests_per_window:
                self.blocked_counter.increment(tags={"limiter": self.config.name})
                self.remaining_gauge.set(0, tags={"limiter": self.config.name})
                
                # Calculate time until next window
                next_window = window_start + self.config.window_size
                retry_after = next_window - current_time
                
                return RateLimitResult(
                    allowed=False,
                    remaining=0,
                    reset_time=datetime.fromtimestamp(next_window),
                    retry_after=retry_after,
                    total_requests=current_count,
                    window_start=datetime.fromtimestamp(window_start)
                )
            
            remaining = self.config.requests_per_window - current_count
            self.allowed_counter.increment(tags={"limiter": self.config.name})
            self.remaining_gauge.set(remaining, tags={"limiter": self.config.name})
            
            return RateLimitResult(
                allowed=True,
                remaining=remaining,
                reset_time=datetime.fromtimestamp(window_start + self.config.window_size),
                total_requests=current_count,
                window_start=datetime.fromtimestamp(window_start)
            )
            
        except Exception as e:
            self.logger.error(f"Redis error in fixed window rate limiter: {e}", exc_info=True)
            self.allowed_counter.increment(tags={"limiter": self.config.name})
            return RateLimitResult(
                allowed=True,
                remaining=self.config.requests_per_window - 1,
                reset_time=datetime.utcnow() + timedelta(seconds=self.config.window_size)
            )

class RateLimiterManager:
    """Manager for multiple rate limiters with hierarchical limits."""
    
    def __init__(self, redis_client: Optional[redis.Redis] = None):
        self.redis_client = redis_client
        self.limiters: Dict[str, BaseRateLimiter] = {}
        self.logger = get_logger(__name__)
    
    def add_limiter(self, config: RateLimitConfig) -> BaseRateLimiter:
        """Add a rate limiter."""
        if config.algorithm == RateLimitAlgorithm.SLIDING_WINDOW:
            limiter = SlidingWindowRateLimiter(config, self.redis_client)
        elif config.algorithm == RateLimitAlgorithm.TOKEN_BUCKET:
            limiter = TokenBucketRateLimiter(config, self.redis_client)
        elif config.algorithm == RateLimitAlgorithm.FIXED_WINDOW:
            limiter = FixedWindowRateLimiter(config, self.redis_client)
        else:
            raise ValueError(f"Unsupported rate limit algorithm: {config.algorithm}")
        
        self.limiters[config.name] = limiter
        self.logger.info(f"Added rate limiter: {config.name} ({config.algorithm.value})")
        return limiter
    
    def get_limiter(self, name: str) -> Optional[BaseRateLimiter]:
        """Get a rate limiter by name."""
        return self.limiters.get(name)
    
    async def check_limits(self, limiters: List[str], key: str) -> Tuple[bool, List[RateLimitResult]]:
        """Check multiple rate limiters and return if all pass."""
        results = []
        
        for limiter_name in limiters:
            limiter = self.limiters.get(limiter_name)
            if not limiter:
                self.logger.warning(f"Rate limiter not found: {limiter_name}")
                continue
            
            result = await limiter.check_rate_limit(key)
            results.append(result)
            
            if not result.allowed:
                # If any limiter blocks, stop checking
                break
        
        all_allowed = all(result.allowed for result in results)
        return all_allowed, results
    
    def create_key(self, user_id: str, endpoint: str = "", organization_id: str = "") -> str:
        """Create a rate limiting key from user and context information."""
        key_parts = [user_id]
        if organization_id:
            key_parts.append(organization_id)
        if endpoint:
            key_parts.append(endpoint)
        
        return ":".join(key_parts)

# Rate limiting decorators
def rate_limit(limiter_names: Union[str, List[str]], key_func: Optional[Callable] = None):
    """Decorator for rate limiting functions."""
    if isinstance(limiter_names, str):
        limiter_names = [limiter_names]
    
    def decorator(func):
        async def async_wrapper(*args, **kwargs):
            manager = get_rate_limiter_manager()
            
            # Generate key
            if key_func:
                key = key_func(*args, **kwargs)
            else:
                # Default key generation from function arguments
                key = f"func:{func.__name__}"
                if args:
                    key += f":{str(args[0])[:50]}"  # Use first arg, truncated
            
            # Check rate limits
            allowed, results = await manager.check_limits(limiter_names, key)
            
            if not allowed:
                # Find the first blocking result
                blocking_result = next(r for r in results if not r.allowed)
                raise RateLimitExceededError(
                    f"Rate limit exceeded for {func.__name__}",
                    blocking_result
                )
            
            return await func(*args, **kwargs)
        
        def sync_wrapper(*args, **kwargs):
            # For sync functions, run async part in event loop
            return asyncio.run(async_wrapper(*args, **kwargs))
        
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator

# Global rate limiter manager
_rate_limiter_manager: Optional[RateLimiterManager] = None

def get_rate_limiter_manager() -> RateLimiterManager:
    """Get the global rate limiter manager."""
    global _rate_limiter_manager
    if _rate_limiter_manager is None:
        # Initialize with Redis if available
        try:
            import os
            redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
            redis_client = redis.Redis.from_url(redis_url, decode_responses=True)
            redis_client.ping()  # Test connection
        except Exception as e:
            logger.warning(f"Redis not available for rate limiting: {e}")
            redis_client = None
        
        _rate_limiter_manager = RateLimiterManager(redis_client)
    
    return _rate_limiter_manager

def setup_default_rate_limiters():
    """Setup default rate limiters for common scenarios."""
    manager = get_rate_limiter_manager()
    
    # API rate limiting - 100 requests per minute
    api_config = RateLimitConfig(
        name="api_requests",
        requests_per_window=100,
        window_size=60,
        algorithm=RateLimitAlgorithm.SLIDING_WINDOW
    )
    manager.add_limiter(api_config)
    
    # Order placement - 10 orders per minute
    order_config = RateLimitConfig(
        name="order_placement",
        requests_per_window=10,
        window_size=60,
        algorithm=RateLimitAlgorithm.TOKEN_BUCKET,
        burst_requests=15  # Allow burst of 15
    )
    manager.add_limiter(order_config)
    
    # Data fetching - 50 requests per minute
    data_config = RateLimitConfig(
        name="data_fetching",
        requests_per_window=50,
        window_size=60,
        algorithm=RateLimitAlgorithm.SLIDING_WINDOW
    )
    manager.add_limiter(data_config)
    
    # Authentication - 5 attempts per minute
    auth_config = RateLimitConfig(
        name="authentication",
        requests_per_window=5,
        window_size=60,
        algorithm=RateLimitAlgorithm.FIXED_WINDOW
    )
    manager.add_limiter(auth_config)
    
    logger.info("Default rate limiters configured")

# Initialize default rate limiters
setup_default_rate_limiters()