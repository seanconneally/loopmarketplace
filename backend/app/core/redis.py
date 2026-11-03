from collections.abc import Awaitable, Callable
from typing import Any, cast

from redis.asyncio import Redis
from redis.asyncio.retry import Retry
from redis.backoff import NoBackoff

from app.core.config import settings

client: Redis = Redis.from_url(
    settings().redis_url,
    decode_responses=True,
    socket_connect_timeout=settings().redis_connect_timeout,
    socket_timeout=settings().redis_socket_timeout,
    max_connections=settings().redis_max_connections,
    health_check_interval=30,
    # Retrying an INCR or GETDEL after a lost response could apply it twice.
    retry=Retry(NoBackoff(), 0),
)


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
