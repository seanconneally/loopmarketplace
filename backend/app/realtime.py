import asyncio
import json
from contextlib import suppress
from uuid import UUID

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.core.config import settings
from app.core.db import sessions
from app.core.errors import DomainError
from app.core.metrics import WEBSOCKETS
from app.core.redis import client
from app.modules.auth.repository import AuthRepository
from app.modules.auth.service import digest
from app.modules.messaging.service import MessagingService
from app.modules.users.service import UserService

router = APIRouter()


class RealtimeService:
    async def serve(self, socket: WebSocket) -> None:
        """Authenticate a first-frame ticket and stream authorized, recoverable events."""
        if socket.headers.get("origin") != settings().public_origin:
            await socket.close(code=1008)
            return
        await socket.accept()
        WEBSOCKETS.inc()
        try:
            first = await asyncio.wait_for(socket.receive_json(), timeout=10)
            if not isinstance(first, dict) or not isinstance(first.get("ticket"), str):
                await socket.close(code=1008)
                return
            raw = await client.getdel(f"ws-ticket:{digest(first['ticket'])}")
            if raw is None:
                await socket.close(code=1008)
                return
            user_raw, family_raw = json.loads(raw)
            user, family = UUID(user_raw), UUID(family_raw)
            async with client.pubsub() as pubsub:
                await pubsub.subscribe(f"user:{user}")
                while True:
                    # Every loop rechecks authority, bounding suspension/logout exposure.
                    async with sessions() as session:
                        await UserService(session).active(user)
                        if not await AuthRepository(session).valid_family(user, family):
                            await socket.close(code=1008)
                            return
                    message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=1)
                    if message:
                        event = json.loads(message["data"])
                        conversation = event["data"].get("conversation_id") or event["data"].get(
                            "viewing", {}
                        ).get("conversation_id")
                        if conversation:
                            async with sessions() as session:
                                try:
                                    await MessagingService(session).member(UUID(conversation), user)
                                except DomainError:
                                    continue
                        await socket.send_json(event)
                    else:
                        await socket.send_json({"type": "heartbeat", "data": {}})
                    # The client sends no application payloads after authentication.
                    # ASGI disconnect delivery is observed by send failures and timeout.
        except (TimeoutError, WebSocketDisconnect, DomainError, ValueError, RuntimeError):
            with suppress(RuntimeError):
                await socket.close(code=1008)
        finally:
            WEBSOCKETS.dec()


@router.websocket("/ws")
async def websocket(socket: WebSocket) -> None:
    await RealtimeService().serve(socket)
