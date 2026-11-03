import asyncio
import random
import time
from datetime import timedelta
from pathlib import Path
from uuid import UUID

import structlog
from sqlalchemy import or_, select

from app.core.db import sessions, utcnow
from app.core.outbox import DeadLetter, Outbox
from app.worker import celery

log = structlog.get_logger()


async def dispatch() -> None:
    from app.modules.media.service import MediaService

    async with sessions() as session:
        now = utcnow()
        rows = list(
            await session.scalars(
                select(Outbox)
                .where(
                    Outbox.completed_at.is_(None),
                    Outbox.available_at <= now,
                    or_(Outbox.lease_until.is_(None), Outbox.lease_until < now),
                )
                .order_by(Outbox.available_at)
                .limit(50)
                .with_for_update(skip_locked=True)
            )
        )
        dispatches = []
        for row in rows:
            if row.attempts >= 5:
                row.completed_at = now
                if row.event_type == "media.process":
                    await MediaService(session).fail(
                        UUID(row.payload["asset_id"]), row.payload.get("generation")
                    )
                session.add(
                    DeadLetter(
                        outbox_id=row.id,
                        event_type=row.event_type,
                        error_code=row.last_error or "lease_expired",
                    )
                )
                continue
            row.attempts += 1
            row.lease_until = now + timedelta(minutes=6)
            row.available_at = now + timedelta(seconds=min(300, 2**row.attempts) + random.random())
            dispatches.append((row.id, "media" if row.event_type == "media.process" else "default"))
        await session.commit()  # A crash after this commit is recovered after the lease.
        for event_id, queue in dispatches:
            try:
                await asyncio.to_thread(
                    celery.send_task, "motorloop.execute", args=[str(event_id)], queue=queue
                )
            except Exception as exc:
                log.warning("enqueue_failed", event_id=str(event_id), error_type=type(exc).__name__)


async def main() -> None:
    from app.modules.viewings.service import ViewingService

    while True:
        try:
            await dispatch()
            async with sessions() as session:
                await ViewingService(session).schedule_reminders()
                await session.commit()
            Path("/tmp/relay-health").write_text(str(time.time()))
        except Exception as exc:
            log.error("relay_iteration_failed", error_type=type(exc).__name__)
        await asyncio.sleep(1)


if __name__ == "__main__":
    asyncio.run(main())
