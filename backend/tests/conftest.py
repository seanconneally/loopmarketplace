import asyncio
import selectors
import sys

import pytest
import pytest_asyncio

from app.core.redis import client


@pytest.hookimpl(optionalhook=True)
def pytest_asyncio_loop_factories(config, item):
    if sys.platform == "win32":
        return {"selector": lambda: asyncio.SelectorEventLoop(selectors.SelectSelector())}
    return {"default": asyncio.new_event_loop}


@pytest_asyncio.fixture(autouse=True)
async def close_redis_between_test_loops():
    yield
    await client.aclose()
