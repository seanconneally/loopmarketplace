import logging
import os

import sentry_sdk
import structlog
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

from app.core.config import settings


def configure_telemetry() -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    structlog.configure(
        processors=[
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.JSONRenderer(),
        ]
    )
    cfg = settings()
    if cfg.sentry_dsn:
        sentry_sdk.init(dsn=cfg.sentry_dsn, send_default_pii=False, traces_sample_rate=0.05)
    if cfg.otel_endpoint:
        provider = TracerProvider(
            resource=Resource.create({"service.name": os.getenv("SERVICE_NAME", "motorloop-api")})
        )
        provider.add_span_processor(
            BatchSpanProcessor(OTLPSpanExporter(endpoint=cfg.otel_endpoint))
        )
        trace.set_tracer_provider(provider)
