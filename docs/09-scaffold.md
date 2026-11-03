# 9. Repository and scaffold

## Feature location

```text
backend/app/core/           settings, sessions, errors, cursors, outbox, telemetry
backend/app/modules/
  auth/                    OTP, access/refresh sessions
  users/                   identity, declarations and verified dealers
  listings/                drafts, typed cars, saves, sale closure; dealer.py imports
  media/                   direct S3 multipart, VideoProvider, ffmpeg/HLS
  feed/                    PostGIS projection, candidate cache, FeedRanker
  messaging/               conversations, persisted messages/read receipts
  viewings/                revisioned proposals, reminders, calendar
  moderation/              reports, blocks, decisions and scam signals
  notifications/           durable local records; external adapter boundary
  analytics/               consent-checked append-only events
backend/app/main.py        assembly, health, metrics and middleware
backend/app/realtime.py    first-frame ticket and authorized fan-out
backend/app/worker.py      Celery handlers and durable terminal failures
backend/app/relay.py       leases, reconciliation, retries and reminders
backend/app/seed.py        original car artwork and sample HLS
backend/alembic/           immutable initial DDL and additive revisions
backend/scripts/           contracts, test media, explicit operator replay
backend/tests/             unit and real Postgres/Redis integration tests
frontend/src/features/     auth, feed, listing, chat, moderation screens
frontend/src/api/          generated OpenAPI types and fetch client
frontend/src/shared/       identity context, dialog and reconnect hook
frontend/public/           PWA manifest, icon, restricted asset service worker
frontend/tests/            two-account Playwright journey
infra/                     Nginx, PgBouncer and observability configuration
.github/workflows/ci.yml   checks, image builds, migration drift and browser flow
```

Routers call services and make no database calls. Domains privately own persistence and expose service interfaces; some bounded writes and the compact dealer workflow remain colocated with orchestration in this initial scaffold. Keep future persistence behind the module repository and extract those remaining statements as features grow. Domain services never read another module's tables; metadata registration, migrations, bootstrap and explicit operator/test utilities are infrastructure exceptions.

## Implemented local path

Auth uses E.164 validation, expiring/attempt-limited Redis challenges, atomic OTP consumption, signed ten-minute access JWTs, hashed rotating refresh credentials, reuse-family revocation, authoritative account checks and expected-Origin cookie mutations. Development code `123456` is visibly labelled; no SMS provider is called.

Listings enforce phone/adult/rights requirements, typed car validation, seller/key uniqueness and conflicting-replay rejection. Ownership checks protect draft media, saves are idempotent and sold listings leave the feed. The local frontend location picker is deliberately coarse Dublin centre; API and CSV inputs support the bounded launch area.

Uploads use 8 MiB presigned parts directly to SeaweedFS's S3 endpoint. Resume reconciles actual stored parts and renews signed URLs; full-file SHA-256 checks prevent mixing files. Draft creation keeps its exact request/key across refreshes, including a lost creation response. Completion verifies actual parts/size and reconciles an already-completed object after a lost response. Workers validate 15–60 seconds, produce 360×640 and 720×1280 HLS with optional AAC audio, posters/thumbnails and a dHash, strip metadata and keep derivatives private until approved. Silent input remains supported. Invalid or exhausted processing is visible as failed; the seller can retry a retained source up to three times or explicitly replace it on the same advert. Generation checks isolate late jobs/completions from replacements and retries.

The **My cars** dashboard lists owned adverts with status filtering and signed keyset pagination. Owners can edit typed details/prices, pause/resume approved adverts, mark published cars sold and recover video uploads. Revision checks reject stale edits/actions. Edits recheck moderation, and flagged edits withdraw the advert for review. Each edit revision can open a new review even if an earlier review with the same text was resolved. Paused preference survives subsequent moderation approval; sold/removed adverts cannot be edited or accept new media.

The feed applies geographic/price/make/year SQL filters and freezes a bounded ordered candidate snapshot for five minutes. A replaceable heuristic and seen penalties are present; the engagement aggregate starts at zero. Redis candidate revisions/TTLs and current visibility/block checks protect publication state; initial requests fall back to recency when cache/ranking fails, while unavailable ranked continuation state returns a restart response.

Chat has one conversation per listing/buyer, REST persistence before delivery, sender-scoped idempotency, scam-pattern warnings, read receipts and Redis user-channel fan-out. WebSockets consume a one-use first-frame ticket; REST history and polling recover missed transport events. Viewings support revision-checked propose/accept/decline/cancel/counter, preserved counter history, public-place tips, accepted-only calendar exports and durable local reminder records.

Reports, symmetric blocks, local text/hash checks and admin approve/remove/suspend actions with reasons are implemented. Dealers have queued CSV row validation, row errors/draft IDs and matching-video uploads through the regular pipeline. Optional analytics batches are consent-checked and deduplicated. Consent withdrawal prevents further seen-history reads, queued workers recheck consent, and a durable event clears that cache; raw-event retention/erasure is still release work. Reminders carry a proposal revision and recheck current status before local delivery.

The outbox relay uses leases, bounded retry/backoff and dead letters. Explicit operator replay preserves the original delivery key for deduplication; the original exhausted record remains. Structured logs, request/job IDs, health/readiness, Prometheus metrics, OTel/Sentry hooks and optional dashboard/alert configuration are provided. No alert recipient or external telemetry destination is configured by default.

## Production release gates

`Settings.production_guard` refuses `APP_ENV=production`. Remove it only as part of a reviewed release implementing these requirements:

- Real EU-reviewed SMS, verified optional email and opt-in push providers; delivery receipts/preferences, provider idempotency and outbound rate/abuse controls.
- Managed EU VideoProvider, authenticated/replay-protected callbacks, encoder isolation and hostile-media review, source lifecycle cleanup, CDN residency/removal/purge workflows and audio policy.
- Prohibited-content/frame scanning, calibrated price anomalies and perceptual-distance/multi-frame matching, staffed evidence views/review coverage, public notices where required, delivered statements of reasons and appeals.
- Privacy export/erasure across all modules/providers, retention enforcement, consent audit history, deletion ledger and restore reapplication, policy publication and GDPR/DSA legal review.
- Configured regions and map selection, additional category adapter/form/schema when needed, complete dealer/operator screens and notification inbox UI.
- Server-generated engagement aggregates, ranking abuse resistance, mature inbox/history ordering, bounded socket buffers and reconnect jitter, accessibility and real iOS/Android/4G tests.
- Independent production worker pools, broker/cache isolation, TLS/secret rotation, least-privilege credentials, redundant ingress/API, managed EU database/PITR, tested object/database recovery and release/load runbooks.

The notification table stores local records but no complete inbox screen exists yet. SMS/email/push and automated visual-content judgments are not simulated as successfully sent or approved production integrations. Public-production readiness, legal compliance, availability and scale are not established by the local checks.

## Local operations

`docker compose up --build` migrates once, generates owned samples and starts Nginx, API, workers, relay, PostgreSQL/PostGIS, PgBouncer, Redis and SeaweedFS. Use `127.0.0.1:15432` for native migration/test tooling; application requests use PgBouncer with psycopg prepared statements disabled. Redis uses AOF/noeviction locally; production should isolate broker and cache pressure.

The API has no published host port. Local Uvicorn trusts forwarded headers inside the Compose network because Nginx overwrites forwarding input; production must restrict trusted proxy CIDRs and ingress reachability. Health/metrics belong on an internal operations network. The optional observability Compose file supplies local Prometheus/Grafana, not operational paging or managed backups.

```sh
docker compose ps
docker compose logs --tail=100 api worker relay
docker compose exec api alembic current
docker compose exec api alembic check
docker compose exec api python scripts/replay_dead_letter.py DEAD_UUID "provider repaired; approved replay"
docker compose exec api python scripts/close_test_listings.py
```

The last command only marks this project's synthetic live `Playwright car …` listings sold when their seller name is exactly `Playwright seller`; it never deletes accounts, chat or audit records. Normal browser tests close their listing through the UI.

For Vite hot reload, align `PUBLIC_ORIGIN` with `http://localhost:5173` in backend/storage and rerun initialization for bucket CORS, then run `npm run dev` in `frontend/`; its proxies target Nginx. The default one-command setup needs none of that configuration. No paid infrastructure or GitHub remote was created.
