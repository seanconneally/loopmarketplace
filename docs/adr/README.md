# Architecture decisions

| Decision | Trade-off |
| --- | --- |
| [0001 — Modular monolith](0001-modular-monolith.md) | Service ownership without distributed operations |
| [0002 — Typed cars and PostGIS](0002-typed-cars.md) | Clear validation and geographic indexes |
| [0003 — Outbox and Celery](0003-outbox-celery.md) | Durable at-least-once work with explicit deduplication |
| [0004 — Direct media](0004-direct-media.md) | Provider flexibility and no API video bandwidth |
| [0005 — Rotating sessions](0005-sessions.md) | Revocation safety with authoritative reads |
| [0006 — Feed and realtime](0006-feed-realtime.md) | Stable cursors and recoverable event delivery |
| [0007 — Development boundary](0007-local-boundary.md) | Runnable local demo with explicit production gates |
