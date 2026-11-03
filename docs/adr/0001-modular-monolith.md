# ADR 0001 — Modular monolith

Accepted. One FastAPI codebase/database minimizes operations; modules own their data and communicate through services/events. Cross-domain foreign keys protect integrity without permitting cross-domain queries. Media processing is the first extraction candidate when encoding isolation or independent deployments demand it.
