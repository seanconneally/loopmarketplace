# Security and UI implementation

This review applies the supplied checklist to Loop Marketplace's React/Vite frontend,
FastAPI backend and local Nginx/S3-compatible stack. Production startup remains blocked
by the existing release guard. The shared development signing key, fixed OTP and fixture
accounts are suitable only for the loopback-bound local environment.

## Security coverage

| Checklist item | Applied control or scope |
| --- | --- |
| Framework headers | Nginx hides upstream server headers and its version. This app uses Vite, not Next.js. |
| Exposed `.git` | All dotfile paths return 404, including nested paths. Build contexts exclude repository internals and `.env`. |
| Storage permissions | Original uploads and processing quarantine stay in the private source bucket. The gateway exposes only known published video, playlist and poster paths, with GET/HEAD only and no storage-operation query strings. Existing owner checks protect signed multipart URLs. Production storage-policy verification remains a release gate. |
| Browser prices | Existing listing schemas validate positive, bounded prices on the server. Only eligible owners may change an asking price, using locked rows and revision checks. There is no checkout or charge calculation; any future checkout must read an authoritative server-side price. |
| Credential stuffing | No password login exists. Existing OTP request/attempt throttles, atomic single use and session revocation remain active. |
| Open database | Database and supporting development ports stay bound to loopback. API access is checked against authoritative account and ownership state. Public deployment needs private networking and rotated credentials. |
| Polyfill.io | No Polyfill.io integration or third-party runtime script CDN. Scripts and fonts are served locally; CSP permits same-origin scripts only. |
| SMS pumping | OTP requests now require the configured application Origin before creating a challenge, in addition to existing phone/IP throttles. SMS remains simulated. Paid-provider spend caps and fraud controls are required before a real adapter is enabled. |
| Prompt injection | There is no LLM or agent integration. Local moderation uses deterministic checks. Any future model must treat adverts/messages as untrusted data and authorize every tool action independently. |
| Weak JWT secret | Configuration rejects signing keys shorter than 32 characters. Existing fixed HS256, issuer, audience, expiry and session checks remain. Malformed identity-claim types now return 401. Length does not prove entropy; production requires a securely generated secret and secret management. |
| Race conditions | Existing row locks, revision checks, scoped idempotency keys, atomic OTP consumption, refresh rotation and generation checks remain. Regression suites cover concurrent/replayed actions. |
| Account pre-hijacking | Accounts are created/verified only after an OTP is consumed; no unverified email account linking exists. |
| Subdomain takeover | No hosted domain or DNS configuration is present. DNS/provider ownership must be checked during deployment and service removal. |
| SSRF | Uploaded videos are probed and decoded with only the local file protocol and MOV/MP4 demuxer allowed. Disguised playlists are rejected before their resources are fetched. No user-controlled server URL fetch feature exists. |
| Path traversal | Upload object keys use server-controlled user/asset/generation identifiers. Local decoding uses a temporary directory. Public media routes accept only expected derivative paths; dotfile and backup paths are blocked. |
| Reset poisoning | No password reset flow exists. Cookies and origin checks use configured settings; the public origin must be HTTP(S), with no credentials, path, query or fragment. Future reset links must use this trusted configuration. |
| Source maps | Vite explicitly disables production maps; the gateway also returns 404 for map files. |
| Clickjacking | DENY and CSP `frame-ancestors 'none'` apply to pages, built assets, service worker, media and errors. A shared include avoids Nginx header inheritance gaps. |
| Open redirects | No arbitrary redirect endpoint exists. Advert navigation remains in React Router; share links use the current application origin. |
| User enumeration | OTP challenge creation does not query account existence. Invalid OTPs use the same error; public seller views omit phone numbers. Session/account status is checked only after authentication. |

CSP also restricts base URLs, embedded objects and form submissions. API responses,
including throttled requests, retain no-store, request IDs and defensive headers.
The gateway suppresses duplicate upstream security headers.
Persisted loopback media URLs follow the configured preview port, so an occupied
default port does not break existing inventory or require rewriting stored adverts.

## Design changes

- Discovery now explains the product directly: “See what’s for sale near you.”
  The description names video tours, local categories, Dublin and seller messaging.
- Removed the generic marketing eyebrow, Dublin badge, decorative details arrow,
  repeated slogan and ordinary-seller badge. Verified-dealer information remains useful.
- Gave the actual listing video more width and height, including on mobile, while keeping
  seller messaging prominent and secondary actions visually quieter.
- Preserved shared Manrope typography, forest/lime colours, components, focus styles,
  responsive layouts and consistent Lucide icons. Secondary text and video badges have
  stronger contrast; mobile feed labels are larger.
- Headings balance their line breaks and descriptions use natural wrapping. Existing
  spacing groups facts, pricing and seller information. Prices and feed counts use
  tabular numerals.
- Video buffering has an announced loading state. Playback failure offers a working
  retry and leaves advert actions available. Missing videos show an explanation.
  Save buttons expose their pressed/busy state and say “Saving…” / “Saved”.
- Existing reduced-motion support remains; spinner motion communicates processing.
  No ornamental animation, random italics or new monospace text was added.

## Verification

Run frontend lint, formatting, build and Vitest. Run backend Ruff, mypy and pytest
from the supported development environment. The new `tests/test_security.py` covers
key length, origin configuration, signed claim types, cross-origin OTP rejection,
throttled-response headers, ASCII OTPs and disguised playlists (ffprobe required).
`Reel.test.tsx` covers buffering, retry recovery and missing-video behaviour.

With Compose running, `node scripts/check-security.mjs` checks the real gateway:
private paths, actual assets, security headers, API cache policy, master/rendition/
segment playback, forbidden media writes/query operations and cross-origin OTPs.
This is a bounded regression check, not a penetration-test certification.

Verified on 14 November 2026: frontend lint/format/build and 32 Vitest cases;
backend Ruff/format/mypy, 31 distinct unit/security cases across Windows Python 3.14
and container Python 3.12 (including real ffprobe); 13 integration cases, including
audio and silent-video transcoding; no migration drift; Nginx configuration validation;
and the live gateway security checks. Windows omits ffprobe-only cases, which were
run in the application container. Desktop and mobile browser layouts were inspected.

References: [OWASP HTTP headers](https://cheatsheetseries.owasp.org/cheatsheets/HTTP_Headers_Cheat_Sheet.html),
[PyJWT validation](https://pyjwt.readthedocs.io/en/stable/api.html),
[FFmpeg protocol restrictions](https://ffmpeg.org/ffmpeg-protocols.html).
