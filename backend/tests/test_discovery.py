import os
from datetime import timedelta
from uuid import UUID, uuid4

import pytest
from sqlalchemy import event

from app.core.db import engine, sessions, utcnow
from app.modules.feed.schemas import FeedFilters
from app.modules.feed.service import FeedService
from app.modules.listings.schemas import ListingCreate, ListingUpdate
from app.modules.listings.service import ListingService
from app.modules.media.models import MediaAsset
from tests.test_integration import login
from tests.test_seller_uploads import BODY, client

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(os.getenv("RUN_INTEGRATION") != "1", reason="Requires Compose dependencies"),
]


async def test_discovery_search_ordered_pages_visibility_and_saved_recovery() -> None:
    marker = f"Discovery-{uuid4().hex[:10]}"
    rows = []
    async with client() as owner, client() as buyer:
        await login(owner)
        await login(buyer)
        owner_id = UUID((await owner.get("/api/v1/users/me")).json()["id"])
        buyer_id = UUID((await buyer.get("/api/v1/users/me")).json()["id"])
        try:
            async with sessions() as session:
                published = utcnow() - timedelta(minutes=1)
                for index in range(24):
                    details = {
                        **BODY,
                        "title": f"{marker} car {index}" + (" 100% Ready" if index == 0 else ""),
                        "price_cents": 1000000 + index % 5 * 100000,
                        "car": {
                            **BODY["car"],
                            "make": "Lucid" if index % 2 == 0 else "Polestar",
                            "model": "Air" if index % 2 == 0 else "Two",
                            "fuel": "electric" if index % 3 == 0 else "petrol",
                            "transmission": "manual" if index % 4 == 0 else "automatic",
                            "year": 2020 + index % 4,
                            "mileage_km": 10000 + index * 2000,
                        },
                    }
                    listing = await ListingService(session).create(
                        owner_id, ListingCreate.model_validate(details), str(uuid4())
                    )
                    listing.published_at = published
                    session.add(
                        MediaAsset(
                            listing_id=listing.id,
                            object_key=f"discovery-fixture/{uuid4()}",
                            upload_id="fixture",
                            size_bytes=1,
                            content_type="video/mp4",
                            idempotency_key=str(uuid4()),
                            request_hash="0" * 64,
                            status="ready",
                            playback_url="http://localhost:8080/media/test/master.m3u8",
                        )
                    )
                    await session.flush()
                    await ListingService(session).media_state(listing.id, "live")
                    rows.append(
                        {
                            "id": listing.id,
                            "price": details["price_cents"],
                            "index": index,
                            "details": details,
                        }
                    )
                await session.commit()

            # Guard the hot path against row-by-row identity/block/save lookups.
            queries = []

            def count_queries(connection, cursor, statement, *args):
                if statement.lstrip().upper().startswith("SELECT"):
                    queries.append(statement)

            event.listen(engine.sync_engine, "before_cursor_execute", count_queries)
            try:
                async with sessions() as session:
                    page = await FeedService(session).page(FeedFilters(q=marker), buyer_id, None)
                    assert len(page.items) == 10
                    assert len(queries) <= 8
            finally:
                event.remove(engine.sync_engine, "before_cursor_execute", count_queries)

            async def pages(params):
                results, cursor = [], None
                for _ in range(10):
                    response = await buyer.get(
                        "/api/v1/feed", params={**params, **({"cursor": cursor} if cursor else {})}
                    )
                    assert response.status_code == 200, response.text
                    results.extend(response.json()["items"])
                    cursor = response.json()["next_cursor"]
                    if not cursor:
                        break
                assert cursor is None
                assert len({item["id"] for item in results}) == len(results)
                return results

            options = await buyer.get("/api/v1/feed/options")
            assert options.status_code == 200, options.text
            assert {"Lucid", "Polestar"} <= set(options.json()["makes"])
            # Every sort crosses multiple pages, including identical price and timestamp ties.
            for sort in ["newest", "price_asc", "price_desc"]:
                found = await pages({"q": marker, "sort": sort})
                expected = sorted(
                    rows,
                    key=lambda row: (
                        (-row["id"].int,)
                        if sort == "newest"
                        else (
                            (row["price"] if sort == "price_asc" else -row["price"]),
                            -row["id"].int,
                        )
                    ),
                )
                assert [item["id"] for item in found] == [str(row["id"]) for row in expected]
            filtered = await pages(
                {
                    "q": f"{marker.lower()} air",
                    "fuel": "electric",
                    "transmission": "automatic",
                    "max_mileage": 40000,
                    "sort": "newest",
                }
            )
            expected_ids = {
                str(row["id"])
                for row in rows
                if row["index"] % 2 == 0
                and row["index"] % 3 == 0
                and row["index"] % 4 != 0
                and row["index"] <= 15
            }
            assert {item["id"] for item in filtered} == expected_ids
            literal = await pages({"q": f"{marker} %", "sort": "newest"})
            assert [item["id"] for item in literal] == [str(rows[0]["id"])]
            for invalid in [
                {"min_price": 200, "max_price": 100},
                {"min_year": 2025, "max_year": 2020},
                {"fuel": "water"},
                {"q": "x" * 101},
            ]:
                assert (await buyer.get("/api/v1/feed", params=invalid)).status_code == 422

            first = (
                await buyer.get("/api/v1/feed", params={"q": marker, "sort": "price_asc"})
            ).json()
            cursor = first["next_cursor"]
            assert cursor
            assert (
                await owner.get(
                    "/api/v1/feed", params={"q": marker, "sort": "price_asc", "cursor": cursor}
                )
            ).status_code == 400
            assert (
                await buyer.get(
                    "/api/v1/feed", params={"q": marker, "sort": "price_desc", "cursor": cursor}
                )
            ).status_code == 400

            # Existing ranked snapshots must recheck edited prices, not return out-of-budget cars.
            recommended_params = {"q": marker, "max_price": 1500000}
            first = (await buyer.get("/api/v1/feed", params=recommended_params)).json()
            assert first["next_cursor"]
            shown = {item["id"] for item in first["items"]}
            changed = next(row for row in rows if str(row["id"]) not in shown)
            async with sessions() as session:
                service = ListingService(session)
                owned = await service.owned(changed["id"], owner_id)
                await service.update(
                    changed["id"],
                    owner_id,
                    ListingUpdate.model_validate(
                        {**changed["details"], "price_cents": 9000000, "revision": owned.revision}
                    ),
                )
                await session.commit()
            following = await buyer.get(
                "/api/v1/feed", params={**recommended_params, "cursor": first["next_cursor"]}
            )
            assert following.status_code == 200, following.text
            assert all(item["price_cents"] <= 1500000 for item in following.json()["items"])
            assert all(item["id"] != str(changed["id"]) for item in following.json()["items"])

            # The shortlist fills a 20-item page even when the first two saves become hidden.
            hidden = sorted(rows, key=lambda row: row["id"].int, reverse=True)[:2]
            async with sessions() as session:
                service = ListingService(session)
                for row in rows:
                    await service.save(row["id"], buyer_id, True)
                for row in hidden:
                    await service.media_state(row["id"], "removed")
                await session.commit()
            saved = await buyer.get("/api/v1/listings/saved")
            assert saved.status_code == 200, saved.text
            assert len(saved.json()["items"]) == 20
            saved_cursor = saved.json()["next_cursor"]
            assert saved_cursor
            remaining = await buyer.get("/api/v1/listings/saved", params={"cursor": saved_cursor})
            assert remaining.status_code == 200 and len(remaining.json()["items"]) == 2, (
                remaining.text
            )
            assert remaining.json()["next_cursor"] is None
            assert (
                await owner.get("/api/v1/listings/saved", params={"cursor": saved_cursor})
            ).status_code == 400
            assert (
                await buyer.delete(f"/api/v1/listings/{hidden[0]['id']}/save")
            ).status_code == 204
        finally:
            async with sessions() as session:
                for row in rows:
                    await ListingService(session).media_state(row["id"], "removed")
                await session.commit()
