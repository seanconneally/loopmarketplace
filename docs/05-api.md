# 5. API and WebSocket contracts

REST is under `/api/v1`. FastAPI's generated `/openapi.json` and Pydantic schemas are the executable HTTP contract; export that document and regenerate the strict TypeScript client whenever routers/schemas change. See [FastAPI's OpenAPI documentation](https://fastapi.tiangolo.com/how-to/extending-openapi/).

**Status legend:** `Present` means the route/service was inspected in the scaffold source; `Planned` is designed production work without an implemented endpoint. Present does not mean runtime-tested or production-ready; the separate verification report records actual checks. `APP_ENV=production` deliberately rejects startup because the production adapters and release gates are incomplete. The user has overridden the original pause checkpoints.

## Shared rules

- Bearer access tokens are short-lived and kept in client memory; refresh credentials rotate in an HttpOnly cookie restricted to `/api/v1/auth`, Secure in production and SameSite Strict.
- Cookie-bearing verify/refresh/logout requests must have the configured exact `Origin`; unsafe cross-origin cookie operations are rejected. Production CSRF/Origin behaviour must be tested with the deployed ingress.
- Domain creation requires `Idempotency-Key` with 8–64 characters. Listings, media allocation, messages, viewing proposals, reports, admin actions and dealer imports enforce operation-specific duplicate/conflict rules; conversation creation instead deduplicates by the natural `(listing_id, buyer_id)` pair and does not persist the supplied header. OTP/ticket issuance has dedicated security semantics and limits rather than replaying one-time credentials.
- Collection responses contain `items` and an opaque signed `next_cursor`, which is `null` at the end. Clients must not parse cursors or substitute offset pagination. Feed cursors bind filter fingerprint and identity.
- UUIDs identify entities; price is integer cents, durations seconds, mileage kilometres, radius kilometres and timestamps ISO 8601 with timezone.
- Errors return the same safe envelope; raw database errors, phone numbers, tokens and stack traces are never sent to clients.
- All authorization is enforced in services: current account/session state, verification, ownership, conversation membership, adult seller declaration, dealer/admin permissions and blocking.

```json
{
  "error": {
    "code": "cursor_expired",
    "message": "Refresh the feed to continue.",
    "request_id": "7bb129ec-8dd4-4f62-a22f-4bf862cf00ac"
  }
}
```

Use `401` for absent/invalid authentication, `403` for rejected permission/origin, `404` when a resource is unavailable to the caller, `409` for state/idempotency conflicts, `410` for expired feed snapshots, `422` for invalid input, `429` for rate limits and `503` for a dependency preventing a safe action. Reverse-proxy/storage errors are separate transport failures; the frontend must handle non-JSON error responses safely.

## Endpoint table

Paths below omit the `/api/v1` prefix except health/docs and WebSocket notes.

| Method | Path | Authentication | Purpose | Status |
| --- | --- | --- | --- | --- |
| POST | `/auth/otp/request` | Public, phone/IP limits | Request challenge for E.164 phone | Present |
| POST | `/auth/otp/verify` | Public challenge + exact Origin | Consume OTP, issue access token and refresh cookie | Present |
| POST | `/auth/refresh` | Refresh cookie + exact Origin | Rotate token; revoke family on reuse | Present |
| POST | `/auth/logout` | Refresh cookie + exact Origin | Revoke session family and clear cookie | Present |
| POST | `/auth/ws-ticket` | Bearer | Mint thirty-second single-use WebSocket ticket | Present |
| GET | `/users/me` | Bearer | Current safe profile, excluding hidden contact data | Present |
| PATCH | `/users/me` | Bearer | Update display name, adult declaration and analytics consent | Present |
| POST | `/listings` | Verified adult seller + key | Create typed car draft with rights confirmation | Present |
| GET | `/listings/{listing_id}` | Public | Public live/sold listing details; no hidden contacts | Present |
| GET | `/listings/{listing_id}/owner` | Owner | Draft/processing/review details for seller | Present |
| GET | `/listings/mine` | Bearer | Owned adverts including drafts; optional status filter and identity-bound cursor | Present |
| PATCH | `/listings/{listing_id}` | Verified adult owner | Update complete typed details with revision; recheck moderation and update feed projection | Present |
| POST | `/listings/{listing_id}/pause` | Owner | Pause approved advert with revision check; remove feed candidate | Present |
| POST | `/listings/{listing_id}/resume` | Owner | Resume approved advert with revision check | Present |
| POST | `/listings/{listing_id}/sold` | Owner | Mark sold; remove feed candidate | Present |
| PUT | `/listings/{listing_id}/save` | Bearer | Idempotently save listing | Present |
| DELETE | `/listings/{listing_id}/save` | Bearer | Idempotently unsave listing | Present |
| GET | `/listings/saved` | Bearer | Cursor page of saved listings | Present |
| GET | `/feed` | Optional bearer | Filtered ranked or recency-fallback page | Present |
| GET | `/feed/options` | Public | Up to 200 distinct makes from published inventory for discovery controls | Present |
| POST | `/media/listings/{listing_id}/upload` | Owner + key | Allocate direct multipart upload | Present |
| POST | `/media/{asset_id}/complete` | Owner | Submit part ETags, finalize and queue processing | Present |
| GET | `/media/{asset_id}` | Owner | Poll asset status and media metadata | Present |
| POST | `/media/{asset_id}/resume` | Owner | Verify SHA-256/size; reconcile stored parts and renew signed URLs | Present |
| POST | `/media/{asset_id}/retry` | Owner + key | Retry failed processing from retained source, up to three seller retries | Present |
| POST | `/conversations` | Verified member + key | Get/create unique conversation for a listing and buyer | Present |
| GET | `/conversations` | Verified member | Cursor page of own conversations | Present |
| GET | `/conversations/{conversation_id}/messages` | Participant | Cursor page of durable message history | Present |
| POST | `/conversations/{conversation_id}/messages` | Verified participant + key | Persist message and scam warning annotations | Present |
| PUT | `/conversations/{conversation_id}/read` | Participant | Monotonically advance read receipt to message_id | Present |
| POST | `/viewings` | Participant + key | Propose time/place attached to conversation | Present |
| GET | `/viewings?conversation_id={id}` | Participant | Cursor page of conversation viewings | Present |
| POST | `/viewings/{viewing_id}/respond` | Participant | Accept, decline, cancel or counter with revision check | Present |
| GET | `/viewings/{viewing_id}/calendar` | Participant | Export private accepted-viewing `.ics` event | Present |
| POST | `/moderation/reports` | Bearer + key | Report listing, user or message | Present |
| PUT | `/moderation/blocks` | Bearer | Block target user idempotently | Present |
| DELETE | `/moderation/blocks/{target_id}` | Bearer | Remove own block | Present |
| GET | `/moderation/queue` | Admin | Cursor page of open reports/review cases | Present |
| POST | `/moderation/actions` | Admin + key | Approve/remove/suspend with audited reason | Present |
| POST | `/analytics/events` | Consenting member | Append validated bounded batch of product events | Present |
| POST | `/dealer/imports` | Verified dealer + key | Queue CSV validation and draft creation; HTTP 202 | Present |
| GET | `/dealer/imports/{job_id}` | Import owner, verified dealer | Poll per-row draft/video-filename/error results | Present |
| POST | `/notices` | Public, abuse controls | Account-free illegal-content notice route and acknowledgement | Planned |
| POST | `/moderation/appeals` | Affected user + key | Appeal a recorded decision and track its outcome | Planned |
| POST | `/users/me/exports` | Step-up bearer + key | Queue machine-readable data export | Planned |
| GET | `/users/me/exports/{id}` | Request owner | Poll export and receive expiring private download | Planned |
| POST | `/users/me/deletion` | Step-up bearer + key | Queue verified erasure/deactivation workflow | Planned |
| PUT | `/notifications/preferences` | Bearer | Configure verified email/push opt-ins | Planned |
| POST | `/notifications/subscriptions` | Bearer + key | Register an authorized browser push subscription | Planned |
| POST | `/webhooks/video/{provider}` | Provider signature, no user cookie | Authenticate completion event and reconcile job | Planned |
| POST | `/media/{asset_id}/abort` | Owner | Cancel/abort incomplete multipart upload | Planned |

Operational paths are `GET /health/live`, `GET /health/ready`, `GET /metrics`, generated `GET /openapi.json`/`GET /docs`, and WebSocket `/ws`, all outside `/api/v1`. Readiness returns database unavailability as `503` and Redis loss as a degraded status; it does not imply write operations remain available. There is no notification-list or subscription router yet; local notification records are worker-owned database effects.

## Important payloads

OTP request accepts `{phone}` in E.164 form; verify accepts `{phone, code}`. The local adapter deliberately exposes a `development_code`; production must reject this adapter/configuration, deliver a real SMS asynchronously and omit development codes. The token response contains `{access_token, token_type, user}` and the refresh credential appears only in its cookie.

Listing creation accepts title/description, `price_cents`, coarse `area`, coordinates, configured `region_id`, category, `rights_confirmed: true` and typed `car: {make, model, year, mileage_km, fuel, transmission}`. The present launch schema permits Dublin/cars only; configurable category/region adapters are the extension boundary and their full registration mechanism must be completed before a second launch.

Upload allocation accepts `{name, size, content_type}` and returns `{asset_id, upload_id, part_size, part_urls}`; `part_urls` is an ordered string array, with one-based part numbers and `part_size = 8,388,608` bytes. Part URLs expire after 900 seconds, declared `size` is at most `500 × 1024 × 1024` bytes, and MIME is `video/mp4` or `video/quicktime`. Completion accepts `{parts: [{part_number, etag}]}`, with 1–64 ordered contiguous parts. `MediaView` contains `id`, `listing_id`, `status`, nullable `playback_url`, `poster_url`, and `duration`; status polling does not currently include a detailed error object. The server chooses the object key and never accepts a seller-supplied playback URL.

Conversation creation accepts `{listing_id}`; the seller comes from listing services and buyer is the authenticated actor. Message creation accepts `{body}` with `Idempotency-Key`, never caller-supplied sender/recipient IDs. Server responses include persisted identifiers/timestamps and scam-warning fields defined by the final MessageView schema.

Viewing creation accepts `{conversation_id, starts_at, place}`. Responses carry a `revision`; respond accepts `{action, revision}` and, for counterproposals, replacement `starts_at`/`place`. Stale revision or an invalid actor/state transition returns `409`/`403`; clients refetch rather than forcing the transition.

Dealer import accepts `{csv_text, rights_confirmed: true}` inside JSON, not a video archive; CSV text is 20–200,000 characters. A queued worker processes at most 100 rows, validates the same car draft schema and records per-row errors/draft IDs/`video_filename`. Poll `GET /dealer/imports/{job_id}` for `{id, status, rows}`; upload each video through the ordinary media API. CSV success does not make drafts live, and business-verification administration remains operational/manual work.

Analytics accepts `{events: [...]}` with 1–100 items containing `client_event_id: UUID`, `listing_id: UUID`, `event_type: "impression" | "watch" | "save" | "message"` and `value` from 0 to 3,600. It returns `204`, deduplicates client IDs and returns `403 consent_required` without current opt-in. The local worker adds impression IDs to a seven-day seen set; the full validated engagement aggregate pipeline is planned. Essential security logs use a separate purpose and no arbitrary client value directly raises rank.

## Limits

The inspected OTP implementation limits requests to ten per IP per ten minutes, three per phone per ten minutes and five verify attempts per phone per five minutes. Middleware limits unsafe API requests to 120/minute by observed client IP and fails closed when Redis cannot supply a safe decision; these are development starting values. Production still needs per-user/new-account limits, trusted-proxy configuration and `Retry-After` where practical. Feed radius caps at 100 km; message bodies at 4,000 characters; viewing place text at 5–300 characters; report/action reasons at 5–1,000. Upload duration/container checks happen in the worker, not by trusting input fields.

## WebSocket protocol

Personal loop additions: authenticated `PUT /feed/feedback` with `{listing_id}` hides an advert, `DELETE /feed/feedback/{listing_id}` undoes that member's dismissal, and `DELETE /feed/preferences` resets their learning cutoff. Analytics also accepts `completion` values from zero to one. Strong save/message/negative signals come from authorized server actions rather than client analytics. See [personal loop contracts and ranking](personal-loop.md).

Gateway path: **`/ws`**. First obtain a one-use ticket over authenticated REST, open a same-origin WebSocket, and send the ticket as the **first frame**, not a query parameter. The first frame must arrive within ten seconds; the ticket expires after thirty. The gateway checks Origin, atomically consumes the ticket, validates current session/account state, subscribes only to the authenticated user's channel and revalidates idle access every fifteen seconds by default (`WEBSOCKET_AUTH_INTERVAL`, 1–30 seconds). Conversation events also recheck current membership/block policy. Invalid access closes with policy-violation code `1008`; reconnect with jittered backoff and a fresh ticket. On connection, the client refetches durable cached state and uses a 45-second silence watchdog. The client sends no other application frames after authentication.

```json
{"ticket":"opaque-single-use-value"}
```

The implemented event shape is a discriminated `{type, data}` object serialized by the worker; it strips internal routing fields such as `recipients` and `user_id`. Producers use entity Pydantic views for message/viewing payloads; a dedicated validated WebSocket union/schema registry is still planned. Never treat an event as an authorization grant or the sole copy of a message.

| Type | Direction | Payload schema | Delivery/recovery |
| --- | --- | --- | --- |
| `listing.status` | Server → authorized owner | `{listing_id: UUID, status: ListingStatus}` | Refetch owner listing or media status if missed |
| `message.created` | Server → conversation participants | `{conversation_id: UUID, message: MessageView}` | Deduplicate message ID; refetch durable history on reconnect |
| `viewing.updated` | Server → conversation participants | `{viewing: ViewingView}` | Refetch structured conversation/viewing state; compare revision |
| `message.read` | Server → participants | `{conversation_id: UUID, reader_id: UUID, message_id: UUID, read_at: ISODateTime}` | Present; durable message read timestamps remain authoritative |
| `block.changed` | Server → both affected members | `{target_id: UUID}` | Present; invalidate relevant views, while services already enforce blocks |
| `heartbeat` | Server → authenticated client | `{}` | Present; transport liveness, sent every fifteen seconds while idle |
| `session.revoked` | Server → affected session | `{reason: string}` | Planned convenience event; current server already revalidates and closes invalid access |

`ListingStatus` uses draft, processing, pending_review, live, sold, failed and removed in local service transitions. `MessageView` contains `{id, conversation_id, sender_id, body, message_type, viewing_id, warnings, created_at, read_at}`, with nullable viewing/read fields. `ViewingView` contains `{id, conversation_id, proposed_by, starts_at, place, status, revision, history}`. These views exclude hidden account contact fields; message bodies and private meeting details remain participant data. Unknown event types should be ignored safely and trigger no mutation.

A richer production event envelope should add stable `event_id`, `occurred_at`, `schema_version` and entity revision so clients can deduplicate, observe lag and evolve schemas. Until present in producers, those fields are **planned**, not guaranteed. Persistent history plus REST polling is the compatibility path when a browser, proxy or Redis connection drops.

## Current marketplace contracts

Listing creation/editing accepts cars, homes, golf or other. Car is nullable and required only for cars; attributes contains validated category facts. Feed category accepts cars/homes/golf or omission for the mixed FYP; other has no browse filter. Playback analytics also accepts bounded replay and recent occurred_at timestamps. Generated OpenAPI and frontend types are current; see [category design](marketplace.md) and [personal loop](personal-loop.md).
