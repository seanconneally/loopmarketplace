from prometheus_client import Gauge
from sqlalchemy import func, select

from app.core.db import sessions, utcnow
from app.core.outbox import DeadLetter, Outbox

PENDING = Gauge("motorloop_outbox_pending", "Durable background work awaiting completion")
OLDEST = Gauge("motorloop_outbox_oldest_seconds", "Age of oldest pending work")
DEAD = Gauge("motorloop_dead_letters", "Unreplayed dead letters")
WEBSOCKETS = Gauge("motorloop_websockets", "Active WebSockets in this API process")


async def collect_work_metrics() -> None:
    async with sessions() as session:
        count, oldest = (
            await session.execute(
                select(func.count(), func.min(Outbox.created_at)).where(
                    Outbox.completed_at.is_(None)
                )
            )
        ).one()
        PENDING.set(count)
        OLDEST.set(max(0, (utcnow() - oldest).total_seconds()) if oldest else 0)
        DEAD.set(
            await session.scalar(
                select(func.count()).select_from(DeadLetter).where(DeadLetter.replayed_at.is_(None))
            )
            or 0
        )
