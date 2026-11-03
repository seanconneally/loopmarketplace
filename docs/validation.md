# Validation record

Validated locally on 3 November 2026. These checks establish the scaffold's local behaviour, not production SLOs or legal compliance.

| Check | Result |
| --- | --- |
| Docker Compose build/start with `--wait` | Passed; Nginx, API, Celery worker, relay, PostgreSQL/PostGIS, PgBouncer, Redis and SeaweedFS healthy; initialization exited successfully |
| Python runtime | Application images run Linux/Python 3.12 |
| Backend full suite in Python 3.12 container | **24 passed**: thirteen domain/provider/realtime/ranking tests and eleven integration cases, including different user interests, signal caps/decay, diversity, feedback isolation/undo, reset/opt-out and existing real Postgres/Redis/S3/ffmpeg journeys |
| Backend strict typing | `mypy app`: no issues in 79 source files |
| Backend lint/format | Ruff check and format check passed |
| Schema creation/upgrades | Alembic `0001` → `0002` → `0003` → `0004` → `0005` applied successfully; existing volumes preserved |
| Schema drift | `alembic check`: no new upgrade operations detected, including the PgBouncer-connected container check |
| Frontend strict TypeScript | Typecheck and Vite production build passed |
| Frontend lint/format | ESLint and Prettier checks passed |
| Frontend component/upload/search/session/realtime tests | **24 passed**, including explicit feed consent, local video preview cleanup/metadata and early validation, plus the existing auth/upload/search/recovery checks |
| Playwright Chromium | **6 end-to-end scenarios passed**: search/share/saved; upload/chat/viewing; interrupted upload and seller controls; failed processing/retry; public/member/dealer/moderator pages; personal-loop consent/watch/hide/undo/reset. Original processing now continues after upload handoff and failures are verified in My cars |
| Dedicated mobile browser profiles | **6 checks passed** across Android-style Chromium and iPhone-style WebKit: session states; injected render failure/retry; offline advert recovery, file assignment and constrained viewport. Chromium sample-video pause/resume passed; WebKit Windows does not certify iPhone playback |
| Physical-device acceptance | **Pending**: no connected iPhone or Android hardware facility was available; see the explicit [device checklist and limits](recovery-and-mobile.md) |
| Responsive regression | Verified 390×844 feed price remains above navigation, checked public/member/dealer/moderator pages for horizontal overflow, verified the locally hosted font loads, and visually reviewed desktop/mobile pages and dialogs |
| Audio preservation | Actual ffprobe inspection of both 360×640 and 720×1280 HLS segments: AAC retained for audible input, no audio for silent input; browser unmute verified |
| Playback observation | Visible clip playing at readyState 4 with advancing playback time; next two clips buffered and paused |
| Optional operations configuration | Main and optional observability Compose configuration validated; optional Prometheus/Grafana containers were not started |
| Paced gateway read smoke | **200 requests, zero failures**, target/actual ten requests/second, at most ten in flight; local sample-inventory p50 12 ms, p95 19 ms, max 109 ms; [raw result](benchmarks/read-smoke-2026-11-03.json) |

Earlier scaffold tests also ran natively on Windows/Python 3.14 during development. Windows tests use a selector event loop compatible with Psycopg, and shared Redis connections are closed between test loops. The final expanded suite used the rebuilt Linux/Python 3.12 application image with actual database, Redis, object storage and ffmpeg. Its public storage endpoint was set to `http://storage:9000` inside that test container so direct signed-URL requests resolve correctly there. ASGI integration clients use distinct test-only IPs so repeated test accounts do not share an OTP quota; application rate limits remain in place.

## What was exercised

Tests cover signed-cursor tampering, production-adapter guards, bounded ranking/seen penalties, scam-pattern warnings, timezone requirements and calendar escaping, listing validation and recovery from a lost successful S3 completion response. Integration cases cover draft idempotency/conflicts, private-draft visibility, refresh reuse revocation, real feed queries, unique messaging, warning payloads, viewing response authorization, analytics opt-in enforcement and symmetric blocking.

The browser scenario uses separate cookie jars/accounts, a newly generated original clip and actual direct storage PUTs; it does not intercept the API or replace the processing pipeline. The test accepts the viewing from the seller account and verifies the buyer sees the update. It then closes its synthetic listing through the seller UI. Only licensed-by-construction sample cars remain in the local feed.

The seller journey deliberately intercepts one draft creation response after the server commits, then aborts storage PUTs after the first successful part. It reloads the page, reuses the exact draft key, finds one advert, rejects an identically named/sized file with different bytes, and resumes without sending the first part again. It verifies a price/description edit in the feed, audio/unmute, pause removal, resume and sold. The failed-video journey confirms a real decoding error becomes actionable in My cars and the original can be retried without another upload. Backend cases also cover strict ownership, stale revisions, review withdrawal, repeated flagged-text review, paused preference after approval, closed-advert edits and stale upload generations.

The discovery integration case traverses 24 disposable adverts with equal-price/time ties in newest and both price orders, combined keyword/specification filters, literal percent search, validation and account/filter-bound cursors. A saved 20-item page fills around removed entries and permits removal of a hidden saved reference. A ranked continuation rechecks an advert moved outside its original budget. Browser verification includes an actual clipboard copy, a public advert opened in a separate session, URL/filter reloads, saved-list reopening/removal and no-result recovery. Responsive price checks wait for the browser's resize callback to settle before asserting the same navigation boundary. Generated Playwright traces are excluded from source linting.

## Evidence

The [UI refresh record](ui-refresh.md) describes the shared visual system and includes screenshots of the redesigned public, seller, dealer and moderation pages, plus upload and profile dialogs. Photos remain deferred.

The [reliability review](reliability-review.md) records the scheduler/worker/session/realtime changes, constant-query feed/inbox checks, repeatable smoke command and remaining scaling limits. The initial unpaced burst triggered the intended per-IP rate limit; the recorded paced smoke was run separately from browser scenarios.

The [recovery and mobile record](recovery-and-mobile.md) distinguishes browser emulation from pending hardware checks and explains exactly which drafts survive reopening, what happens on connection loss and how crash/session recovery was verified.

- [Desktop feed](screenshots/desktop.png)
- [Mobile feed](screenshots/mobile.png)
- [Accepted viewing](screenshots/viewing-accepted.png)
- [Seller dashboard](screenshots/seller-dashboard.png)
- [Mobile seller dashboard](screenshots/seller-mobile.png)
- [Discovery search and filters](screenshots/discovery-search.png)
- [Direct advert on desktop](screenshots/advert-desktop.png)
- [Direct advert on mobile](screenshots/advert-mobile.png)
- [Saved shortlist](screenshots/shortlist.png)

The HLS library is split into its own bundle, but Vite still reports a >500 kB uncompressed video-library chunk (about 187 kB gzip). That is a performance-budget item for the real-device/4G release work, not a build failure.

## Limits

No 100k-MAU load test, representative p95 latency test, 4G first-frame measurement, chaos/failover exercise, production restore drill, external provider verification, real-device push test, legal review or public cloud deployment was performed. The optional dashboards are supplied/configuration-checked; paging, managed EU telemetry and PITR need operational setup. Production startup remains intentionally blocked until [the release gates](09-scaffold.md) are implemented and reviewed.

CI is included; its GitHub execution has not been verified in this pass. Local checks exercised its principal lint/type/build/migration/test steps. The updated development stack is left running at [localhost:8080](http://localhost:8080), with existing data volumes preserved. Use `docker compose up -d --build` for a later restart/update.


## Loop Marketplace update — 3 November 2026

The product now has a mixed For you feed, Cars/Homes/Golf clubs filters, Something else for uncategorised adverts, category-aware creation/editing/details/saves and an adaptive interest-v2 recommender. Canonical generic routes and old car-link aliases are both covered. See [category design](marketplace.md) and [personal loop](personal-loop.md).

Final local results:

| Check | Result |
| --- | --- |
| Backend unit/integration regression | 28 passed; includes PostGIS category discovery, home editing, per-category prices and real-Redis concurrent adaptive-page retries |
| Frontend unit tests | 30 passed; includes generic forms, old car drafts, URL filters and account/reset-safe receipt queues |
| Desktop browser journeys | 7 passed in one sequential run; mixed FYP/filters, search/share/saves, golf upload → chat → viewing, personalization controls, interrupted multipart resume/edit/pause, processing retry and page review |
| Mobile browser profiles | 6 passed across Chromium Pixel 7 and WebKit iPhone 13 profiles |
| Contracts/build/static checks | OpenAPI/types regenerated; production web build, TypeScript, ESLint, Prettier, Ruff and strict mypy passed |
| Database | Existing data preserved through migration 0006; Alembic reports no schema drift |

Initial browser runs exposed label-selector ambiguity after renaming the picker and concurrent trace-output collisions. Selectors were corrected, mobile artifacts now use a separate ignored directory, and the final desktop run passed sequentially. Repeated sign-ins reached the development OTP quota; only the temporary local test-IP counter was cleared for the final run. Application limits were not weakened.

Compact desktop autoplay, mobile overflow and clip/control positioning were checked. Current captures: [compact](screenshots/loop-marketplace-compact.png), [mixed desktop](screenshots/loop-marketplace-desktop.png), [golf](screenshots/loop-marketplace-golf.png), [mobile](screenshots/loop-marketplace-mobile.png). Labelled original home/golf/other sample clips supplement the existing car samples. They are not real adverts or stock photos.

Actual phone hardware, representative production scale, recommender quality/conversion experiments and all existing public-release provider/privacy/operations gates remain pending. The earlier public-read smoke figures were not a benchmark of this adaptive recommender. Code remains local, uncommitted and unpushed.
