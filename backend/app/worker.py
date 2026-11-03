import asyncio
import json
from datetime import timedelta
from typing import Any
from uuid import UUID

import structlog
from celery import Celery
from sqlalchemy import select

from app.core.config import settings
from app.core.db import sessions, utcnow
from app.core.outbox import DeadLetter, Outbox
from app.core.redis import client, command

celery = Celery("motorloop", broker=settings().redis_url)
celery.conf.update(
    task_serializer="json",
    accept_content=["json"],
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    worker_prefetch_multiplier=1,
    broker_transport_options={"visibility_timeout": 600},
    task_time_limit=300,
    broker_connection_retry_on_startup=True,
    broker_connection_timeout=3,
    task_publish_retry_policy={
        "max_retries": 2,
        "interval_start": 0,
        "interval_step": 0.5,
        "interval_max": 1,
    },
)
log = structlog.get_logger()


async def fan_out(event_type: str, payload: dict[str, Any]) -> None:
    recipients = payload.get("recipients", [payload["user_id"]] if "user_id" in payload else [])
    data = {
        key: value
        for key, value in payload.items()
        if key not in {"recipients", "user_id"} and not key.startswith("_")
    }
    envelope = json.dumps({"type": event_type, "data": data})
    for recipient in recipients:
        await client.publish(f"user:{recipient}", envelope)


async def process_event(event_id: UUID) -> None:
    from app.modules.listings.dealer import DealerService
    from app.modules.media.service import MediaService
    from app.modules.notifications.service import NotificationService
    from app.modules.users.service import UserService

    async with sessions() as session:
        event = await session.scalar(
            select(Outbox).where(Outbox.id == event_id).with_for_update(skip_locked=True)
        )
        if event is None or event.completed_at is not None:
            return
        try:
            if event.event_type == "media.process":
                await MediaService(session).process(
                    UUID(event.payload["asset_id"]), event.payload.get("generation")
                )
            elif event.event_type == "media.abort":
                from app.modules.media.provider import LocalVideoProvider

                await asyncio.to_thread(
                    LocalVideoProvider().abort,
                    event.payload["object_key"],
                    event.payload["upload_id"],
                )
            elif event.event_type == "dealer.import":
                await DealerService(session).process(UUID(event.payload["import_id"]))
            elif event.event_type == "feed.invalidate":
                await client.incr(f"feed:revision:{event.payload['region_id']}")
            elif event.event_type == "notification.requested":
                await NotificationService(session).deliver(
                    UUID(event.payload.get("_delivery_key", str(event.id))), event.payload
                )
            elif event.event_type == "analytics.received":
                ids = event.payload["seen_ids"]
                consented = (
                    await UserService(session).active(UUID(event.payload["user_id"]))
                ).analytics_consent
                if ids and consented:
                    await command("SADD", f"feed:seen:{event.payload['user_id']}", *ids)
                    await client.expire(f"feed:seen:{event.payload['user_id']}", 7 * 86400)
            elif event.event_type == "analytics.withdrawn":
                await client.delete(f"feed:seen:{event.payload['user_id']}")
            elif event.event_type in {
                "listing.status",
                "message.created",
                "message.read",
                "viewing.updated",
                "block.changed",
            }:
                await fan_out(event.event_type, event.payload)
            event.completed_at, event.lease_until = utcnow(), None
            await session.commit()
        except Exception as exc:
            await session.rollback()
            # Re-open after rollback so business effects cannot leak through a failed handler.
            failed = await session.scalar(
                select(Outbox).where(Outbox.id == event_id).with_for_update(skip_locked=True)
            )
            if failed and failed.completed_at is None:
                failed.last_error = type(exc).__name__  # Never persist provider bodies or secrets.
                failed.lease_until = None
                failed.available_at = utcnow() + timedelta(seconds=min(300, 2**failed.attempts))
                if failed.attempts >= 5:
                    failed.completed_at = utcnow()
                    if failed.event_type == "media.process":
                        await MediaService(session).fail(
                            UUID(failed.payload["asset_id"]), failed.payload.get("generation")
                        )
                    session.add(
                        DeadLetter(
                            outbox_id=failed.id,
                            event_type=failed.event_type,
                            error_code=type(exc).__name__,
                        )
                    )
                await session.commit()
            log.error("job_failed", event_id=str(event_id), error_type=type(exc).__name__)


@celery.task(name="motorloop.execute")  # type: ignore[untyped-decorator]
def execute(event_id: str) -> None:
    """Celery entry point; durable retry scheduling belongs to the outbox relay."""

    # Celery prefork processes reuse this function with fresh loops; release the Redis
    # client pool before closing each loop so no connection crosses event loops.
    async def run() -> None:
        try:
            await process_event(UUID(event_id))
        finally:
            await client.aclose()

    asyncio.run(run())
