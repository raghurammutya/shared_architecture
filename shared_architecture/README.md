# Shared Architecture for Stocksblitz Microservices

## Overview

`shared_architecture` is the foundational library for all Stocksblitz microservices. It centralizes common infrastructure concerns such as:

- ✅ Configuration Management
- ✅ Connection Management (Redis, TimescaleDB, RabbitMQ, MongoDB)
- ✅ Data Adapters with High-Performance Bulk Operations
- ✅ Logging and Metrics
- ✅ Health Checks
- ✅ Dynamic SQLAlchemy Model Generation
- ✅ Exception Handling
- ✅ Data Transfer Utilities (Redis ⇄ TimescaleDB, Redis ⇄ MongoDB)
- ✅ Keycloak Authentication Support

## Installation

Make sure you have installed this package via PyPI or GitHub Package Registry:

```bash
pip install shared_architecture
```

## Configuration Management

Reads from environment variables or Kubernetes configmaps.

```python
from shared_architecture.config.config_loader import config_loader
api_url = config_loader.get("API_URL", default="http://localhost")
```

## Connection Management

```python
from shared_architecture.connection_manager import connection_manager

connections = connection_manager.get_all_connections()
redis_client = connections["redis"]
timescaledb_session = connection_manager.create_timescaledb_session()
```

## Health Checks

```python
from shared_architecture.health_check import aggregate_health_check

status = aggregate_health_check()
print(status)  # { 'redis': 'healthy', 'timescaledb': 'healthy', ... }
```

## Logging and Metrics

```python
from shared_architecture.logging.logger import get_logger
logger = get_logger("my_service")
logger.info("Service started")
```

## Bulk Operations Examples

### ✅ TimescaleDB Bulk Insert

```python
from shared_architecture.utils.data_adapter_timescaledb import process_bulk_insert
from your_project.models import YourSQLAlchemyModel
from your_project.schemas import YourPydanticSchema

process_bulk_insert(session, YourSQLAlchemyModel, YourPydanticSchema, data_list)
```

### ✅ Redis Bulk Set/Get

```python
from shared_architecture.utils.data_adapter_redis import bulk_set, bulk_get

bulk_set(redis_client, {"key1": "value1", "key2": "value2"})
result = bulk_get(redis_client, ["key1", "key2"])
```

### ✅ MongoDB Bulk Insert/Update

```python
from shared_architecture.utils.data_adapter_mongodb import bulk_insert, bulk_update

bulk_insert(mongo_collection, [{"_id": "doc1", "field": "value"}])
```

## Data Transfer Utilities

### ✅ Redis ⇄ TimescaleDB

```python
from shared_architecture.utils.redis_timescaledb_transfer import redis_to_timescaledb
redis_to_timescaledb(redis_client, session, model, keys, schema_class)
```

### ✅ Redis ⇄ MongoDB

```python
from shared_architecture.utils.redis_mongodb_transfer import redis_to_mongodb
redis_to_mongodb(redis_client, mongo_collection, keys)
```

## Dynamic Model Generation

```python
from shared_architecture.utils.sqlalchemy_model_factory import generate_dynamic_model
DynamicModel = generate_dynamic_model("dynamic_table", {"field1": "str", "field2": "int"})
```

## Exception Handling

```python
from shared_architecture.exceptions import ValidationError
raise ValidationError("Invalid input data")
```

## Keycloak Authentication

```python
from shared_architecture.utils.keycloak_helper import validate_token
user_info = validate_token(jwt_token)
```

## Running Tests

Use the provided test runner:

```bash
python run_all_tests.py
```

Or run manually:

```bash
pytest -v --tb=short tests/
```

---

## Need Help?

Contact the platform team or refer to internal documentation for further assistance.
