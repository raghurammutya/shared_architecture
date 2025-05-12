class RedisMock:
    def __init__(self):
        self.store = {}

    async def hset(self, key, field, value):
        self.store.setdefault(key, {})[field] = value

    async def hget(self, key, field):
        return self.store.get(key, {}).get(field)

    async def xadd(self, key, fields, id='*'):
        self.store.setdefault(key, []).append((id, fields))

    async def xrange(self, key, start='-', end='+'):
        return self.store.get(key, [])

    async def ping(self):
        return True
