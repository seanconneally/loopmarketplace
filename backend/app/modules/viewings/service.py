from datetime import datetime, timedelta
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import utcnow
from app.core.errors import require
from app.core.outbox import emit
from app.core.paging import decode_cursor, encode_cursor
from app.modules.messaging.service import MessagingService
from app.modules.viewings.models import Viewing
from app.modules.viewings.repository import ViewingRepository
from app.modules.viewings.schemas import ViewingInput, ViewingPage, ViewingResponse, ViewingView


def ics_escape(value: str) -> str:
    return (
        value.replace("\\", "\\\\")
        .replace("\r", "")
        .replace("\n", "\\n")
        .replace(";", "\\;")
        .replace(",", "\\,")
    )


class ViewingService:
    def __init__(self, session: AsyncSession) -> None:
        self.session, self.repo = session, ViewingRepository(session)

    async def create(self, user: UUID, data: ViewingInput, key: str) -> ViewingView:
        """Propose a future viewing once and add its structured card to chat."""
        await MessagingService(self.session).member(data.conversation_id, user)
        require(data.starts_at > utcnow(), 422, "past_viewing", "Choose a future time.")
        scoped = f"{user}:{key}"
        result = await self.session.execute(
            insert(Viewing)
            .values(
                conversation_id=data.conversation_id,
                proposed_by=user,
                starts_at=data.starts_at,
                place=data.place,
                idempotency_key=scoped,
            )
            .on_conflict_do_nothing(index_elements=["conversation_id", "idempotency_key"])
            .returning(Viewing.id)
        )
        new_id = result.scalar_one_or_none()
        row = await self.session.scalar(
            select(Viewing).where(
                Viewing.conversation_id == data.conversation_id, Viewing.idempotency_key == scoped
            )
        )
        assert row is not None
        require(
            row.starts_at == data.starts_at and row.place == data.place,
            409,
            "idempotency_conflict",
            "This key belongs to another viewing.",
        )
        if new_id:
            await self._announce(row, user, "Viewing proposed")
        return ViewingView.model_validate(row)

    async def respond(self, viewing_id: UUID, user: UUID, data: ViewingResponse) -> ViewingView:
        """Apply one revision-checked response; counters preserve the previous proposal."""
        row = await self.repo.locked(viewing_id)
        require(row, 404, "viewing_missing", "Viewing not found.")
        assert row is not None
        await MessagingService(self.session).member(row.conversation_id, user)
        require(
            row.revision == data.revision,
            409,
            "viewing_changed",
            "This proposal changed. Refresh before responding.",
        )
        if data.action == "cancel":
            require(
                row.status in {"proposed", "accepted"},
                409,
                "invalid_state",
                "This viewing is already closed.",
            )
            row.status = "cancelled"
        else:
            require(
                row.status == "proposed" and row.proposed_by != user,
                409,
                "invalid_response",
                "Only the other party can respond to an open proposal.",
            )
            require(row.starts_at > utcnow(), 409, "past_viewing", "This proposed time has passed.")
            if data.action == "counter":
                require(
                    data.starts_at and data.starts_at > utcnow() and data.place,
                    422,
                    "counter_details_required",
                    "Choose a future time and public place.",
                )
                row.history = [
                    *row.history,
                    {
                        "starts_at": row.starts_at.isoformat(),
                        "place": row.place,
                        "proposed_by": str(row.proposed_by),
                        "status": "countered",
                        "revision": row.revision,
                    },
                ]
                assert data.starts_at is not None and data.place is not None
                row.starts_at, row.place, row.proposed_by = data.starts_at, data.place, user
            else:
                row.status = "accepted" if data.action == "accept" else "declined"
        row.revision += 1
        await self._announce(row, user, f"Viewing {data.action}")
        return ViewingView.model_validate(row)

    async def _announce(self, row: Viewing, user: UUID, label: str) -> None:
        conversation = await MessagingService(self.session).member(row.conversation_id, user)
        await self.session.flush()
        await MessagingService(self.session).send(
            row.conversation_id,
            user,
            f"{label}: {row.starts_at.isoformat()} · {row.place}",
            f"viewing:{row.id}:{row.revision}",
            row.id,
        )
        await emit(
            self.session,
            "viewing.updated",
            {
                "viewing": ViewingView.model_validate(row).model_dump(mode="json"),
                "recipients": [str(conversation.buyer_id), str(conversation.seller_id)],
            },
        )

    async def page(self, conversation: UUID, user: UUID, cursor: str | None) -> ViewingPage:
        """List proposals for an authorized conversation."""
        await MessagingService(self.session).member(conversation, user)
        rows = await self.repo.page(
            conversation, UUID(decode_cursor(cursor)["id"]) if cursor else None
        )
        return ViewingPage(
            items=[ViewingView.model_validate(row) for row in rows[:20]],
            next_cursor=encode_cursor({"id": str(rows[19].id)}) if len(rows) > 20 else None,
        )

    async def calendar(self, viewing_id: UUID, user: UUID) -> str:
        """Export a private accepted viewing without allowing calendar field injection."""
        row = await self.session.get(Viewing, viewing_id)
        require(row, 404, "viewing_missing", "Viewing not found.")
        assert row is not None
        await MessagingService(self.session).member(row.conversation_id, user)
        require(
            row.status == "accepted",
            409,
            "not_accepted",
            "Accept the viewing before adding it to a calendar.",
        )

        def stamp(value: datetime) -> str:
            return value.strftime("%Y%m%dT%H%M%SZ")

        lines = [
            "BEGIN:VCALENDAR",
            "VERSION:2.0",
            "PRODID:-//Motorloop//Viewings//EN",
            "BEGIN:VEVENT",
            f"UID:{row.id}@motorloop.local",
            f"DTSTAMP:{stamp(utcnow())}",
            f"DTSTART:{stamp(row.starts_at)}",
            f"DTEND:{stamp(row.starts_at + timedelta(minutes=30))}",
            "SUMMARY:Motorloop car viewing",
            f"LOCATION:{ics_escape(row.place)}",
            "DESCRIPTION:Meet in a busy public place. Inspect before paying.",
            "END:VEVENT",
            "END:VCALENDAR",
        ]
        # RFC5545 folding, respecting UTF-8 octets, not Python character count.
        folded: list[str] = []
        for line in lines:
            current = ""
            for character in line:
                if len((current + character).encode()) > 73:
                    folded.append(current)
                    current = " "
                current += character
            folded.append(current)
        return "\r\n".join(folded) + "\r\n"

    async def schedule_reminders(self) -> None:
        """Claim due reminders transactionally so scheduler replicas cannot duplicate them."""
        rows = list(
            await self.session.scalars(
                select(Viewing)
                .where(
                    Viewing.status == "accepted",
                    Viewing.reminded_at.is_(None),
                    Viewing.starts_at > utcnow(),
                    Viewing.starts_at <= utcnow() + timedelta(hours=1),
                )
                .with_for_update(skip_locked=True)
            )
        )
        for row in rows:
            conversation = await MessagingService(self.session).member(
                row.conversation_id, row.proposed_by
            )
            for user_id in [conversation.buyer_id, conversation.seller_id]:
                await emit(
                    self.session,
                    "notification.requested",
                    {
                        "user_id": str(user_id),
                        "kind": "viewing_reminder",
                        "viewing_id": str(row.id),
                        "revision": row.revision,
                    },
                )
            row.reminded_at = utcnow()

    async def reminder_valid(self, viewing_id: UUID, revision: int) -> bool:
        """Suppress a queued reminder if the viewing was changed or cancelled."""
        row = await self.session.get(Viewing, viewing_id)
        return bool(
            row
            and row.status == "accepted"
            and row.revision == revision
            and row.starts_at > utcnow()
        )
