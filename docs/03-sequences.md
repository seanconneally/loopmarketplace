# 3. Core sequence diagrams

These diagrams describe the implemented local module/control flow, with explicitly labelled production extensions. Notifications persist in-app records only; real SMS, push/email, managed transcoding, sampled-frame moderation and signed storage/provider callbacks are release gates. Source inspection does not substitute for the separate runtime verification report. The user has overridden the original review pauses.

## Upload and publication

The HTTP contract splits draft creation from upload allocation so a seller can correct details or retry a failed upload without creating another listing. Both mutations require ownership checks and stable idempotency semantics; the video itself never passes through FastAPI.

```mermaid
sequenceDiagram
    actor Seller
    participant Web as React client
    participant API as Listings / Media services
    participant DB as PostgreSQL + outbox
    participant Store as Private object storage
    participant Relay as Outbox relay
    participant Queue as Redis / Celery
    participant Worker as Media worker
    participant Video as VideoProvider
    participant Mod as Moderation service
    participant Gateway as WebSocket gateway

    Seller->>Web: Confirm rights, details and adult eligibility
    Web->>API: POST /listings + Idempotency-Key
    API->>API: Verify phone, account, rights and category schema
    API->>DB: Persist draft + request identity
    DB-->>Web: listing_id, draft state
    Web->>API: POST /media/listings/{id}/upload
    API->>API: Check ownership, declared size and media type
    API->>Store: Allocate scoped multipart upload
    API->>DB: Persist asset/upload identity
    API-->>Web: asset_id, upload_id, part_size, part_urls
    loop Each bounded part
        Web->>Store: PUT bytes using presigned part URL
        Store-->>Web: Part ETag
    end
    Web->>API: POST /media/{asset}/complete with part ETags
    API->>Store: Complete/verify multipart identity and object size
    API->>DB: Mark processing + durable media job, commit
    API-->>Web: Processing status; poll URL
    Relay->>DB: Claim committed work with expiring lease
    Relay->>Queue: Enqueue stable outbox/job ID
    Queue->>Worker: Deliver job, possibly more than once
    Worker->>DB: Claim/check idempotent processing state
    Worker->>Video: Local ffprobe/ffmpeg, HLS/posters/thumbnails
    Video->>Store: Read source; write derivatives to private processed prefix
    Video-->>Worker: Duration, asset metadata, hashes, results
    Worker->>Mod: Local text/contact checks + matching poster dHash
    alt Requires human review
        Mod-->>Worker: pending_review with evidence references
    else Eligible and approved
        Mod-->>Worker: approved
    end
    opt Local checks pass or admin approves review
        Worker->>Video: Publish approved derivatives
        Video->>Store: Copy private processed objects to playback bucket
    end
    Worker->>API: Apply guarded media/publication transition
    API->>DB: Asset + listing + feed projection + status event, commit
    Relay->>Gateway: Publish listing.status via Redis
    Gateway-->>Web: listing.status {listing_id, status}
    Web->>API: Poll asset/owner status if event missed
    API-->>Web: Authoritative current state
```

Presigned part URLs expire after fifteen minutes and are scoped to a server-selected object key/part number. Parts are 8 MiB, with a 500 MiB source cap; MIME is limited to MP4/MOV declarations and completion verifies contiguous ordered ETags, part count, upload generation and exact total bytes. ffprobe checks the container/video stream and 15–60-second duration (with a 0.1-second local upper-bound tolerance); ffmpeg generates 360×640 and 720×1280 HLS with optional AAC audio, poster and thumbnail sheet. Silent input remains valid. Full production codec/sandbox and sampled-frame policy remain release work.

On refresh or interruption, the client recovers the draft ID (or replays its exact creation body/key), reselects and hashes the original video, then calls `POST /media/{asset}/resume`. The server checks ownership and the full-file SHA-256/size, lists actual storage parts, and returns completed ETags plus renewed URLs. The client skips saved parts and finalizes on the same advert. Lost successful PUT/completion responses are reconciled against storage. Failed processing can be retried from the retained original with an idempotent seller request, up to three times; explicit replacement allocates a new generation on the same asset/advert. See the [seller/upload guide](seller-uploads.md).

Processed objects stay in the private sources bucket until checks permit publication; pending review cannot directly fetch quarantine media through the playback origin. The local text/hash pass is not a comprehensive prohibited-content scan. SeaweedFS 4.48 provides the local S3 API; the development storage credentials/configuration are not a production security configuration.

The local path uses authenticated client finalization. A future provider/storage callback must be signed and replay-protected and converge on the same reconciliation transition; no such webhook is implemented here. Multipart completion is an external side effect: robust reconciliation after a timeout or database rollback remains a release gate because completing an object and committing PostgreSQL cannot be one atomic transaction.

On transient processing failure, retry with exponential backoff/jitter and capped attempts. Durable job state and leases allow recovery after queue loss; exhausted attempts become dead-letter records with a replay path. Guarded state/version checks stop an old successful callback from resurrecting an asset superseded by a replacement upload, a sold listing or a moderation removal. Human review time is excluded from the two-minute processing objective and measured separately.

## Sending a message

```mermaid
sequenceDiagram
    actor Buyer
    participant Web as Sender client
    participant API as Messaging service
    participant Policy as Users / Listings / Moderation services
    participant DB as PostgreSQL + outbox
    participant Relay as Relay / notification worker
    participant Redis as Redis pub/sub
    participant Gateway as Recipient API replica
    participant Recipient as Seller client
    participant Notify as Local notification records

    Buyer->>Web: Send message
    Web->>API: POST conversation messages + Idempotency-Key
    API->>Policy: Verify account, membership and current block rules
    Policy-->>API: Allowed
    API->>API: Validate body; annotate scam-pattern warnings
    API->>DB: Insert message + conversation update + outbox, commit
    Note over API,DB: Unique sender/key and request fingerprint prevent duplicate sends
    API-->>Web: Persisted MessageView
    Relay->>DB: Claim committed message event
    Relay->>Redis: Publish event to user-scoped channel
    Redis->>Gateway: message.created
    Gateway->>Recipient: Authorized WebSocket event
    Relay->>Notify: Idempotently store notification.requested event
    Note over Notify,Recipient: Real offline push/email adapters are planned
    Recipient->>API: GET message history after reconnect/cursor
    API->>Policy: Recheck membership and block policy
    API->>DB: Read durable keyset page
    API-->>Recipient: Messages, warnings and next_cursor
    Recipient->>API: PUT read position with message_id
    API->>DB: Advance monotonic receipt + outbox, commit
    Relay->>Redis: message.read event with reader_id
```

One conversation exists per `(listing_id, buyer_id)`, enforced in the database; the seller is derived from the listing and clients cannot choose an arbitrary recipient. A lost HTTP response can be retried with the same key/body and must return the same persisted message; reusing a key for different content returns a conflict. A failed fan-out never rolls back an already committed message.

Redis pub/sub has at-most-once delivery semantics, so reconnect/history fetch is required; see the [official Redis documentation](https://redis.io/docs/latest/develop/pubsub/). Clients deduplicate incoming events by persisted entity ID, merge REST responses and WebSocket events, and display durable send status rather than assuming socket delivery proves persistence. Push/email adapters are development-only until production providers, subscriptions and residency are verified.

## Proposing and responding to a viewing

```mermaid
sequenceDiagram
    actor Proposer
    participant Web as Chat UI
    participant Viewings as Viewing service
    participant Messaging as Messaging membership service
    participant DB as PostgreSQL + outbox
    participant Relay as Relay / scheduler
    participant Notify as In-app notification records
    participant Other as Other participant

    Proposer->>Web: Choose future time and public meeting place
    Web->>Web: Show first-viewing safety guidance
    Web->>Viewings: POST /viewings + Idempotency-Key
    Viewings->>Messaging: Check active conversation membership and block policy
    Messaging-->>Viewings: Participants
    Viewings->>DB: Proposed viewing + structured event, commit
    Viewings-->>Web: ViewingView with revision
    Relay-->>Other: viewing.updated through authorized WebSocket
    Other->>Viewings: POST respond {action, revision}
    Viewings->>Messaging: Revalidate membership/current policy
    Viewings->>DB: Lock/check revision and allowed actor transition
    alt Accept
        Viewings->>DB: Mark accepted + durable reminders + event
    else Decline or cancel
        Viewings->>DB: Mark terminal state + cancel pending reminders + event
    else Counter
        Viewings->>DB: Preserve prior proposal; create revised proposal + event
    end
    Viewings->>DB: Commit transition
    Viewings-->>Other: Current ViewingView
    Relay-->>Web: viewing.updated
    opt Accepted viewing
        Relay->>Notify: Store due reminders for both participants
        Note over Notify,Other: Outbound delivery is planned
        Web->>Viewings: GET /viewings/{id}/calendar
        Viewings->>Messaging: Verify participant access
        Viewings-->>Web: Escaped .ics with stable UID
    end
```

Only the other party may accept/decline the current proposal; cancellation/counter rules are explicit in the service state machine. Clients send the revision they saw; competing or stale responses return `409` instead of silently overwriting each other. Preserve original proposal history and counter authorship so the next acceptance applies to the intended time/place.

Use timezone-aware timestamps and UTC storage, render in the launch region's timezone, require a future time, and escape/fold calendar text safely. The local scheduler selects accepted, not-yet-reminded viewings within an hour and enqueues in-app records; there is no real push/email send. Before enabling outbound delivery, recheck the accepted revision at delivery time so cancellation can suppress already queued reminders. Precise meeting details stay within the conversation and must be excluded from logs and future push previews.
