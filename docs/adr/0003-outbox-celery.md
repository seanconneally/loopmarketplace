# ADR 0003 — Transactional outbox and Celery

Accepted. Commit state/work together, dispatch via leases, and deduplicate effects because delivery is at least once. Celery is chosen for mature workload routing and worker controls, with somewhat more configuration than Dramatiq. Redis transports work; PostgreSQL retains progress/failures so broker loss cannot erase a committed job.
