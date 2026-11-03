import os
from uuid import uuid4

import httpx
import pytest

from app.main import app

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        os.getenv("RUN_INTEGRATION") != "1",
        reason="Set RUN_INTEGRATION=1 with Compose dependencies running",
    ),
]


async def login(client: httpx.AsyncClient) -> str:
    phone = "+35387" + str(uuid4().int % 10000000).zfill(7)
    response = await client.post("/api/v1/auth/otp/request", json={"phone": phone})
    assert response.status_code == 200, response.text
    response = await client.post("/api/v1/auth/otp/verify", json={"phone": phone, "code": "123456"})
    assert response.status_code == 200, response.text
    token = str(response.json()["access_token"])
    client.headers["Authorization"] = f"Bearer {token}"
    response = await client.patch(
        "/api/v1/users/me",
        json={"name": "Integration buyer", "adult_declared": True, "analytics_consent": False},
    )
    assert response.status_code == 200
    return token


async def test_draft_idempotency_ownership_and_session_reuse() -> None:
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(
            app=app, client=(f"198.19.{uuid4().int % 256}.{uuid4().int % 256}", 12345)
        ),
        base_url="http://localhost:8080",
        headers={"Origin": "http://localhost:8080"},
    ) as client:
        await login(client)
        body = {
            "title": "Integration test car",
            "price_cents": 1200000,
            "area": "Dublin",
            "latitude": 53.3498,
            "longitude": -6.2603,
            "rights_confirmed": True,
            "car": {
                "make": "Toyota",
                "model": "Yaris",
                "year": 2020,
                "mileage_km": 40000,
                "fuel": "hybrid",
                "transmission": "automatic",
            },
        }
        headers = {"Idempotency-Key": str(uuid4())}
        first = await client.post("/api/v1/listings", json=body, headers=headers)
        assert first.status_code == 201, first.text
        replay = await client.post("/api/v1/listings", json=body, headers=headers)
        assert replay.json()["id"] == first.json()["id"]
        conflict = await client.post(
            "/api/v1/listings", json={**body, "price_cents": 1}, headers=headers
        )
        assert conflict.status_code == 409
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(
                app=app, client=(f"198.19.{uuid4().int % 256}.{uuid4().int % 256}", 12345)
            ),
            base_url="http://localhost:8080",
        ) as other:
            response = await other.get(f"/api/v1/listings/{first.json()['id']}")
            assert response.status_code == 404
        original_refresh = client.cookies["refresh"]
        rotated = await client.post("/api/v1/auth/refresh")
        assert rotated.status_code == 200
        reused = await client.post(
            "/api/v1/auth/refresh", headers={"Cookie": f"refresh={original_refresh}"}
        )
        assert reused.status_code == 401
        client.headers["Authorization"] = f"Bearer {rotated.json()['access_token']}"
        assert (await client.get("/api/v1/users/me")).status_code == 401


async def test_feed_chat_viewing_and_symmetric_block() -> None:
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(
            app=app, client=(f"198.19.{uuid4().int % 256}.{uuid4().int % 256}", 12345)
        ),
        base_url="http://localhost:8080",
        headers={"Origin": "http://localhost:8080"},
    ) as buyer:
        await login(buyer)
        feed = await buyer.get("/api/v1/feed")
        assert feed.status_code == 200, feed.text
        listing = feed.json()["items"][0]
        key = {"Idempotency-Key": str(uuid4())}
        conversation = await buyer.post(
            "/api/v1/conversations", json={"listing_id": listing["id"]}, headers=key
        )
        assert conversation.status_code == 201, conversation.text
        conversation_id = conversation.json()["id"]
        message_key = {"Idempotency-Key": str(uuid4())}
        path = f"/api/v1/conversations/{conversation_id}/messages"
        sent = await buyer.post(
            path, json={"body": "Send deposit to https://payment.example"}, headers=message_key
        )
        assert sent.status_code == 201, sent.text
        assert sent.json()["warnings"]
        assert (
            await buyer.post(
                path, json={"body": "Send deposit to https://payment.example"}, headers=message_key
            )
        ).json()["id"] == sent.json()["id"]
        proposal = await buyer.post(
            "/api/v1/viewings",
            json={
                "conversation_id": conversation_id,
                "starts_at": "2027-01-15T12:00:00Z",
                "place": "Dundrum shopping centre main entrance",
            },
            headers={"Idempotency-Key": str(uuid4())},
        )
        assert proposal.status_code == 201, proposal.text
        rejected = await buyer.post(
            f"/api/v1/viewings/{proposal.json()['id']}/respond",
            json={"action": "accept", "revision": 1},
        )
        assert rejected.status_code == 409
        denied = await buyer.post(
            "/api/v1/analytics/events",
            json={
                "events": [
                    {
                        "client_event_id": str(uuid4()),
                        "listing_id": listing["id"],
                        "event_type": "watch",
                        "value": 1,
                    }
                ]
            },
        )
        assert denied.status_code == 403
        assert (
            await buyer.put("/api/v1/moderation/blocks", json={"user_id": listing["seller"]["id"]})
        ).status_code == 204
        assert (await buyer.get(path)).status_code == 403
        filtered = await buyer.get("/api/v1/feed")
        assert all(
            item["seller"]["id"] != listing["seller"]["id"] for item in filtered.json()["items"]
        )
