# Validation record

Validated locally on 2 November 2026. These checks establish the scaffold's local behaviour, not production SLOs or legal compliance.

| Check | Result |
| --- | --- |
| Docker Compose build/start with `--wait` | Passed; Nginx, API, Celery worker, relay, PostgreSQL/PostGIS, PgBouncer, Redis and SeaweedFS healthy; initialization exited successfully |
| Python runtime | Application images run Linux/Python 3.12 |
| Backend full suite in Python 3.12 container | **14 passed**: eight domain/provider unit tests plus six integration cases covering real Postgres/Redis/S3 and audible/silent ffmpeg output |
| Backend strict typing | `mypy app`: no issues in 79 source files |
| Backend lint/format | Ruff check and format check passed |
| Schema creation/upgrades | Alembic `0001` → `0002` → `0003` → `0004` applied successfully; existing volumes preserved |
| Schema drift | `alembic check`: no new upgrade operations detected, including the PgBouncer-connected container check |
| Frontend strict TypeScript | Typecheck and Vite production build passed |
| Frontend lint/format | ESLint and Prettier checks passed |
| Frontend component/upload tests | **4 passed**: phone OTP/profile declaration, full-file fingerprints, cancellation, missing-part-only resume, generation completion and wrong-file rejection |
| Playwright Chromium | **3 end-to-end scenarios passed**: original upload/chat/viewing journey; lost draft response/interrupted upload/reload/resume/edit/pause/resume/sold; failed processing and retained-source retry |
| Responsive regression | Verified 390×844 feed price remains above navigation, seller dashboard has no horizontal overflow, and desktop/mobile dashboard layouts were visually reviewed |
| Audio preservation | Actual ffprobe inspection of both 360×640 and 720×1280 HLS segments: AAC retained for audible input, no audio for silent input; browser unmute verified |
| Playback observation | Visible clip playing at readyState 4 with advancing playback time; next two clips buffered and paused |
| Optional operations configuration | Main and optional observability Compose configuration validated; optional Prometheus/Grafana containers were not started |

Earlier scaffold tests also ran natively on Windows/Python 3.14 during development. Windows tests use a selector event loop compatible with Psycopg, and shared Redis connections are closed between test loops. The final expanded suite used the rebuilt Linux/Python 3.12 application image with actual database, Redis, object storage and ffmpeg. Its public storage endpoint was set to `http://storage:9000` inside that test container so direct signed-URL requests resolve correctly there. ASGI integration clients use distinct test-only IPs so repeated test accounts do not share an OTP quota; application rate limits remain in place.

## What was exercised

Tests cover signed-cursor tampering, production-adapter guards, bounded ranking/seen penalties, scam-pattern warnings, timezone requirements and calendar escaping, listing validation and recovery from a lost successful S3 completion response. Integration cases cover draft idempotency/conflicts, private-draft visibility, refresh reuse revocation, real feed queries, unique messaging, warning payloads, viewing response authorization, analytics opt-in enforcement and symmetric blocking.

The browser scenario uses separate cookie jars/accounts, a newly generated original clip and actual direct storage PUTs; it does not intercept the API or replace the processing pipeline. The test accepts the viewing from the seller account and verifies the buyer sees the update. It then closes its synthetic listing through the seller UI. Only licensed-by-construction sample cars remain in the local feed.

The seller journey deliberately intercepts one draft creation response after the server commits, then aborts storage PUTs after the first successful part. It reloads the page, reuses the exact draft key, finds one advert, rejects an identically named/sized file with different bytes, and resumes without sending the first part again. It verifies a price/description edit in the feed, audio/unmute, pause removal, resume and sold. The failed-video journey confirms a real decoding error becomes actionable in My cars and the original can be retried without another upload. Backend cases also cover strict ownership, stale revisions, review withdrawal, repeated flagged-text review, paused preference after approval, closed-advert edits and stale upload generations.

## Evidence

- [Desktop feed](screenshots/desktop.png)
- [Mobile feed](screenshots/mobile.png)
- [Accepted viewing](screenshots/viewing-accepted.png)
- [Seller dashboard](screenshots/seller-dashboard.png)
- [Mobile seller dashboard](screenshots/seller-mobile.png)

The HLS library is split into its own bundle, but Vite still reports a >500 kB uncompressed video-library chunk (about 187 kB gzip). That is a performance-budget item for the real-device/4G release work, not a build failure.

## Limits

No 100k-MAU load test, representative p95 latency test, 4G first-frame measurement, chaos/failover exercise, production restore drill, external provider verification, real-device push test, legal review or public cloud deployment was performed. The optional dashboards are supplied/configuration-checked; paging, managed EU telemetry and PITR need operational setup. Production startup remains intentionally blocked until [the release gates](09-scaffold.md) are implemented and reviewed.

CI is included but has not run on GitHub because no remote repository was created. Local checks exercised its principal lint/type/build/migration/test steps. The updated development stack is left running at [localhost:8080](http://localhost:8080), with existing data volumes preserved. Use `docker compose up -d --build` for a later restart/update.
