import time
from contextlib import asynccontextmanager
from typing import Any
from uuid import uuid4

import structlog
from fastapi import FastAPI, Request, Response
from opentelemetry import trace
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest
from redis.exceptions import RedisError
from sqlalchemy import text

from app.core.db import engine, sessions
from app.core.errors import ErrorEnvelope, install_error_handlers
from app.core.metrics import collect_work_metrics
from app.core.redis import client, rate_limit
from app.core.telemetry import configure_telemetry
from app.modules.analytics.router import router as analytics
from app.modules.auth.router import router as auth
from app.modules.feed.router import router as feed
from app.modules.listings.dealer import router as dealer
from app.modules.listings.router import router as listings
from app.modules.media.router import router as media
from app.modules.messaging.router import router as messaging
from app.modules.moderation.router import router as moderation
from app.modules.users.router import router as users
from app.modules.viewings.router import router as viewings
from app.realtime import router as realtime

configure_telemetry()
log = structlog.get_logger()
REQUESTS = Counter("motorloop_http_requests_total", "HTTP requests", ["method", "route", "status"])
LATENCY = Histogram("motorloop_http_seconds", "HTTP latency", ["route"])


@asynccontextmanager
async def lifespan(app: FastAPI):  # type: ignore[no-untyped-def]
    yield
    await client.aclose()
    await engine.dispose()


error_responses: dict[int | str, dict[str, Any]] = {
    code: {"model": ErrorEnvelope, "description": "Consistent application error envelope"}
    for code in [400, 401, 403, 404, 409, 410, 413, 422, 429, 500]
}
app = FastAPI(
    title="Motorloop API",
    version="0.1.0",
    lifespan=lifespan,
    responses=error_responses,
    description="Local development scaffold. Production deployment is intentionally guarded.",
)
install_error_handlers(app)


@app.middleware("http")
async def observe(request: Request, call_next: Any) -> Response:
    request.state.request_id = str(uuid4())
    start = time.perf_counter()
    if request.url.path.startswith("/api/v1") and request.method not in {"GET", "HEAD", "OPTIONS"}:
        try:
            allowed = await rate_limit(
                f"mutations:{request.client.host if request.client else 'unknown'}", 120
            )
        except RedisError:
            allowed = False
        if not allowed:
            from fastapi.responses import JSONResponse

            return JSONResponse(
                status_code=429,
                content={
                    "error": {
                        "code": "rate_limited",
                        "message": "Please try again shortly.",
                        "request_id": request.state.request_id,
                    }
                },
            )
    with trace.get_tracer("motorloop.http").start_as_current_span(f"{request.method} request"):
        response: Response = await call_next(request)
    route = getattr(request.scope.get("route"), "path", "unmatched")
    elapsed = time.perf_counter() - start
    REQUESTS.labels(request.method, route, str(response.status_code)).inc()
    LATENCY.labels(route).observe(elapsed)
    response.headers["X-Request-ID"] = request.state.request_id
    response.headers["X-Content-Type-Options"] = "nosniff"
    if request.url.path.startswith("/api"):
        response.headers["Cache-Control"] = "no-store"
    log.info(
        "request_complete",
        request_id=request.state.request_id,
        method=request.method,
        route=route,
        status=response.status_code,
        elapsed_ms=round(elapsed * 1000, 1),
    )
    return response


for module in [
    auth,
    users,
    listings,
    media,
    feed,
    messaging,
    viewings,
    moderation,
    analytics,
    dealer,
]:
    app.include_router(module, prefix="/api/v1")
app.include_router(realtime)


@app.get("/health/live", include_in_schema=False)
async def live() -> dict[str, str]:
    return {"status": "alive"}


@app.get("/health/ready", include_in_schema=False)
async def ready() -> Response:
    try:
        async with sessions() as session:
            await session.execute(text("SELECT 1"))
    except Exception:
        return Response('{"status":"unavailable"}', status_code=503, media_type="application/json")
    # Redis failure degrades feeds but blocks mutations; keep read replicas routable.
    try:
        await client.ping()
        status = "ready"
    except RedisError:
        status = "degraded"
    return Response(f'{{"status":"{status}"}}', media_type="application/json")


@app.get("/metrics", include_in_schema=False)
async def metrics() -> Response:
    await collect_work_metrics()
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
