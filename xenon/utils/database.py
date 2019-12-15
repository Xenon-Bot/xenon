from motor.motor_asyncio import AsyncIOMotorClient


class DatabaseClient(AsyncIOMotorClient):
    def __init__(self, *args, cache_size=1000, **kwargs):
        self.cache_size = cache_size
        self.cache = []
        super().__init__(*args, **kwargs)

    def _get_from_cache(self, filter):
        for f, r in self.cache:
            if f == filter:
                return r

    def _add_to_cache(self, filter, result):
        self.cache.append((filter, result))
        if len(self.cache) > self.cache_size:
            self.cache.pop(0)

    async def find_one(self, filter, *args, cache=False, **kwargs):
        if cache:
            cached = self._get_from_cache(filter)
            if cached:
                return cached

            else:
                result = await super().find_one(*args, **kwargs)
                if result:
                    self._add_to_cache(filter, result)

                return result

        else:
            return await super().find_one(*args, **kwargs)
