import asyncio
import json
import os
from contextlib import asynccontextmanager
from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from sqlalchemy import delete, select
from sqlalchemy import event as sql_event

from app import realtime
from app.core.db import engine, sessions, utcnow
from app.core.outbox import Outbox
from app.core.redis import client
from app.modules.listings.models import Listing
from app.modules.messaging.models import Conversation
from app.modules.messaging.service import MessagingService
from app.modules.moderation.models import Block
from app.modules.notifications.models import Notification
from app.modules.notifications.service import NotificationService
from app.modules.users.models import User
from app.modules.viewings.models import Viewing
from app.modules.viewings.service import ViewingService
from app.worker import process_event


async def test_idle_websocket_bounds_authorization_queries_and_heartbeats(monkeypatch):
    clock = [0]
    active, family = AsyncMock(), AsyncMock(return_value=True)

    @asynccontextmanager
    async def session():
        yield object()

    class Subscription:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return None

        async def subscribe(self, channel):
            pass

        async def get_message(self, **kwargs):
            clock[0] += 1
            if clock[0] > 31:
                raise RuntimeError("socket disconnected")
            return None

    user, family_id = uuid4(), uuid4()
    monkeypatch.setattr(realtime, "monotonic", lambda: clock[0])
    monkeypatch.setattr(realtime, "sessions", session)
    monkeypatch.setattr(realtime, "UserService", lambda _: SimpleNamespace(active=active))
    monkeypatch.setattr(realtime, "AuthRepository", lambda _: SimpleNamespace(valid_family=family))
    monkeypatch.setattr(
        realtime,
        "client",
        SimpleNamespace(
            getdel=AsyncMock(return_value=json.dumps([str(user), str(family_id)])),
            pubsub=Subscription,
        ),
    )
    socket = SimpleNamespace(
        headers={"origin": realtime.settings().public_origin},
        accept=AsyncMock(),
        receive_json=AsyncMock(return_value={"ticket": "one-use-ticket"}),
        send_json=AsyncMock(),
        close=AsyncMock(),
    )
    await realtime.RealtimeService().serve(socket)
    assert active.await_count == 3  # At 0, 15 and 30 seconds, rather than every second.
    assert family.await_count == 3
    assert socket.send_json.await_count == 3
    socket.close.assert_awaited_once_with(code=1008)


integration = pytest.mark.skipif(os.getenv("RUN_INTEGRATION") != "1", reason="Requires Compose")


@pytest.mark.integration
@integration
async def test_reminder_batches_survive_blocks_and_recheck_before_delivery():
    async with sessions() as session:
        # Keep fixtures and emitted work uncommitted, invisible to the running relay.
        seller = User(phone=f"+3538{uuid4().int % 10**8:08}", verified_at=utcnow())
        buyers = [
            User(phone=f"+3538{uuid4().int % 10**8:08}", verified_at=utcnow()) for _ in range(3)
        ]
        session.add_all([seller, *buyers])
        await session.flush()
        listing = Listing(
            seller_id=seller.id,
            title="Reminder isolation fixture",
            price_cents=100,
            latitude=53.3,
            longitude=-6.2,
            area="Dublin",
            idempotency_key=str(uuid4()),
            request_hash="0" * 64,
        )
        session.add(listing)
        await session.flush()
        viewings = []
        for index, buyer in enumerate(buyers):
            conversation = Conversation(
                listing_id=listing.id, buyer_id=buyer.id, seller_id=seller.id
            )
            session.add(conversation)
            await session.flush()
            viewing = Viewing(
                conversation_id=conversation.id,
                proposed_by=buyer.id,
                starts_at=utcnow() + timedelta(minutes=index + 1),
                place="Public meeting place",
                status="accepted",
                idempotency_key=str(uuid4()),
            )
            session.add(viewing)
            viewings.append(viewing)
        session.add(Block(blocker_id=buyers[0].id, blocked_id=seller.id))
        await session.flush()
        service = ViewingService(session)
        await service.schedule_reminders(batch_size=2)
        assert viewings[0].reminded_at and viewings[1].reminded_at
        assert viewings[2].reminded_at is None
        assert not await service.reminder_valid(viewings[0].id, 1)
        await service.schedule_reminders(batch_size=2)
        assert viewings[2].reminded_at
        events = list(
            await session.scalars(
                select(Outbox).where(
                    Outbox.event_type == "notification.requested",
                    Outbox.payload["viewing_id"].astext.in_([str(row.id) for row in viewings]),
                )
            )
        )
        assert len(events) == 4  # Both participants, only for the two eligible viewings.
        await service.schedule_reminders(batch_size=2)
        assert (
            len(
                list(
                    await session.scalars(
                        select(Outbox).where(
                            Outbox.payload["viewing_id"].astext.in_(
                                [str(row.id) for row in viewings]
                            ),
                        )
                    )
                )
            )
            == 4
        )
        # A block added after scheduling must also suppress an already queued delivery.
        session.add(Block(blocker_id=buyers[1].id, blocked_id=seller.id))
        await session.flush()
        blocked_event = next(
            event for event in events if event.payload["viewing_id"] == str(viewings[1].id)
        )
        await NotificationService(session).deliver(blocked_event.id, blocked_event.payload)
        assert not await session.scalar(
            select(Notification.id).where(Notification.event_id == blocked_event.id)
        )
        await session.rollback()


@pytest.mark.integration
@integration
async def test_duplicate_worker_delivery_skips_locked_job_and_applies_effect_once():
    region = f"reliability-{uuid4()}"
    counter = f"feed:revision:{region}"
    async with sessions() as session:
        event = Outbox(
            event_type="feed.invalidate",
            payload={"region_id": region},
            available_at=utcnow() + timedelta(days=1),
        )
        session.add(event)
        await session.commit()
        event_id = event.id
    try:
        async with sessions() as lock:
            await lock.scalar(select(Outbox).where(Outbox.id == event_id).with_for_update())
            await asyncio.wait_for(process_event(event_id), timeout=2)
            assert await client.get(counter) is None
            await lock.rollback()
        await process_event(event_id)
        await process_event(event_id)
        assert await client.get(counter) == "1"
        async with sessions() as session:
            row = await session.get(Outbox, event_id)
            assert row and row.completed_at
    finally:
        async with sessions() as session:
            await session.execute(delete(Outbox).where(Outbox.id == event_id))
            await session.commit()
        await client.delete(counter)


@pytest.mark.integration
@integration
async def test_conversation_pages_use_bounded_queries_and_hide_unavailable_peers():
    async with sessions() as session:
        buyer = User(phone=f"+3538{uuid4().int % 10**8:08}", verified_at=utcnow())
        peers = [
            User(
                phone=f"+3538{uuid4().int % 10**8:08}", name=f"Seller {index}", verified_at=utcnow()
            )
            for index in range(25)
        ]
        session.add_all([buyer, *peers])
        await session.flush()
        for index, peer in enumerate(peers):
            listing = Listing(
                seller_id=peer.id,
                title=f"Conversation car {index}",
                price_cents=100,
                latitude=53.3,
                longitude=-6.2,
                area="Dublin",
                idempotency_key=str(uuid4()),
                request_hash="0" * 64,
            )
            session.add(listing)
            await session.flush()
            session.add(Conversation(listing_id=listing.id, seller_id=peer.id, buyer_id=buyer.id))
        peers[0].status = "suspended"
        session.add_all(
            [
                Block(blocker_id=buyer.id, blocked_id=peers[1].id),
                Block(blocker_id=peers[2].id, blocked_id=buyer.id),
            ]
        )
        await session.flush()
        queries = []

        def count_queries(connection, cursor, statement, *args):
            if statement.lstrip().upper().startswith("SELECT"):
                queries.append(statement)

        sql_event.listen(engine.sync_engine, "before_cursor_execute", count_queries)
        try:
            cursor, seen = None, []
            while True:
                queries.clear()
                page = await MessagingService(session).page(buyer.id, cursor)
                assert len(queries) <= 5  # Constant work per page, independent of row count.
                seen.extend(page.items)
                cursor = page.next_cursor
                if cursor is None:
                    break
        finally:
            sql_event.remove(engine.sync_engine, "before_cursor_execute", count_queries)
        assert len(seen) == 22
        assert len({row.id for row in seen}) == 22
        assert {row.other_name for row in seen} == {peer.name for peer in peers[3:]}
        assert all(row.listing_title.startswith("Conversation car ") for row in seen)
        await session.rollback()
