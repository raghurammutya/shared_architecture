# 🧠 shared_architecture Documentation

This `docs/` folder contains developer-friendly guides to help teams adopt and extend the `shared_architecture` package.

## Included

- [mocking.md](mocking.md): How to enable mocks and test microservices
- [redis_usage.md](redis_usage.md): Accessing Redis and RedisMock
- [config_examples.md](config_examples.md): Best practices for environment config

## Usage

All microservices should:

```python
from shared_architecture.utils import connection_manager
```

Then call:

```python
redis = connection_manager.get_redis()
```

## Developer Tips

- Use `USE_MOCKS=true` for unit testing
- Extend `shared_architecture.mocks` when adding features
- Centralize any shared utility or client into this package

Happy coding!