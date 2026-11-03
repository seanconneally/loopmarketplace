# 1. Assumptions and open questions

Each assumption is a working default, not a verified product requirement.

## Assumptions

- **Name:** Motorloop is the working app and project name; trademark and domain availability have not been checked.
- **Launch region:** Dublin, Ireland, with a configurable launch boundary and default 50 km search radius.
- **Locale:** English and EUR initially; region configuration owns currency, timezone, supported locale and geographic boundary.
- **Scale:** Launch at 1,000 MAU; design for 100,000 MAU and 5,000 new videos/day; concurrency and traffic distributions will be modelled in deliverable 7.
- **Targets:** API reads p95 <200 ms, first frame <1.5 s on 4G, message delivery <1 s, upload-to-live <2 minutes excluding human review, and 99.9% availability are objectives to validate, not guarantees.
- **Deployment:** Production targets managed container hosting, PostgreSQL/PostGIS, Redis and object storage in AWS eu-west-1, subject to provider capability, cost and residency review before provisioning.
- **Residency:** Content, databases, backups, queues and observability data must remain in the EU; any CDN, SMS, push or email provider must pass a separate data-flow and contractual review.
- **Budget:** No spending limit has been supplied; no paid resources will be provisioned during design or scaffolding.
- **Accounts:** All verified members can buy; adult members can sell; dealer and admin permissions are explicit grants rather than mutually exclusive buyer/seller identities.
- **Age:** Sellers must declare that they are 18+; this declaration is not proof of age, and stronger verification remains a product/legal decision.
- **Verification:** SMS OTP is mandatory before publishing or messaging; dealers also require manual business verification before receiving a badge or bulk import access.
- **Transactions:** There are no payments, deposits, escrow, delivery or title-transfer services in the app.
- **Video:** Accept MP4/MOV containers, enforce 15–60 seconds and a 500 MB source limit, and validate actual codecs and content after upload.
- **Processing:** Use a local ffmpeg adapter for development and an EU managed-transcoding adapter for production, behind the same VideoProvider interface.
- **Car data:** Use typed car attributes and a category adapter, with common marketplace fields on listings; a future category adds its own validated schema and typed data rather than changing the core listing model.
- **Location:** Store a coarse seller-selected listing point; expose an approximate area publicly and share precise meeting details only within a conversation.
- **Publication:** Listings go live only after required verification, successful processing, rights confirmation and moderation checks; suspicious content remains pending review.
- **Launch inventory:** Seed the feed with licensed test media locally and consenting, verified dealers in production; no scraped videos or third-party adverts.
- **Notifications:** In-app history is authoritative; push requires opt-in and email requires a verified optional address, with both channels delivered asynchronously.
- **Analytics:** Collect non-essential watch and impression events only with consent; retain essential security and delivery records under a separately documented basis.
- **Development:** Docker Compose must support a local happy path without paid credentials using clearly labelled development-only OTP, storage and notification adapters.
- **Testing:** Production security and performance claims require real Postgres/Redis integration tests, concurrency tests and load tests; the scaffold alone will not establish them.

## Open questions

- **Brand and geography:** Are Motorloop and Dublin the desired name and first launch area?
- **Business and budget:** What legal entity operates the marketplace, what dealer volume is committed, and what monthly infrastructure ceiling should shape the cost model?
- **Deployment:** Is there an existing EU cloud account or a preferred host that should replace the proposed AWS target?
- **Identity:** Is an adult declaration sufficient for launch, or is stronger age/identity verification required?
- **Moderation:** Who reviews flagged listings and appeals, during which hours, and under what response-time target?
- **Privacy:** Which lawful bases, retention periods, international-transfer arrangements and dealer obligations will counsel approve?
- **Providers:** Which SMS, email, push and video providers meet the budget and EU data-flow requirements?
- **Media rights:** Can the operator provide owned or licensed sample videos and documented dealer upload consent?
- **Traffic:** What average viewing time, playback bitrate, source size and concurrent-user peak should replace the explicit estimates in the later cost model?

Unanswered questions do not block this architecture. They remain visible inputs to subsequent schema, compliance and cost decisions.
