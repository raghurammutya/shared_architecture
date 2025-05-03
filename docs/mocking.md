# 🧪 Mocks in shared_architecture

This document describes the mock client architecture used to test microservices without real infrastructure.

## Mocks Available

- Redis: `RedisMock`
- MongoDB: `MongoMock`
- TimescaleDB: `MagicMock`
- RabbitMQ: `RabbitMQMock`

## How to Enable

Set this in your `.env` or your test setup:

```bash
USE_MOCKS=true
```

All infrastructure connectors will now return mocks.

## Writing Tests

```python
def test_with_mocked_redis():
    redis = connection_manager.get_redis()
    await redis.hset("tick:NSE:NIFTY", "price", "21000")
```

Avoid importing mocks directly. Always access via `connection_manager`.