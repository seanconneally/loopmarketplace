# 8. Trust, safety and compliance plan

**Legal review required before public launch.** This is an engineering plan and proposed operational policy, not a legal determination. In particular, counsel must confirm the operator's DSA classification/exemptions, trader obligations, lawful bases, age assurance, media rights, retention and international data flows. A local development scaffold does not implement or prove every production control described here.

## Current implementation boundary

Source inspection finds local phone-OTP simulation with rate limits, rotating sessions, adult/rights declarations, private source/processed media, text/contact and exact poster-dHash review signals, chat scam warnings, reports, symmetric blocks and reasoned admin actions. Media uses local ffmpeg and SeaweedFS S3 storage. Notification jobs store in-app records only; they do not send real SMS, push or email. This is source reconciliation, not a claim about runtime checks.

Production sampled-frame/prohibited-content scanning, price-anomaly detection, affected-user statements of reasons, public account-free notices, appeals, export/deletion, retention automation, real providers and full EU data-flow evidence remain release gates. `APP_ENV=production` deliberately rejects startup. The user overrode the source prompt's pause checkpoints; no further review pause is required to finish these deliverables.

## Verification and publication

Require phone verification before publishing or starting/sending chat. OTP challenges expire, have an attempt ceiling, use per-phone/IP/account limits and store hashes rather than codes; delivery goes through a queued provider adapter. Add account-age quotas and abuse budgets because phone verification does not prove identity, ownership, adulthood or honesty.

Private sellers declare they are 18+ and confirm they own the item and have the right to upload the video. The scaffold stores boolean declarations; production must also retain approved declaration versions/timestamps and the agreed assurance evidence, avoiding a full birth date unless needed. Dealer import checks the dealer role and stored business-verification fact; the verification administration/evidence workflow remains manual/planned and needs reviewer, expiry/recheck and revocation records. Bulk upload cannot bypass ordinary draft/media checks.

Use an explicit publication gate: active eligible seller + rights declaration + valid typed car details + ready media + acceptable moderation result. A client completion callback never sets a listing live. Sold, removed, suspended and blocked items must disappear from feed responses immediately through current authorization/visibility checks; projection/cache updates follow asynchronously.

## Fraud and content pipeline

| Signal | Automated action | Human decision |
| --- | --- | --- |
| Invalid duration/codec, oversize file or corrupt media | Reject processing, retain a minimal error and short-lived quarantined evidence | Review processing failures on appeal |
| Prohibited content or exposed contact details in text/frames | Keep pending review; do not publish the original | Approve, require an edit or remove with a reason |
| Similar perceptual hash | Link a duplicate-review case with source IDs | Decide whether it is a permitted dealer repost or suspicious copy; hash similarity is not proof of theft |
| Extreme price relative to comparable make/model/year | Add a review signal and lower new-account limits where justified | Review context; rare/modified/damaged vehicles can be legitimate outliers |
| Deposit requests, payment links or courier stories in chat | Warn the recipient and attach an explainable signal | Escalate reported cases; do not silently claim every matching message is fraud |
| Burst posts/messages or repeated reports | Rate-limit, challenge or temporarily restrict according to policy | Review before prolonged suspension; protect against coordinated false reports |

Inspect uploads in restricted workers with resource/time ceilings, patched codecs and no arbitrary network fetches. Sample frames and listing text through approved scanning adapters; store scan version/confidence and review outcomes. Automated scanning reduces review load but does not replace reporting, trained staff or an incident route.

Chat warnings should say what triggered the warning and recommend avoiding advance payments, sharing payment credentials or following unfamiliar links. Hide account phone/email unless the person deliberately shares it in their own message. Preserve reportable evidence with access controls, while avoiding message-body copies in ordinary logs and notification previews.

## Reports, blocks, decisions and appeals

Anyone can submit an illegal-content notice from an easy-to-find listing/user/report page, including a content URL/ID, reason and supporting explanation; provide a non-account notice route rather than requiring a reporter to register. Authenticated users can also report a conversation message or block another member. Blocking is enforced bidirectionally for new contact, feed visibility and active sockets, with a carefully documented policy for access to existing safety evidence.

The admin queue shows severity, age, report evidence, related signals and prior decisions. Enforce server-side admin authorization, audit reads of sensitive evidence, and require a structured reason for approve/remove/suspend actions. Record target, actor, timestamp, legal/terms reference, relevant facts, automation involvement, scope/duration and available redress; notify the affected person with a clear statement of reasons. Keep appeal review separate from the initial decision where staffing permits.

Operational starting targets: acknowledge notices immediately, triage credible imminent-danger cases urgently, triage high-risk fraud/illegal-content reports within 24 hours, and other cases within two working days. These are staffing targets, not a statement of a universal statutory deadline. Provide an escalation/runbook and an on-call owner before accepting public inventory; do not promise 24-hour coverage with no reviewer available.

## DSA applicability

Motorloop stores and publicly distributes user adverts, so the design treats it as a hosting service and likely an online platform; counsel must confirm that classification. Small scale does not remove all DSA duties. See the Irish regulator's [service categories](https://www.cnam.ie/industry-and-professionals/online-safety-framework/digital-services-act/who-does-the-dsa-apply-to/) and the Commission's [DSA questions and answers](https://digital-strategy.ec.europa.eu/en/faqs/digital-services-act-questions-and-answers).

| Stage | Duties to assess | Design response |
| --- | --- | --- |
| Launch, including micro/small operators | Intermediary contacts/terms; hosting notice-and-action, statements of reasons and qualifying serious-crime escalation (Arts 11–14, 16–18) | Contact routes, versioned terms, public notice form, case tracking, decision notifications, restricted escalation runbook |
| Verified micro/small status | Some transparency/platform duties have exemptions (Arts 15(2), 19); Art 24(3) information requests still matter | Record exemption assessment and business-size evidence; retain aggregate recipient and moderation records |
| Loss of exemption | Platform complaints/redress, trusted-flagger handling, misuse, transparency, advertising/recommender and minor-protection duties become relevant, with applicable transition rules | Appeal workflow, priority routing, reason taxonomy, reporting exports and explainable feed controls |
| Trader distance-contract service, if applicable | Arts 29–32 have a separate scope/exemption analysis | Assess dealer identity, trader disclosures and compliance-by-design before adding contract checkout flows |
| Very large platform designation | Additional systemic-risk/audit/data-access duties follow designation at the applicable EU recipient threshold | Measure EU recipients distinctly from account MAU; create a new compliance programme if approaching designation |

Article 30 concerns platforms allowing consumers to conclude distance contracts with traders. In-person payment and no checkout do **not**, by themselves, settle whether contractual agreement through chat falls within that scope. Do not collect dealer payment-account/identity-document data solely by assumption; obtain a scope decision and implement any required verification/disclosure/retention before launch. See the [DSA text, especially Articles 19, 29 and 30](https://eur-lex.europa.eu/legal-content/EN/TXT/?qid=1667477533513&uri=CELEX%3A32022R2065).

Statements of reasons to affected users are a hosting obligation. Submission to the Commission's public Transparency Database is a separate platform obligation with micro/small exemptions; do not publish personal evidence or report text into that database. See the Commission's [transparency overview](https://digital-strategy.ec.europa.eu/en/policies/dsa-brings-transparency) and [database onboarding guidance](https://sandbox.sor.dsa.ec.europa.eu/page/onboarding-documentation).

## GDPR and privacy engineering

Maintain a data inventory covering purpose, category, lawful basis, processor, region, access role and retention. Suggested bases to evaluate are contract for core account/chat functions, legitimate interests with a recorded balancing assessment for proportionate security/fraud controls, legal obligation where applicable, and consent for non-essential analytics. These are proposed mappings for counsel to approve, not blanket bases for every event or scan. Data minimisation and documented deletion/review periods underpin the design; see the DPC's [data-protection principles](https://dataprotection.ie/en/organisations/data-protection-basics/principles-data-protection).

Use coarse public listing locations and avoid ingesting a home address through video metadata. Strip location/device metadata from public derivatives; protect the private source separately. Viewing places are participant-only. Encrypt storage/backups in transit and at rest, use least-privilege service accounts, keep secrets outside the repository and audit access to phone numbers, dealer evidence, reports and private messages.

Non-essential product analytics is disabled until affirmative opt-in. Offer equally accessible accept/reject controls and a persistent privacy-settings route; store consent version/time and stop new collection when withdrawn. Necessary session/security processing must have a bounded, documented purpose and must not become a hidden analytics channel. The DPC confirms that [analytics cookies need consent](https://www.dataprotection.ie/en/faqs/cookies/do-i-need-consent-analytics-cookies) and that [withdrawal must be easy](https://www.dataprotection.ie/en/faqs/cookies/my-website-or-app-uses-cookies-and-other-tracking-do-i-have-get-consent-users).

### Proposed retention schedule

The periods below are engineering defaults for review, **not periods prescribed by GDPR**. Every exception needs a reason, access restriction, expiry and review owner. GDPR does not set one universal retention schedule; see the DPC's [retention guidance](https://www.dataprotection.ie/en/faqs/responsibilities-data-controllers/how-long-should-personal-data-be-held-meet-obligations-imposed-gdpr).

| Record | Proposed default | Deletion/review mechanism |
| --- | --- | --- |
| OTP challenge | Five-minute validity; delete expired records within 24 hours | Scheduled cleanup; rate-limit counters expire separately |
| Refresh sessions | Local fourteen-day lifetime, revoked at logout/reuse; production maximum to approve | Hash-only record; family revocation implemented, scheduled record cleanup planned |
| Upload parts/failed quarantine | Abort abandoned multipart uploads after 24 hours; rejected sources after seven days | Storage lifecycle plus media reconciliation |
| Successful original video | Seven days after processing unless a documented evidence need applies | Private object deletion job and ledger |
| Public derivatives/listing media | While live, with a 90-day review/expiry policy; sold/removed content inaccessible promptly | Unpublish, purge CDN, delete within the approved window; explicit seller renewal if still live |
| Chat and viewing details | Review/delete 12 months after last conversation activity; earlier erasure where applicable | Participant policy, redaction/anonymisation and limited evidence holds |
| Raw consented analytics | Proposed 30 days; non-identifying aggregates up to 13 months | Partition/deletion automation planned; local seen sets expire after seven days, stop being read on withdrawal and are cleared by a durable event; full deletion is still planned |
| Security logs | 30 days normally, up to 90 for investigated incidents | Redaction, strict access and scheduled expiry |
| Moderation/appeal evidence | Provisional 12 months after case closure | Legal/rights balancing review; minimize message/video copies |
| Backups | Rolling 35-day recovery window | Expire copies; reapply deletion ledger on restore before serving users |

A longer legally required hold overrides routine deletion only for the specific data and purpose approved. Do not erase another participant's necessary conversation record indiscriminately; assess redaction/pseudonymisation and explain the result to the requesting person.

### Rights and incidents

Provide authenticated export and delete-my-data requests with step-up verification and status tracking. Background jobs collect module-owned records, export a machine-readable archive through an expiring private URL, revoke sessions, unpublish content and remove/anonymise approved records across storage, projections, caches and providers. Keep a minimal request/deletion ledger, not an unrestricted copy of the erased account. Track one-month response handling and any valid extension/refusal; see the DPC's [rights guidance](https://www.dataprotection.ie/en/individuals/know-your-rights/restriction-individual-rights-certain-circumstances).

Before production, document processor agreements, subprocessors, support access, data-transfer grounds, EU hosting evidence and a DPIA screening. EU database location alone does not establish complete residency for CDN edges, SMS routing, push infrastructure, telemetry or vendor support. If a provider cannot meet the agreed restriction, replace it or resolve the product requirement with the operator before enabling it.

Maintain an incident log and decision owner. Risk-bearing personal-data breaches require notification to the competent authority without undue delay and, where feasible, within 72 hours of awareness; high-risk breaches may require notifying affected people. Document even a decision not to notify. See the DPC's [breach guidance](https://www.dataprotection.ie/en/faqs/responsibilities-data-controllers/what-do-i-do-if-there-security-breach).

## Public launch acceptance

The operator must supply a named safety owner, tested report/appeal routes, approved terms/privacy/rights notices, staffed review targets, verified production adapters, EU data-flow evidence, removal/purge tests and a completed restore/incident drill. The implementation inventory must distinguish working local behaviour, disabled development adapters and outstanding production controls; passing CI alone is insufficient.

In particular, local admin removal changes database/feed visibility but does not establish production CDN purge, and local moderation action audit records do not yet generate a legally reviewed affected-user notice or appeal process. Treat those as release-blocking gaps rather than implying the moderation queue alone meets DSA duties.
