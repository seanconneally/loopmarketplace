# Motorloop

**See the car. Hear its story. Find your next drive nearby.**

A video-first local car marketplace: FastAPI modular monolith, React PWA, direct multipart uploads, background HLS processing and durable chat/viewing proposals. Working launch assumptions: Dublin, Ireland; EUR; English; EU production hosting.

This folder contains **all ten design deliverables and a runnable local development scaffold**. Real provider integrations, privacy workflows and production operations remain explicit [release gates](docs/09-scaffold.md).

## Run locally

With Docker Desktop running Linux containers, open a terminal in this folder:

```sh
docker compose up --build
```

Open **[localhost:8080](http://localhost:8080)** after initialization finishes. The first run downloads images and generates three original illustrated 15-second HLS clips; allow a few minutes. No paid credentials or third-party advert footage is required.

Background start: `docker compose up -d --build`. Stop: `docker compose down`. Data persists in named volumes; adding `-v` would erase those volumes.

| Local access | Value |
| --- | --- |
| App | <http://localhost:8080> |
| Development OTP | `123456`, shown in the sign-in dialog; SMS is simulated |
| Sample verified dealer | `+353860000001` |
| Sample moderator | `+353860000099` |
| Other valid E.164 phone | Creates an ordinary local member after verification |
| PostgreSQL | `127.0.0.1:15432` (container port 5432) |
| Redis / S3 storage | `127.0.0.1:6379` / `localhost:9000` |

All published development ports bind to loopback. Compose works without copying `.env.example`; never reuse its development credentials publicly. `APP_ENV=production` intentionally refuses startup until production adapters and release controls are implemented.

## Try it

1. Browse videos and filter by make, budget, distance and year; save a car after signing in.
2. Enter a name and confirm 18+ to sell; upload an owned 15–60 second MP4/MOV of at most 500 MiB and add car details.
3. Clean videos publish after processing; suspicious text/hash matches wait for review. Invalid or exhausted work is exposed as failed.
4. Use a separate browser profile/account to message the seller, propose a public viewing, and accept/decline/counter from the other account. Accepted viewings export to `.ics`.
5. Report a listing/conversation, block a member, or mark your own live listing sold.
6. The sample dealer has **Dealer studio** for [CSV inventory](docs/dealer-template.csv) plus matching owned videos; the sample moderator has the review queue.

**My cars** is the seller dashboard at [localhost:8080/my-cars](http://localhost:8080/my-cars). It includes saved drafts and status filters, editing prices/details, pausing/resuming approved adverts, marking sold, and retrying or replacing failed videos. On mobile, open **Account → My cars**. See the [seller and upload guide](docs/seller-uploads.md).

Interrupted uploads resume on the **same advert**, sending only missing parts. Reselect the original video after a refresh; a full-file fingerprint prevents mixing different files. New processed videos retain audio; playback starts muted with an unmute button. Existing silent derivatives need to be regenerated from an audible original to gain sound.

No outbound SMS, push or email is sent. Dealer/admin identities are development fixtures, not production account provisioning.

## All ten deliverables

| # | Document |
| --- | --- |
| 1 | [Assumptions and open questions](docs/01-assumptions.md) |
| 2 | [Architecture and component diagram](docs/02-architecture.md) |
| 3 | [Upload, message and viewing sequences](docs/03-sequences.md) |
| 4 | [Database decisions and index rationale](docs/04-database.md) · [complete SQL DDL](docs/schema.sql) |
| 5 | [API and WebSocket contracts](docs/05-api.md) · [OpenAPI](docs/openapi.json) · [event JSON Schema](docs/websocket-events.schema.json) |
| 6 | [Ranking and cache invalidation](docs/06-feed-ranking.md) |
| 7 | [Scaling, reliability and cost maths](docs/07-scaling-costs.md) |
| 8 | [Trust, safety, GDPR and DSA — legal review required](docs/08-trust-safety-compliance.md) |
| 9 | [Scaffold, repository and release gates](docs/09-scaffold.md) |
| 10 | [MVP, v1 and scale roadmap](docs/10-roadmap.md) |

The [original brief](docs/source-prompt.txt) is preserved; its review pauses were overridden by the instruction to complete the project. [Architecture decisions](docs/adr/README.md) record the major trade-offs. [Validation](docs/validation.md) records exact checks and limits.

## Repository and checks

```text
backend/     FastAPI modules, services/repositories, Alembic, pytest, workers
frontend/    React features, PWA shell, generated API types, Vitest/Playwright
infra/       Nginx, PgBouncer, Prometheus/Grafana
docs/        Design, SQL, contracts, ADRs and screenshots
.github/     CI: lint, strict types, tests, migration drift and image builds
```

Backend: create a Python 3.12 virtual environment, install `pip install -e '.[dev]'` from `backend/`, then run:

```sh
ruff check app tests scripts
ruff format --check app tests scripts
mypy app
pytest -m 'not integration'
alembic check
```

With Compose running, set `RUN_INTEGRATION=1` and run `pytest -m integration`. The Windows test setup uses a Psycopg-compatible selector loop; application containers run Linux/Python 3.12.

Frontend, from `frontend/`, using Node 22+:

```sh
npm ci
npm run lint
npm run format:check
npm run build
npm test
npx playwright install chromium
npm run test:e2e
```

Playwright needs the running stack and Docker CLI. It generates an original clip, uses two synthetic accounts, completes upload → feed → message → viewing acceptance, marks its listing sold, and saves screenshots in `docs/screenshots/`.

Regenerate contracts with `python scripts/export_contracts.py` in `backend/`, then `npm run generate:api` and `npx prettier --write src/api/generated.ts` in `frontend/`. Add migrations for schema changes; do not regenerate the immutable `0001` snapshot.

Optional dashboards: `docker compose -f compose.yaml -f compose.observability.yaml up -d`. Grafana uses `localhost:3000`, Prometheus `localhost:9090`; alert delivery and production telemetry destinations are not configured. Availability, 4G playback and 100k-MAU targets require further real-device/load validation.
