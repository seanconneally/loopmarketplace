# 4. Database schema

The complete executable PostgreSQL 16/PostGIS DDL is [schema.sql](schema.sql). It includes every table, primary/unique key, foreign key, check constraint and explicit index in the current scaffold. Run the Alembic chain rather than manually applying this snapshot to an existing database: `0001` creates the original tables, `0002` adds domain references, `0003` adds the source listing's generated geography point and GiST index, and `0004` adds seller revisions/pause state and resumable-upload/audio metadata.

## Model decisions

Prices are integer minor units with a three-character currency, timestamps are timezone-aware, identifiers are UUIDs, and phone numbers are canonical E.164. Members can buy and sell; `member`, `dealer` and `admin` distinguish privileges, with separate phone verification, adult declaration, business verification and account status. These declarations are checked by services at the moment of an action.

Car attributes live in `car_details`, a typed one-to-one table, rather than free-form JSONB: validation, range checks and make/year filtering are straightforward. Common listing lifecycle and ownership stay in `listings`; another category introduces its typed attributes and adapter without duplicating auth, media, messaging, viewings or moderation. This scaffold exposes cars explicitly; generic category forms and a region-configuration registry remain a future addition, not a claim that arbitrary categories already work.

`listings.location` is a stored, generated `geography(Point,4326)` derived from the coarse latitude/longitude, preventing conflicting coordinates. The independently owned `feed_candidates` projection also has a geographic point and only public data. Its IDs deliberately have no foreign keys: it is rebuildable and is always filtered against current authoritative visibility; business entities do have relational references, which do not authorize cross-module table queries.

Foreign keys normally restrict deletion. A privacy workflow must coordinate erasure/anonymization and retention through module interfaces; indiscriminate cascades across chat and audit history are not acceptable. Within an aggregate, `car_details`, `saves` and conversation messages have the explicit cascades shown in DDL. Polymorphic report/action targets cannot have a single SQL foreign key; services validate target type, existence and authorization, and audit records retain the identifiers after a lawful removal.

The one-conversation-per-listing/buyer constraint prevents duplicate threads. Message uniqueness is scoped to conversation, sender and client idempotency key, with payload conflicts rejected. A viewing counter preserves the prior revision as `status=countered` in JSONB history and keeps the active proposal's state `proposed`; row locking plus revision checks prevents competing responses. Read receipts timestamp incoming messages up to an authorized history position.

Outbox rows are committed with domain changes. `lease_until`, `available_at`, attempt count and terminal timestamps support recovery and backoff; `dead_letters` retains exhausted work. Sources and processed quarantine objects remain private, while `media_assets` records playback facts and an exact 64-bit dHash review signal. A matching hash is not a theft verdict, and approximate Hamming-distance search/multi-frame hashes are later fraud improvements.

## Explicit indexes and their reasons

| Index | Reason |
| --- | --- |
| `ix_blocks_reverse` | Finds blocks in the reverse direction for symmetric access policy. |
| `ix_conversation_buyer` | Narrows the buyer's conversation history without scanning all conversations. |
| `ix_conversation_seller` | Narrows the seller's conversation history without scanning all conversations. |
| `ix_events_listing` | Supports bounded event aggregation by listing, type and time. |
| `ix_events_time` (BRIN) | Summarizes naturally time-correlated append-only events cheaply. |
| `ix_feed_filters` | Narrows region/make/year/price candidates before ranking. |
| `ix_feed_location` (GiST) | Accelerates meter-based `ST_DWithin` searches on the feed projection. |
| `ix_feed_recency` | Supports region-local recency ordering with a unique cursor tie-breaker. |
| `ix_listings_live_recency` (partial) | Supports live-only recency operations without indexing historical drafts/sold items. |
| `ix_listings_seller_id` | Finds a seller's owned inventory for management and lifecycle work. |
| `ix_listings_owner_history` | Supports seller-scoped `(created_at,id)` descending keyset pages, including drafts and historical adverts. |
| `ix_listings_location` (GiST) | Keeps source listing radius queries/rebuild tooling independent of feed projection availability. |
| `ix_media_assets_perceptual_hash` | Finds exact perceptual-hash matches for duplicate review. |
| `ix_messages_history` | Supports conversation-scoped keyset history and read-position updates. |
| `ix_notifications_user_id` | Finds durable in-app notification records for a recipient. |
| `ix_outbox_pending` (partial) | Claims only unfinished work by due time instead of scanning completed history. |
| `ix_refresh_sessions_family` | Revokes and validates an entire refresh-token family. |
| `ix_refresh_sessions_user` | Supports account session inventory and revocation workflows. |
| `ix_reports_queue` | Narrows open reports and supports chronological queue operations. |
| `ix_saves_listing` | Supports listing-level save counts and cleanup in reverse of the primary key. |
| `ix_viewings_conversation` | Lists a conversation's structured proposals using a unique cursor. |
| `ix_viewings_reminder` (partial) | Claims accepted upcoming viewings that have not been reminded. |

The initial conversation/report screens use bounded UUID keysets; changing them to last-message/time order requires matching composite cursor predicates and query-plan checks. Indexes are not a substitute for representative `EXPLAIN (ANALYZE, BUFFERS)` measurements.

Every `pk_*` index provides entity lookup and uniqueness; the `saves` composite primary key also prevents duplicate saves. Unique indexes on phone/email, dealer user ID, listing seller/idempotency key, conversation listing/buyer, message conversation/sender/key, media listing/object key, event user/client-event ID, refresh hash, import/report/action idempotency key, notification event ID, block user pair, viewing conversation/key and dead-letter outbox ID enforce the corresponding business invariant and safe retry scope. Nullable email uniqueness permits multiple accounts without email.

## Partitioning and retention plan

Keep messages and events unpartitioned at launch so global idempotency and primary-key guarantees remain simple. Product events are append-only through the API; no update endpoint exists. Retention, lawful erasure and operational cleanup need privileged, audited background procedures before public launch.

At measured event growth, create monthly range partitions on `created_at` with a maintained default/future partition, detach expired months, and write aggregates before raw expiry. PostgreSQL requires a partitioned table's unique constraints to include the partition key: retain a separate compact ingestion-deduplication table keyed by `(user_id, client_event_id)` with a bounded replay window, and make partitioned event PKs `(created_at,id)` rather than pretending a global `id` unique index still exists.

For chat, first tune history indexes and archive old conversations. If time partitioning is justified later, use `(conversation_id, created_at, id)` cursors and a separate message-id/idempotency directory to preserve REST lookups, viewing references and deduplication across monthly partitions; migrate foreign-key references to the directory before moving data. Do not simply partition the current table while retaining its existing global keys. An alternative is conversation-hash partitioning when history locality matters more than time-based deletion.

Daily encrypted snapshots, EU PITR and tested restores are production operations described in [the scaling plan](07-scaling-costs.md); local Docker volumes provide persistence only.

## Marketplace extension

Migration 0006 adds listings.attributes JSONB, feed_candidates.category, a region/category/recency index and nullable make/year in the feed projection. Car facts stay in car_details; generic listings never create placeholder car records. The original schema.sql remains the initial release snapshot; Alembic migrations are the current schema authority. See [marketplace categories](marketplace.md).
