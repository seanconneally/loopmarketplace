import hashlib
import re
from uuid import UUID

from sqlalchemy import delete, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import require
from app.core.outbox import emit
from app.core.paging import decode_cursor, encode_cursor
from app.modules.moderation.models import Block, ModerationAction, Report
from app.modules.moderation.repository import ModerationRepository
from app.modules.moderation.schemas import ActionInput, ReportInput, ReportPage, ReportView
from app.modules.users.service import UserService

SCAM_PATTERNS = [
    (
        r"\b(deposit|down payment|reservation fee)\b",
        "Avoid advance deposits; inspect the car first.",
    ),
    (
        r"https?://|\b(paypal|revolut|western union|crypto)\b",
        "Be careful with payment links and off-platform payments.",
    ),
    (
        r"\b(courier|shipping agent|delivery agent)\b",
        "Courier stories can be a scam. Arrange a public viewing.",
    ),
]


def scam_warnings(body: str) -> list[str]:
    return [warning for pattern, warning in SCAM_PATTERNS if re.search(pattern, body, re.I)]


class ModerationService:
    def __init__(self, session: AsyncSession) -> None:
        self.session, self.repo = session, ModerationRepository(session)

    async def blocked(self, first: UUID, second: UUID) -> bool:
        """Return symmetric block policy for feeds, messaging and viewings."""
        return await self.repo.blocked(first, second)

    async def blocked_peers(self, user: UUID, peers: set[UUID]) -> set[UUID]:
        """Apply symmetric block policy to a bounded conversation page in one query."""
        return await self.repo.blocked_peers(user, peers)

    async def set_block(self, user: UUID, target: UUID, enabled: bool) -> None:
        """Set a user's directional block, with symmetric access enforcement."""
        require(user != target, 422, "invalid_block", "You cannot block yourself.")
        await UserService(self.session).active(target)
        if enabled:
            await self.session.execute(
                insert(Block).values(blocker_id=user, blocked_id=target).on_conflict_do_nothing()
            )
        else:
            await self.session.execute(
                delete(Block).where(Block.blocker_id == user, Block.blocked_id == target)
            )
        await emit(
            self.session,
            "block.changed",
            {"target_id": str(target), "recipients": [str(user), str(target)]},
        )

    async def report(self, user: UUID, data: ReportInput, key: str) -> ReportView:
        """Persist an authenticated report with a scoped idempotency key."""
        from app.modules.listings.service import ListingService
        from app.modules.messaging.service import MessagingService

        if data.target_type == "listing":
            await ListingService(self.session).detail(data.target_id, user)
        elif data.target_type == "user":
            await UserService(self.session).active(data.target_id)
        else:
            await MessagingService(self.session).message_for_report(data.target_id, user)
        scoped = f"{user}:{key}"
        statement = (
            insert(Report)
            .values(reporter_id=user, idempotency_key=scoped, **data.model_dump())
            .on_conflict_do_nothing()
        )
        await self.session.execute(statement)
        result = await self.session.scalar(select(Report).where(Report.idempotency_key == scoped))
        assert result is not None
        require(
            result.target_type == data.target_type
            and result.target_id == data.target_id
            and result.reason == data.reason,
            409,
            "idempotency_conflict",
            "This key belongs to a different report.",
        )
        return ReportView.model_validate(result)

    async def admin(self, user: UUID) -> None:
        """Require an active administrator using authoritative account state."""
        require(
            (await UserService(self.session).active(user)).role == "admin",
            403,
            "admin_required",
            "Administrator access required.",
        )

    async def queue(self, user: UUID, cursor: str | None) -> ReportPage:
        """List open reports with a stable UUID keyset."""
        await self.admin(user)
        after = UUID(decode_cursor(cursor)["id"]) if cursor else None
        rows = await self.repo.reports(after)
        return ReportPage(
            items=[ReportView.model_validate(row) for row in rows[:20]],
            next_cursor=encode_cursor({"id": str(rows[19].id)}) if len(rows) > 20 else None,
        )

    async def scan_listing(self, listing_id: UUID, duplicate: bool) -> bool:
        """Apply local text/hash signals; production frame scanning is a release gate."""
        from app.modules.listings.service import ListingService

        text, revision = await ListingService(self.session).moderation_context(listing_id)
        reasons = []
        if duplicate:
            reasons.append("Matching perceptual video hash; human review required")
        if re.search(r"https?://|\+\d[\d\s]{7,}|\b\S+@\S+\.\S+", text):
            reasons.append("Contact details or external link in listing text")
        if reasons:
            await self.session.execute(
                insert(Report)
                .values(
                    target_type="listing",
                    target_id=listing_id,
                    reason="; ".join(reasons),
                    idempotency_key=f"scan:{listing_id}:{revision}:{hashlib.sha256(text.encode()).hexdigest()[:16]}",
                )
                .on_conflict_do_nothing()
            )
        return bool(reasons)

    async def act(self, user: UUID, data: ActionInput, key: str) -> None:
        """Audit a reasoned moderation action and apply it through the owning module."""
        from app.modules.listings.service import ListingService
        from app.modules.media.service import MediaService

        await self.admin(user)
        scoped = f"{user}:{key}"
        existing = await self.session.scalar(
            select(ModerationAction).where(ModerationAction.idempotency_key == scoped)
        )
        if existing:
            require(
                existing.target_id == data.target_id
                and existing.target_type == data.target_type
                and existing.action == data.action
                and existing.reason == data.reason,
                409,
                "idempotency_conflict",
                "This key belongs to another action.",
            )
            return
        if data.target_type == "listing":
            require(
                data.action in {"approve", "remove"},
                422,
                "invalid_action",
                "Use approve or remove for listings.",
            )
            if data.action == "approve":
                await MediaService(self.session).approve(data.target_id)
            else:
                await ListingService(self.session).media_state(data.target_id, "removed")
        else:
            require(
                data.action == "suspend" and data.target_id != user,
                422,
                "invalid_action",
                "Use suspend for another user.",
            )
            await UserService(self.session).suspend(data.target_id)
        self.session.add(
            ModerationAction(moderator_id=user, idempotency_key=scoped, **data.model_dump())
        )
        await self.session.execute(
            update(Report)
            .where(
                Report.target_type == data.target_type,
                Report.target_id == data.target_id,
                Report.status == "open",
            )
            .values(status="resolved")
        )
        await emit(
            self.session,
            "moderation.action",
            {**data.model_dump(mode="json"), "moderator_id": str(user)},
        )
