# Personal loop and video uploads

The current interest-v2 recommender is an explainable rules-based implementation for Loop Marketplace. It is not TikTok's proprietary algorithm or a trained model. Real pilot data is needed before claiming improvements in relevance or conversion.

## While scrolling

The mixed For you feed includes every eligible category. Opted-in members get four clips per page; anonymous and opted-out sessions get ten. Before requesting the next page, the client samples active playback and flushes fresh receipts with a short timeout. The server re-ranks only the unseen remainder using the newest committed history. Loaded pages stay stable; changing interests does not rearrange the clips already delivered.

Profiles use at most 200 events from 30 days, after the last reset. Completion below 12% is a weak negative; above 30% grows into a positive. Replays add capped positive weight. Saves and new seller conversations are stronger, server-owned actions. Not interested hides the advert for that member even with tracking off; Undo restores it and retracts the negative signal.

Signals combine a seven-day decay with a 30-minute session boost. The strongest receipt per advert/event type/day contributes, and the total per advert/day is capped between −5 and 6. Repeated playback receipts cannot grow preference strength without bound. Own listings are excluded from profile learning.

Affinities cover category, car make/fuel/gearbox and applicable item facts such as brand, club type or property type. Price preference is calculated separately for each category. Freshness, a seen penalty, seller/brand variety and every-fifth-slot exploration keep the feed from becoming one narrow repeated stream. Diversity relaxes when inventory is sparse. Filters and live eligibility always take precedence over ranking.

## Cursor correctness and bounded cost

A session has at most 150 candidate IDs. Redis stores ordered IDs, committed pages and the next unserved position. A compare-and-swap Lua update commits each page once: simultaneous requests with the same cursor converge on the same IDs and next cursor. Removed or hidden adverts may disappear on retry, but a committed page is never backfilled with another page's items. New page commits renew the snapshot's 30-minute expiry. New inventory enters a fresh session, not the middle of the current pool.

Signed cursors bind account, exact normalized filters, preference version and snapshot. Reset/consent changes invalidate old personalized continuation. Expiry returns an actionable refresh error. A fresh request falls back to SQL recency if Redis is unavailable; an interrupted existing ranked session requires refresh. Explicit newest/price sorting retains SQL keyset pagination. The candidate/history bounds are deliberate pilot limits, not an unlimited global recommendation corpus.

## Playback and privacy controls

Watch time uses actual foreground media advancement, excluding pause and buffering. Replays are capped at two in a receipt. Batches use stable UUIDs for safe retry, a bounded in-memory queue and a 60-second freshness limit. They are not persisted in local storage. Account changes, reset and opt-out clear queued history. Client timestamps are validated; receipts older than the server reset cutoff are ignored. The server rechecks consent and accepts only playback signals from analytics; saves/messages cannot be forged through that endpoint.

Reset ignores older interests without removing saved listings or restoring deliberately hidden adverts. Raw event retention/erasure and production abuse controls remain release work; reset is not a promise that all event rows have been erased.

## Easier uploads

The picker provides an on-device preview, size, general filming tips, early format/size checks and metadata duration validation where supported. The mobile recording control depends on the browser/OS. Unsupported local preview can still submit an allowed original for definitive server validation. Object URLs are released on replacement/unmount.

The seller can leave after original upload completion while background processing continues. My listings provides failures, retry/replace and same-advert multipart resume. Original audio is preserved when present; playback begins muted. No photo feature was added. Actual iPhone/Android hardware acceptance remains pending; browser device profiles are recorded separately.

See [feed implementation details](06-feed-ranking.md), [category design](marketplace.md) and [validation](validation.md).
