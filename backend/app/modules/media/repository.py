from typing import cast
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.media.models import MediaAsset


class MediaRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get(self, asset: UUID, lock: bool = False) -> MediaAsset | None:
        query = select(MediaAsset).where(MediaAsset.id == asset)
        return cast(
            MediaAsset | None,
            await self.session.scalar(
                query.with_for_update().execution_options(populate_existing=True) if lock else query
            ),
        )

    async def by_listing(self, listing: UUID, lock: bool = False) -> MediaAsset | None:
        query = select(MediaAsset).where(MediaAsset.listing_id == listing)
        return cast(
            MediaAsset | None,
            await self.session.scalar(
                query.with_for_update().execution_options(populate_existing=True) if lock else query
            ),
        )

    async def duplicate(self, asset: UUID, perceptual_hash: str) -> bool:
        return bool(
            await self.session.scalar(
                select(MediaAsset.id)
                .where(
                    MediaAsset.id != asset,
                    MediaAsset.perceptual_hash == perceptual_hash,
                    MediaAsset.status == "ready",
                )
                .limit(1)
            )
        )
