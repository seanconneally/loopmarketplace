# 6. Feed candidates, ranking and caching

The current Loop Marketplace feed mixes all eligible listings by default. Cars, Homes and Golf clubs narrow candidate selection; Something else has no separate browse filter. See [category design](marketplace.md) and [personal loop](personal-loop.md) for the current product and signal rules. This replaces the original car-only frozen interest-v1 session design.

## Eligibility and projections

The feed owns feed_candidates: listing/seller ID, category, location, price, nullable car make/year and public JSON projection. It queries this projection rather than joining other modules' tables. Listing publication/edit/removal synchronously projects through a public service in the caller's transaction, with durable outbox invalidation afterward.

Apply region, exact geographic origin/radius, price, optional category/search and any requested car facts before ranking. Default year bounds do not filter rows with no car. PostgreSQL/PostGIS indexes support geography, recency and category. Keyword matching is a bounded pilot search over title, description, category, area and public facts; large catalogues will need a dedicated indexed text-search design.

Before delivering every page, batched service calls recheck live listing IDs, active seller accounts, bilateral blocking, saved flags and explicit dismissals. Cache content never overrides current eligibility.

## Ranking

The replaceable FeedRanker baseline is:

```text
-log1p(age_hours) + min(1, log1p(max(0, engagement))/10) - (1.5 if seen else 0)
```

interest-v2 combines 0.35 times the unseen baseline with bounded content affinities, per-category price similarity and a seen penalty. Category preferences learn across the mixed feed; specific facts learn within categories. A category's price preference never transfers to another category. Every fifth slot uses the baseline for exploration. Seller/brand diversity and breaks in long category runs are relaxed when alternatives run out.

Only members currently consenting to analytics get a learned profile. Fetch at most 200 recent events after the member's reset cutoff and within 30 days, using the user/time index, then fetch public facts in one batch. Own inventory is excluded. The current weights are tunable hypotheses; ranking does not prove trust, intent or seller quality. Private chat text is not a feature.

## Adaptive pagination and failure handling

Select at most 150 candidates. A Redis session stores the pool order, committed page IDs and frontier. Four-item personalized windows learn again from current history before each unseen page; other sessions return up to ten. The prefix already consumed is never re-ranked. An atomic compare-and-swap publishes a page once so concurrent retries converge. Current eligibility can remove a delivered item on retry; it cannot refill a committed page with unseen IDs and create later duplicates.

Signed cursor fields include version, snapshot reference, consumed position, exact filter fingerprint, account and preference version. Account/filter changes reject a mismatched cursor; consent/reset or expiry require a refresh. New page commits renew a 30-minute snapshot lifetime. The pool is finite; refresh starts a new candidate window rather than pretending to page the entire corpus.

Explicit newest and price sorts use strict SQL keysets. A new ranked request falls back to SQL recency on Redis failure. Redis loss during a ranked continuation returns 410, preserving page-order integrity rather than silently appending another ordering. Database/authorization failures remain errors. Ranker exception circuit-breaking and global model serving are not implemented.

## Cache keys

| Family | Contents and lifetime |
| --- | --- |
| feed:candidates:{region}:{cell}:{revision}:{filters} | Shared candidate IDs; 30 seconds. Exact origin/filter fingerprint prevents geographic cache leakage. |
| feed:revision:{region} | Outbox-incremented generation for candidate invalidation. |
| feed:snapshot:{random_id} | Bounded ID pool, committed pages, frontier; 30 minutes after page commit. |
| feed:seen:{user_id} | Impression IDs; seven-day TTL renewed on additions, consent-gated read/write and cleared on withdrawal/reset. Membership checks are bounded to candidate IDs. |

Publication, sale, removal and eligible-field edits invalidate future candidate lookups. Current eligibility checks protect existing sessions immediately. Production needs replay/reconciliation after Redis loss, media purge, request coalescing and bounded fallback concurrency; these are not implied by the local cache.

## Measurement and scale

Measure useful conversations/viewings, hides/reports, seller exposure, category coverage, fresh-stock discovery, abandonment and cost per useful session. Compare against recency with consented holdouts before training models. Real inventory, traffic and device-network measurements are still required. The current implementation does not claim production throughput or TikTok-scale learning. A future model can replace ordering while preserving the same eligibility, privacy, bounded-request and cursor contracts.
