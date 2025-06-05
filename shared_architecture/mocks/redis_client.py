class MockRedisClient:
    def __init__(self):
        self._store = {}

    def get(self, key):
        return self._store.get(key)

    def set(self, key, value):
        self._store[key] = value
        return True

    def lpop(self, key):
        if key not in self._store or not isinstance(self._store[key], list):
            return None
        if self._store[key]:
            return self._store[key].pop(0)
        return None

    def rpush(self, key, *values):
        if key not in self._store:
            self._store[key] = []
        self._store[key].extend(values)
        return len(self._store[key])

    def delete(self, key):
        return self._store.pop(key, None)

    def close(self):
        self._store.clear()


# Singleton
_mock_redis_client = MockRedisClient()

def get_redis_client():
    return _mock_redis_client
