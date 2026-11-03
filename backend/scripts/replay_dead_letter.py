"""Explicit local operator replay: pass a dead-letter UUID and a reason."""

import asyncio
import sys
from uuid import UUID

from app.core.db import sessions, utcnow
from app.core.outbox import DeadLetter, Outbox
from app.modules.media.service import MediaService


async def replay(dead_id: UUID, reason: str) -> None:
    if len(reason.strip()) < 10:
        raise ValueError("A meaningful replay reason is required")
    async with sessions() as session:
        dead = await session.get(DeadLetter, dead_id)
        if dead is None or dead.replayed_at:
            raise ValueError("Dead letter missing or already replayed")
        event = await session.get(Outbox, dead.outbox_id)
        if event is None:
            raise ValueError("Original event is missing")
        dead.replayed_at = utcnow()
        payload = dict(event.payload)
        if event.event_type == "media.process":
            payload["generation"] = await MediaService(session).retry_failed(
                UUID(event.payload["asset_id"])
            )
        # Keep the original event/attempt record; a new outbox item gets a new delivery budget.
        session.add(
            Outbox(
                event_type=event.event_type,
                payload={
                    **payload,
                    "_delivery_key": event.payload.get("_delivery_key", str(event.id)),
                },
                last_error=f"operator_replay:{dead.id}; reason:{reason}",
            )
        )
        await session.commit()
        print(f"Replayed {dead.id}; reason retained with the new durable outbox record.")


if __name__ == "__main__":
    asyncio.run(replay(UUID(sys.argv[1]), sys.argv[2]))
