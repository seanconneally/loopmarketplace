# 10. Phased roadmap

The supplied brief asks for a production-oriented design and a runnable scaffold, not a claim that a complete publicly operated marketplace can be certified by generating files. Use the implementation inventory and verification report to determine what exists today; the phases below define the work and evidence needed to ship responsibly.

The user explicitly overrode the original checkpoint pauses and requested all deliverables. Current source includes the local core journeys, worker/outbox flow and SeaweedFS-backed media pipeline; production startup remains disabled. SMS/push/email delivery, managed video processing, sampled-frame scanning, privacy export/deletion, public notice/appeal workflows and operational compliance are planned release gates. Nothing in this roadmap claims a runtime check passed; results are recorded separately.

## Phase 0 — runnable foundation and design handoff

Deliver the monorepo and all design documents, one-command local Compose stack, generated OpenAPI/TypeScript contract, seeded vertical-video feed and an end-to-end path through phone verification, a listing, chat and a viewing. Use explicit development adapters where paid services are unnecessary, and record every incomplete or production-only component. Keep routers thin, services testable and repositories private to modules.

**Exit evidence:** documented setup works from a clean checkout; lint/type checks and service tests pass; migrations apply on empty real PostgreSQL/PostGIS; Redis integration works; frontend build succeeds; the upload-to-viewing browser path passes in the stated environment. Record any checks that could not run instead of treating them as passed.

**Main risk:** mistaking a useful local scaffold for an operated production service. Production credentials, legal review, safety staffing, failover and real-device performance remain explicit launch work.

## Phase 1 — MVP pilot in one region, cars only

Finish and harden every in-scope pilot journey: production SMS with rotation/reuse tests; direct multipart upload and managed encoding; approved-media publication; distance/price/make/year filtering; saves; real-time chat with reconnect recovery; read receipts and scam warnings; viewing responses/counters/reminders/calendar; report/block/admin decisions/appeals; verified dealer imports; consented events; export/erasure. Add accessible empty/error/loading states and test mobile browsers and weak networks.

Provision EU production services through reviewed infrastructure configuration, retain no secrets in Git, establish monitored backups/PITR, and run restore and incident exercises. Bring a small group of consenting dealers and buyers into an invitation pilot before broad launch. Review phone abuse, duplicate inventory, viewing safety, report response times and real bandwidth cost daily.

**Exit evidence:** real-provider integration and authorization tests, concurrency/idempotency tests, a successful restore, residency/processor review, legal sign-off, staffed safety coverage, representative 4G tests and a budget with alerts. Demonstrate all agreed SLOs at declared pilot peak, with outage/fallback exercises.

**Main risk:** trustworthy inventory and fraud response. Thin supply or slow handling of fake adverts can invalidate the product even when playback and infrastructure work.

## Phase 2 — v1 quality and repeatable operations

Improve relevance using measured consented engagement signals, seller quality and bounded exposure diversity while keeping recency fallback and transparent controls. Improve dealer CSV validation/recovery, moderation productivity, appeal handling, notification preferences, accessibility and mobile playback quality. Automate retention/deletion reconciliation, cache invalidation audits and provider-cost attribution.

Refine the unit-cost model from actual watch time, bitrate, retained originals and moderation work; test throttles before enabling broad acquisition. Add operational dashboards and concise runbooks that a solo maintainer can use under pressure. Plan reviewer/on-call backup as use grows; software cannot provide human coverage by itself.

**Exit evidence:** repeatable release/rollback, bounded review and queue age, tested monthly recovery, stable cost per active buyer and per published video, and no unresolved critical safety/security findings. Confirm that a second region/category is isolated to configuration, validation and category-specific migration work.

**Main risk:** unbounded operations and cost. Video consumption, OTP abuse and manual safety workload can outgrow the maintainer before API throughput does.

## Phase 3 — design load and measured scale

Load-test the declared 100,000-MAU workload and 5,000-video daily ingestion separately, including peaks and dealer bursts. Scale APIs/workers independently, isolate broker from evictable cache traffic, use managed transcoding capacity, tune hot queries and add read replicas only for lag-tolerant consumers. Partition/expire raw events and messages when measured sizes/plans justify it; preserve idempotency indexes and historical cursor semantics.

Extract media processing first if independent deployment, sandbox security or encoding capacity demands a service boundary. Introduce a learned FeedRanker only after sufficient consented labels, offline evaluation, online safeguards, bias/abuse monitoring and an operational fallback exist. Keep payments, native apps and vehicle-history products outside this roadmap until separately scoped.

**Exit evidence:** target API/message/playback/upload percentiles at declared peak, controlled failure drills, proven restore objectives, acceptable cost run rate, reviewed legal duties as enterprise size changes and sufficient operational staffing. Reassess DSA business-size exemptions independently of MAU; 100,000 MAU does not itself make the service a designated very large platform.

**Main risk:** data-plane cost and operational complexity. Adopt a new service, datastore or ranking model only when it resolves a measured bottleneck with a clear owner and rollback path.

## Suggested delivery order after scaffolding

1. Validate local setup and the core end-to-end path, then close authorization and idempotency gaps.
2. Connect EU-reviewed production video, SMS and notification providers with contract tests.
3. Finish safety tooling, notice/appeal paths, retention and privacy operations with the named operator.
4. Run real-device, load, recovery and incident tests; verify costs and complete legal/data-flow review.
5. Invite a small dealer/buyer pilot, measure outcomes, and expand only when safety coverage and supply are ready.
