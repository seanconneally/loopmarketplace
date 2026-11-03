# Functionality, reliability and maintainability review

Reviewed locally on 3 November 2026. The changes below address verified code paths and regression cases. They do not certify production capacity or remove the existing production startup guard.

## Changes implemented

| Area | Finding | Improvement and evidence |
| --- | --- | --- |
| Public feed | Each item performed separate active-seller, block and save checks | Batch lookups through owning module services preserve current visibility and saved flags. A real database test limits the ten-item ranked page to eight SELECTs, including candidate selection and visibility checks. Existing filter, pagination and hidden-advert integration cases still run. |
| Inbox summaries | Each row repeated membership, identity, title and block queries | Bounded batch lookups through users, listings and moderation interfaces. A 25-conversation integration fixture verifies both block directions, suspended accounts, pagination and at most five SELECTs per page. No cross-module table joins were introduced. |
| Reminders | A blocked/suspended participant raised a domain error that rolled back the entire scheduler batch | Ordered batches of at most 100 rows use `SKIP LOCKED`; ineligible reminders are marked handled and skipped. Delivery checks authority again, including blocks added after scheduling. Tests cover batch boundaries, no duplicate scheduling and suppression of an already queued reminder. |
| Duplicate jobs | Duplicate Celery delivery could occupy a worker waiting behind a job's row lock | Workers skip an already locked event. The durable relay lease still recovers interrupted work. Failure bookkeeping also takes a lock and does not overwrite a completed event. A real concurrent database test verifies no waiting and one effect on replay. |
| Realtime idle load | Every socket checked account/session authority against Postgres every second | Checks occur every 15 seconds by default, with conversation access checked for every conversation event. Heartbeats are sent every 15 seconds when idle. The clock-controlled regression verifies three checks over 31 seconds rather than one per iteration. |
| Reconnect recovery | Pub/sub events lost during disconnect did not automatically refresh all affected cached data | On connection the client invalidates durable chat/viewing/conversation, feed, saved and seller queries. Jitter spreads retry timing, and a 45-second silence watchdog replaces half-open connections. Cleanup cancels retries. Block changes notify both members and refresh affected views. |
| Session races | A delayed refresh could replace a newer login or reintroduce an old token after local sign-out | Versioned token updates discard stale refresh results. Concurrent 401s share a refresh; late 401s reuse the already renewed token. Calendar export now also refreshes expired access. Tests cover stale refreshes, concurrent failures and retained mutation keys. |
| Chat history | Only the first 20 conversations, latest 50 messages and first 20 viewings were reachable | Explicit cursor controls load further pages. Older messages remain chronological and are deduplicated by ID. Query errors are visible. Per-conversation drafts prevent text moving to another seller. |
| Ambiguous network results | Clicking retry after a message or new viewing was saved but its response was lost generated another operation key | The same unchanged operation retains its key. The recovery follow-up also persists message keys/text in tab-scoped storage, so message retry after reopening retains the key; new viewing keys last while the form remains mounted. Successful delivery clears the key; editing an operation creates a new one. Pending new viewing submissions are disabled. See [recovery and mobile readiness](recovery-and-mobile.md) for persistence limits. |
| Redis and publishing | Application Redis connections did not set explicit timeout/pool bounds | Configurable connect/read timeouts and a bounded pool. Automatic command retries are disabled so an ambiguous `INCR`/`GETDEL` response cannot be blindly repeated. Celery publishing retries and connection attempts are bounded separately. |

## Runtime configuration

Compose passes these through from the environment or root `.env`; defaults are also validated by application settings:

| Variable | Default | Meaning |
| --- | --- | --- |
| `REDIS_CONNECT_TIMEOUT` | `2` | Connection attempt timeout, seconds |
| `REDIS_SOCKET_TIMEOUT` | `5` | Redis command socket timeout, seconds |
| `REDIS_MAX_CONNECTIONS` | `256` | Maximum application Redis connections per process |
| `WEBSOCKET_AUTH_INTERVAL` | `15` | Idle account/session authority check interval, seconds; allowed range 1–30 |

Each active WebSocket subscription occupies a Redis connection from this pool. These development defaults are not a thousands-of-sockets capacity setting. Size replica count, per-process pool limits, Redis `maxclients`, database/PgBouncer capacity and gateway connection limits together before increasing traffic. Logout/suspension on an idle socket can take up to the configured interval, plus query/transport time; normal API requests continue to authorize against current state.

## Verification and repeatable smoke check

The full backend suite runs against real PostgreSQL/PostGIS, Redis and S3-compatible storage with ffmpeg. Frontend tests cover session races, realtime recovery, upload fingerprints, filter state, chat pagination/drafts and ambiguous message/viewing responses. The five Playwright journeys exercise actual upload processing, chat/viewing acceptance, seller editing/pause/resume/sold, upload recovery, failed-video retry, discovery/share/saved and desktop/mobile page checks. See [validation](validation.md) for the recorded results.

Run the read-only gateway smoke check from the project root with Node 22+ and the local stack running:

```sh
node scripts/smoke-load.mjs
```

It sends 200 reads across ranked/newest feeds, available makes and a direct advert, with at most ten concurrent requests and a target of ten requests/second. It reports actual elapsed time, latency percentiles, HTTP/network failures and achieved throughput. `BASE_URL`, `REQUESTS`, `CONCURRENCY` and `TARGET_RPS` are configurable and bounded. Run it separately from browser tests to avoid mixing workloads. It consumes response bodies, checks status/error envelopes and fails on request errors.

An initial unpaced 200-request burst hit the gateway's intentional 20 requests/second per-IP limit (119 responses were 429). That is a rate-limit observation, not evidence of backend saturation; the default smoke check is paced below that limit. Do not disable the gateway limiter to make a benchmark look better.

The [recorded paced run](benchmarks/read-smoke-2026-11-03.json) completed 200 requests at ten requests/second, with zero failures, p50 12 ms, p95 19 ms and maximum 109 ms. It used sample inventory on this local Docker stack, not representative production data or network conditions.

## Remaining production work

- Measure with representative inventory, message history, active sockets, devices and traffic distribution. The sample inventory smoke check cannot demonstrate a 100k-MAU target, sustained throughput or a production p95 SLO.
- Separate media and ordinary workers into independently sized deployments; the development worker currently consumes both queues. Encoding still holds a background-work database transaction and is bounded by the existing worker timeout/lease; profiling and managed encoding remain release work.
- Add managed database backups/PITR and prove restores, storage lifecycle rules, outbox/notification retention, CDN delivery/removal and multi-instance failover. No automatic deletion was introduced in this pass.
- Review real query plans and growth. Keyword substring matching, richer ordering/indexes, long histories and moderation/report queues need realistic-volume benchmarks. Older loaded chat pages are refetched with active history; very large inbox sessions may need a separate immutable-history cache/virtualization strategy.
- Expose operational alerts for queue age/dead letters, connection exhaustion, error rates, media failures and storage costs. Existing optional metrics/dashboard configuration is not deployed paging.
- Implement and verify real auth/media/notification adapters and the other [release gates](09-scaffold.md). Production startup stays blocked.

The design remains a modular monolith with owning-module repositories, typed service boundaries, generated API contracts and existing revision/idempotency rules. These changes add bounded work and focused regression tests without adding infrastructure services or changing the database schema.

Implementation references: [PostgreSQL SELECT and queue locking](https://www.postgresql.org/docs/16/sql-select.html), [Redis client timeouts and production usage](https://redis.io/docs/latest/develop/clients/redis-py/produsage/).
