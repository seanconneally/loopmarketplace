# 6. Feed candidates, ranking and caching

The MVP ranker is deterministic, explainable and replaceable through `FeedRanker.score`. It optimizes useful local stock first; it does not attempt a learned recommendation model or claim that a popularity score proves seller trust.

Source reconciliation: the local scaffold implements candidate projection, the heuristic, short-lived snapshots, current visibility checks and cache/ranker fallback. It does not implement a trained model or full engagement aggregation. Production startup is guarded; runtime outcomes belong to the separate verification report. The user's instruction to finish the entire delivery supersedes the source prompt's review pauses.

## Candidate eligibility

Filter on configured region, coarse geographic point/radius, integer price range, optional make and year range before ranking. Use `geography(Point, 4326)` and indexed `ST_DWithin` with radius converted from kilometres to metres; PostGIS documents metre units for geography and an index-aware bounding-box comparison in this function. See [ST_DWithin documentation](https://postgis.net/docs/ST_DWithin.html).

The feed module owns `feed_candidates`, including seller ID, location, public listing/media projection, common filter columns and engagement aggregate. Its repository queries only that projection. Listing/media/user/moderation facts arrive through their public services/events, rather than feed code joining those modules' tables.

The scaffold updates/removes the projection synchronously through public module interfaces inside the owning write transaction, then emits durable invalidation events. This is a deliberate simplification from the architecture's event-fed production projection: it gives consistent local publication/removal while preserving table ownership. Event-driven rebuild/reconciliation and independent consumer checkpoints can replace synchronous projection when operational demand justifies it.

Before returning each page, authoritative services recheck live listing eligibility, seller account status and bilateral blocking, and decorate saved state for the current member. A stale candidate cache or snapshot must never make removed/sold/blocked content visible again. Batch those checks at scale to avoid page-size-proportional query amplification; ten-item pages make the initial implementation bounded, not automatically fast enough for the p95 target.

## Exact MVP score

```text
age_hours = max(0, (now - published_at) / one_hour)
score = -log1p(age_hours)
        + min(1.0, log1p(max(0, engagement)) / 10)
        - (1.5 if already_seen else 0)
```

Sort by `(score DESC, listing_id DESC)` for deterministic ties. Age uses one captured `now` per snapshot; IDs break ties without implying extra quality. The engagement bonus is capped at 1, and seen status subtracts 1.5, so untrusted engagement cannot create an unlimited ranking advantage.

For intuition, with no engagement or seen penalty, a one-hour-old listing scores about −0.69 and a 24-hour-old one about −3.22. Applying the maximum bonus adds one; an impression/seen penalty subtracts 1.5. Recency therefore remains substantial and an older highly active advert cannot remain dominant forever.

The ranker accepts an aggregate, not raw per-user events. Its local projection `engagement` defaults to zero and no production-quality aggregation updates it yet, so current ordering is recency plus consented seen penalties. A proposed production aggregate blends eligible watch-through rate, distinct verified-user saves and distinct legitimate buyer conversations, with minimum samples, age windows, fraud exclusions and per-user/listing deduplication. Saving a listing or ingesting a watch event does not currently imply that its engagement bonus changes.

Seen penalties rely on consented viewing data. Ingestion rejects members without current consent; workers recheck consent before adding impression IDs to a seven-day set. Withdrawal emits a durable cache-clear event and the feed immediately stops reading seen history for that member. Full erasure/retention and consent audit history remain production gates. Saving/messaging reuse for ranking still needs a documented privacy basis and retention policy.

## Cursor pagination

Ranked pagination freezes at most 150 eligible candidate IDs, ordered once, in a five-minute Redis snapshot. An HMAC-signed opaque cursor carries snapshot reference, consumed position, normalized filter fingerprint and identity; changing filters or account returns a mismatch and starts a new session. Pages contain up to ten visible listings; consume hidden IDs too so removed/blocked candidates cannot trap the cursor.

The cursor position indexes a frozen in-memory ID set; it is **not SQL offset pagination**. New adverts and changing engagement enter a fresh session, not the middle of a frozen ranking. Expired snapshots return `410 cursor_expired`, and the UI offers a clear refresh action. The 150-item cap is a deliberate bounded MVP browsing window; a subsequent refresh starts a new candidate window rather than claiming to page an unlimited global corpus.

For cache/ranking degradation on a new request, PostgreSQL recency uses signed keyset state `(published_at, listing_id)` with a strict less-than predicate and returns `ranking: "recency-fallback"`. Redis loss while continuing an existing ranked snapshot returns `410 cursor_expired` with an explicit refresh instruction, rather than appending a differently ordered page that could repeat items. Existing recency cursors continue their database ordering without requiring Redis. Seamless continuation across arbitrary ranking modes would require a separate consumed-ID/session policy and is not promised.

The scaffold catches exceptions from scoring/sorting and Redis failures on a new request and uses recency fallback. Database/authorization failures are not converted into a supposedly successful empty feed; safe eligibility remains necessary. Failure-path runtime validation must be read from the verification report rather than inferred from these branches.

## Redis keys and invalidation

| Key family | Contents / TTL | Invalidation and correctness rule |
| --- | --- | --- |
| `feed:candidates:{region}:{cell}:{revision}:{filters}` | Candidate IDs, 30 seconds | Region revision bump on publication, sale, removal or eligible-field change makes old keys unreachable; TTL removes them |
| `feed:revision:{region}` | Current generation integer | Increment through committed outbox invalidation; missing key defaults to zero; keep monotonic generation in a rebuild/recovery strategy before relying on it across Redis resets |
| `feed:snapshot:{random_id}` | Frozen ordered candidate IDs, 300 seconds | Never rewrite ranking in place; eligibility checks hide removed content; expired cursor forces restart |
| `feed:seen:{user_id}` | Impression listing IDs, seven-day expiry refreshed on additions | Ingestion and workers check current consent; withdrawal clears the key and disables reads; full deletion/retention remains a production gate |
| `rate:{scope}` | Atomic counters with fixed expiry | Expire per rule; sensitive mutations fail closed if a safe decision cannot be made |
| `ws-ticket:{digest}` | User/session ticket, 30 seconds | Atomic consume; no retry reuse; revoked sessions rejected again by auth |
| `otp:{phone_digest}` / OTP counters | Challenge hash and short attempt windows | Atomic consume on success, bounded attempts and TTL; no plaintext phone in key |

The cell prefix is the rounded geographic origin; the **current scaffold also includes the exact normalized filter/centre fingerprint**. This prevents sharing an exact-radius result with another centre and accidentally admitting outside-radius stock, but reduces cache reuse. A later shared-cell candidate cache must query a conservative superset for the whole cell plus search radius, then reapply each user's exact radius and filters before ranking.

Save/message/watch aggregate updates invalidate ranking inputs for **new** sessions; existing snapshots stay stable. Seller suspension/block changes require current service checks immediately even before cache invalidation. Public listing details require equivalent current visibility checks; CDN removal/purge is a separate safety responsibility for already delivered media.

Database fallback, candidate-cache refill and outbox relay must have bounded timeouts/concurrency to avoid a cache-outage thundering herd. Short random TTL jitter, request coalescing and a circuit breaker are planned production optimizations; no cache key is allowed to become authoritative for ownership, verification or moderation.

## Client playback and analytics

Virtualise the feed, mount only a small neighbourhood, and play only the active visible video. Preload the next two at the lowest rendition with a bounded buffer, cancel downloads when scroll direction changes and destroy off-screen hls.js instances. Respect reduced motion, data-saving preferences, browser autoplay policies and manual pause; test Safari native HLS and browsers using hls.js separately.

Batch supported impression/watch events with stable client event IDs, valid listing IDs and capped values. Store raw consented events append-only and aggregate asynchronously; do not increment arbitrary engagement directly from untrusted client values. Cap watch duration to plausible asset duration/session time, deduplicate retries and exclude the seller's own/bot/flagged traffic from eligible ranking input.

## Path to a learned model

1. Measure real feed quality first: successful conversations/viewings, report rate, stock freshness and cost per useful session; raw watch time alone can reward misleading videos.
2. Establish consented training labels, deduplication, holdout periods and a feature registry with owner, purpose and retention; use minimum aggregation thresholds and avoid hidden sensitive proxies.
3. Train/evaluate offline against recency and heuristic baselines, including geography/dealer concentration, new sellers, scam exposure and cold-start behaviour.
4. Implement a second `FeedRanker` adapter with a strict response budget and the same candidate/eligibility boundaries; version ranker and features in telemetry.
5. Run a limited controlled experiment with safety metrics, capacity/spend limits and an immediate heuristic/recency rollback. Expand only if useful outcomes improve without increased fraud or unfair concentration.

The learned ranker changes ordering, not eligibility, contact privacy, block enforcement or the source of truth. Keep ranking computation out of the transaction that publishes a listing, and do not split it into a new service merely to satisfy a model-serving pattern before load requires it.
