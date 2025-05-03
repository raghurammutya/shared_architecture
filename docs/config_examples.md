# ⚙️ Config Loading in shared_architecture

## Using `get_env()` Utility

Use this helper for all environment variable access:

```python
from shared_architecture.config.config_loader import get_env

REDIS_URL = get_env("REDIS_URL", "redis://localhost:6379")
USE_TLS = get_env("USE_TLS", "false", bool)
```

## Advantages

- Typed conversion
- Automatic defaulting
- Raises error on missing required keys
- Avoids silent bugs due to incorrect env configuration