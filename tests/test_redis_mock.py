# tests/test_redis_mock.py

import pytest
import asyncio
from shared_architecture.utils import connection_manager

@pytest.mark.asyncio
async def test_redis_tick_data_store_and_retrieve():
    redis = connection_manager.get_redis()
    await redis.hset("tick:NSE:NIFTY", "price", "22000")
    value = await redis.hget("tick:NSE:NIFTY", "price")
    assert value == "22000"

@pytest.mark.asyncio
async def test_redis_tick_data_not_found():
    redis = connection_manager.get_redis()
    value = await redis.hget("tick:NSE:INVALID", "price")
    assert value is None