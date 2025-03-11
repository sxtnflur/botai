from config import settings
from aiocache import Cache, cached
from aiocache.serializers import PickleSerializer

# cache = Cache.from_url(settings.redis.url)

default_cached = cached(
                        ttl=settings.cache_ttl,
                        cache=Cache.MEMORY, namespace="tgbot",
                        serializer=PickleSerializer(),
                        # client=redis.Redis.from_url(settings.redis.url),
                        )