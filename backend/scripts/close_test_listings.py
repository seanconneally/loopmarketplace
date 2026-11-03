"""Keep the public local feed tidy by closing only this project's synthetic browser listings."""

import asyncio

from sqlalchemy import select

from app.core.config import settings
from app.core.db import sessions
from app.modules.listings.models import Listing
from app.modules.listings.service import ListingService
from app.modules.users.service import UserService


async def close() -> None:
    if settings().app_env != "development":
        raise RuntimeError("This utility is development-only")
    async with sessions() as session:
        rows = list(
            await session.scalars(
                select(Listing).where(
                    Listing.title.startswith("Playwright car "), Listing.status == "live"
                )
            )
        )
        for row in rows:
            seller = await UserService(session).active(row.seller_id)
            if seller.name == "Playwright seller":
                await ListingService(session).sold(row.id, row.seller_id)
        await session.commit()


if __name__ == "__main__":
    asyncio.run(close())
