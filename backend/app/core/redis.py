from collections.abc import Awaitable, Callable
from typing import Any, cast

from redis.asyncio import Redis

from app.core.config import settings

client: Redis = Redis.from_url(settings().redis_url, decode_responses=True)


async def command(*arguments: str | int) -> Any:
    """Isolate Redis 6's incomplete async command typing at the adapter boundary."""
    execute = cast(Callable[..., Awaitable[Any]], client.execute_command)
    return await execute(*arguments)


async def rate_limit(key: str, limit: int, seconds: int = 60) -> bool:
    result = await command(
        "EVAL",
        "local n=redis.call('INCR',KEYS[1]); if n==1 then redis.call('EXPIRE',KEYS[1],ARGV[1]) end; return n",
        1,
        f"rate:{key}",
        str(seconds),
    )
    return int(result) <= limit
