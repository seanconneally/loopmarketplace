# 7. Scaling, reliability and monthly costs

Planning baseline: 1,000 MAU and 50 videos/day at launch; 10× means 10,000 MAU and 500 videos/day; 100× means the design target of 100,000 MAU and 5,000 videos/day. These are explicit workload assumptions, not a prediction that seller supply and buyer demand grow together.

This is a production planning model, not measured capacity or an incurred bill. The delivered application is a local scaffold with production startup deliberately disabled pending release gates; local S3 storage is SeaweedFS 4.48, while the estimates below compare proposed managed EU services. Runtime checks and resource usage are reported separately. The original review pauses were superseded by the user's instruction to complete all deliverables.

## Performance model and targets

Assume 20% daily activity, 150 minutes of viewing per MAU per month, 30-second average uploads, 1.5 Mbps mean delivered bitrate, 20% extra bytes for preload/retries, 15% of active users messaging, and a peak-to-average factor of 10. MAU is not concurrency: measure concurrent playback, API requests, open sockets, uploads, queue age and database I/O independently before sizing.

| Objective | Measurement and acceptance |
| --- | --- |
| Feed/listing API p95 <200 ms | Measured at ingress, excluding video delivery, at declared filter mix and peak concurrency; include cold-cache results separately |
| First video frame <1.5 seconds | Real-device 4G test, poster-to-first-frame timings, cold CDN and warm CDN cohorts; low initial rendition and short segments |
| Message delivery <1 second | Persisted REST send to recipient receipt on healthy connected clients; separately track offline notification latency |
| Upload-to-live <2 minutes | Storage completion to publish for valid, auto-approved samples; report p50/p95 by duration/codec, excluding human-review time |
| Availability 99.9% | Monthly critical browse/contact requests; roughly 43 minutes of a 30-day month is the error budget |

Do not claim the targets from a successful local smoke test. A repeatable load test must include sold/removal invalidation, geographic density, reconnect storms, slow external providers, Redis outages and burst dealer imports.

## What breaks first

| Load | Likely first limits | Fix before increasing capacity |
| --- | --- | --- |
| Launch, 1× | One worker tied up by a large upload; empty inventory; manual moderation; SMS abuse | Separate media/notification queues, per-task deadlines, dealer import quotas, operational review coverage and new-account limits |
| 10× launch | Encoding queue age, excessive HLS preload, too many DB connections, dense-city candidate sets | Managed transcoding or more media workers, cancel off-screen downloads, tune PgBouncer budgets, PostGIS projection/index checks, cell candidate caches and bounded candidates |
| 100× launch | CDN bill, event-table growth, hot chat/history indexes, Redis cache/broker contention, pub/sub reconnect fan-out | Bitrate/watch-time budgets, event partition retention and aggregate jobs, keyset queries, separate broker/cache Redis, bounded socket buffers and reconnect jitter; add read replica only for lag-tolerant reads |
| Beyond design target | Media security/isolation and independent capacity; hot database domains | Extract media processing first using its existing provider/events boundary; consider event offload and chat partitioning only after measured query/load evidence |

The first constraint is workload-dependent. Alert thresholds and queue ages should determine action; 100,000 MAU alone does not require microservices, database sharding or a learned ranker.

## Capacity and reliability rules

The API, WebSocket gateway and workers are stateless. Keep at least two API replicas and redundant ingress for a real availability objective; scale media and notifications independently. PgBouncer allocates a fixed total server-connection budget across processes; a worker replica must not silently multiply that budget. Run schema migrations once as a release job, never concurrently in every API startup in production.

Use a managed PostgreSQL primary with automated failover when the availability requirement justifies its cost. A read replica can serve analytics, rebuilds and sufficiently stale feed candidates; current account status, conversation authorization, block decisions and read-after-write checks stay on the primary. No cross-module replica joins are permitted merely because the storage is shared.

Redis failure must preserve durable mutations: feed falls back to recency, clients recover messages from PostgreSQL, and outbox reconciliation re-enqueues missing work. If an abuse-control decision cannot be obtained safely, publishing/messaging/OTP operations return a temporary error. Redis pub/sub is notification transport, never message storage. Separate non-evicting broker state from an evictable candidate cache in production; prefixes are useful organization but do not isolate memory pressure.

Use outbox leases, deterministic job IDs and application-level idempotency. The scaffold has durable outbox retries capped at five dispatch attempts, six-minute leases, a 300-second task ceiling, Redis visibility timeout of 600 seconds and separate `media`/`default` routing; the local worker consumes both. Backoff/jitter, isolated production worker pools and durable dead letters limit retry storms. Any production replay workflow needs a reviewed reason and retained attempt history.

| Dependency or process | Health/readiness signal |
| --- | --- |
| API | Process liveness; database readiness; report cache degradation independently rather than removing every browse replica |
| Worker | Worker heartbeat, queue-specific task progress and oldest runnable job; a running process alone is insufficient |
| Relay/scheduler | Recent successful claim/dispatch cycle, no expired leases accumulating |
| PostgreSQL/PgBouncer | Connection/query probe, primary role, pool saturation and wait time |
| Redis | Ping plus memory/eviction/persistence/broker age checks |
| Nginx | Local health route, upstream error rate, connection and upgrade failures |
| Storage/transcoder | Bounded synthetic upload/playback check and authenticated completion-event lag |

## Dashboards and alerts

| Area | Dashboard | Initial actionable alert |
| --- | --- | --- |
| API | p50/p95/p99 by route, error ratio, DB time, pool waits | Critical route error-budget burn; sustained p95 >200 ms at representative load |
| Video | Upload completion age, phase durations, failures by codec/provider, pending-review age | Oldest runnable video >2 minutes or repeated processing failures; review backlog over staffed SLA |
| Jobs | Queue depth/oldest age, attempts, lease expiry, dead letters | Notification queue age >30 seconds; any growing dead-letter backlog |
| Chat | Active sockets, fan-out latency, dropped buffers, reconnects | Connected delivery p95 >1 second; reconnect or authorization-failure surge |
| Data | CPU/I/O, locks, replication lag, PostGIS plans, partition sizes | Primary connection budget nearly exhausted or replica lag beyond query tolerance |
| Spend | Delivered GB, average bitrate, preload ratio, uploads, provider costs | Daily run rate exceeds budget by 20%; investigate data increase before scaling automatically |

Thresholds are starting values to tune against pilot traffic. Page only for user impact, lost progress, safety work or imminent resource exhaustion; aggregate low-priority anomalies into a daily review.

## Backups and recovery

Enable daily encrypted snapshots and continuous PostgreSQL point-in-time recovery in the EU. Proposed objectives are RPO ≤15 minutes and RTO ≤4 hours, measured through a monthly restore into an isolated account/network. Validate login/session behaviour, listing/media references, message ordering, outbox replay and deletion tombstones after restoring; do not notify real users from the restore environment. Keep backup copies and encryption-key recovery instructions separate from the primary failure domain. Retain a deletion ledger and reapply it after restore before reopening access.

Storage lifecycle policies abort incomplete multipart uploads, delete rejected/source objects on schedule and remove versions when legally required; versioning is not a substitute for erasure. Test CDN removal and provider cleanup, not only database recovery. A restore drill is an operational task the owner must schedule; it is not established by writing this document.

## Cost model

Prices below are a planning model in **USD/month, excluding VAT, labour, legal work, moderation staffing and paid acquisition**, reviewed on 2 November 2026. No resources have been provisioned. Product prices are region/configuration dependent; rounded unit allowances are deliberately distinguished from verified public rate examples. Convert to EUR using the billing-period exchange rate rather than embedding an unstable conversion.

### Video delivery arithmetic

```text
GB per MAU = 150 minutes × 60 seconds × 1.5 megabits/second ÷ 8 ÷ 1,000 × 1.20
           = 2.025 GB/month
Launch     = 1,000 × 2.025 = 2,025 GB ≈ 2.025 TB/month
Design     = 100,000 × 2.025 = 202,500 GB ≈ 202.5 TB/month
```

For a transparent comparator, CloudFront's published Europe pay-as-you-go table currently gives the first 1 TB free, next 9 TB at $0.085/GB, next 40 TB at $0.080, next 100 TB at $0.060 and next 350 TB at $0.040; request charges are separate. Using rounded decimal tier sizes gives launch `(2,025 − 1,000) × .085 ≈ $87` and design `9,000 × .085 + 40,000 × .080 + 100,000 × .060 + 52,500 × .040 ≈ $12,065`. AWS billing units/discounts and account-wide free-tier consumption will change the exact invoice. See [official CloudFront pricing](https://aws.amazon.com/cloudfront/pricing/pay-as-you-go/).

This is a **cost comparator**, not approval to use unrestricted global edges: the EU-only hosting/data requirement requires a compatible provider and contract, including edge caches, support access and logs. Obtain a quote for the selected EU delivery policy. Reducing bitrate by one-third roughly reduces bandwidth volume by one-third; tiered billing means the final dollar reduction is not exactly proportional.

At two-second segment duration, 150 minutes implies about 4,500 segment requests per MAU, or 4.5 million at launch and 450 million at design load before manifests, posters and retries. Budget roughly 20% more requests and $500–$800/month at design load for CDN requests/invalidations/logging, then replace the allowance with actual measured request counts and the selected provider's tariff.

### Storage arithmetic

Assume an average source of 80 MB kept seven days after successful processing, and all renditions/posters totalling 15 MB per listing kept for an average 90 days. These are proposed lifecycle settings, subject to the safety/legal retention review; sources needed for active investigation are explicitly held and access-controlled.

```text
Launch sources      = 50/day × 7 days × .080 GB = 28 GB
Launch derivatives  = 50/day × 90 days × .015 GB = 67.5 GB
Launch steady state = 95.5 GB
Design sources      = 5,000/day × 7 × .080 GB = 2,800 GB
Design derivatives  = 5,000/day × 90 × .015 GB = 6,750 GB
Design steady state = 9,550 GB
```

Use a **$0.023–$0.030/GB-month planning allowance** pending an EU-region quote: approximately $2–$3/month at launch and $220–$287 at design load for primary objects. The first month is lower while the retained inventory fills. Requests, object versions, evidence holds, replication and backups are extra. S3 bills these components separately; see [official S3 pricing](https://aws.amazon.com/s3/pricing/).

Keeping every original for a year instead of seven days would add `5,000 × 358 × .080 = 143,200 GB` at design load, roughly $3,300–$4,300/month before replication. Retention is therefore both a privacy decision and a meaningful cost input.

### Transcoding arithmetic

At 30 fps, one SD plus two HD AVC outputs give an illustrative normalization total of `1 + 2 + 2 = 5`; a 30-second source therefore yields `0.5 × 5 = 2.5` normalized output minutes. Launch produces `50 × 30 × 2.5 = 3,750` normalized minutes/month; design produces `5,000 × 30 × 2.5 = 375,000`. MediaConvert bills normalized output minutes with codec/resolution/quality multipliers and region-specific rates; portrait resolution uses the horizontal dimension. See [official MediaConvert pricing and normalization examples](https://aws.amazon.com/mediaconvert/pricing/).

Budget **$0.008–$0.020 per normalized minute** until the exact Ireland ladder and volume tariff are quoted: about $30–$75/month at launch and $3,000–$7,500 at design load. This is an allowance, not a quoted Ireland rate. ffmpeg can lower direct encoding fees but adds worker capacity, patching, isolation and on-call work; compare total operating cost after measuring representative clips.

### Monthly total allowance

| Component | Launch, 1k MAU / 50 videos daily | Design, 100k MAU / 5k videos daily |
| --- | ---: | ---: |
| Video CDN transfer | ~$87 | ~$12,065 |
| CDN requests, invalidation and delivery logs | $0–$20 | $500–$800 |
| Primary video object storage | $2–$3 | $220–$287 |
| Object requests, copies, evidence/backup allowance | $10–$40 | $100–$400 |
| Managed transcoding allowance | $30–$75 | $3,000–$7,500 |
| API/relay/notification containers and ingress | $80–$200 | $300–$900 |
| Managed Postgres/PostGIS, backup/PITR allowance | $100–$250 | $400–$1,200 |
| Redis/broker/cache allowance | $30–$100 | $150–$500 |
| Observability and networking allowance | $30–$100 | $150–$500 |
| SMS, push/email and automated-scan allowance | $30–$150 | $500–$2,000 |
| **Indicative total** | **$400–$1,025** | **$17,400–$26,200** |

Container/database/Redis/provider rows are budget allowances, not verified instance quotations. Highly available multi-AZ managed deployments, NAT gateways, support plans, unusually frequent OTP sends or expensive frame moderation can exceed them. Use a region-specific calculator with the actual architecture before purchasing; cheap single-node deployments do not substantiate the 99.9% target.

Video egress dominates this viewing-heavy **design-load** scenario. At launch, fixed infrastructure can dominate; with many dealer uploads and little viewing, transcoding can dominate instead. At 30 rather than 150 viewing minutes per MAU, bandwidth volume falls to one-fifth while ingestion costs remain unchanged. Set upload quotas, usage alerts, bitrate ceilings and an emergency throttle so growth cannot create an unchecked bill.
