# Pilot catalogue and mobile readiness

Updated 14 November 2026. This is local development work; production startup remains
guarded by the existing release gates.

## A useful demo catalogue

With the Compose app running, expand the catalogue:

```sh
docker compose exec -T api python -m app.demo_inventory
```

The optional loader adds 24 clearly labelled synthetic adverts: six cars, six homes,
six golf listings and six chairs, across eight Dublin areas and four additional
fictional sellers. The original six samples remain, giving 30 fixture adverts in a
fresh environment. Existing user/test adverts are preserved, so an older database
may contain more. Cars cover six additional makes and a range of fuels, gearboxes,
prices and mileages. Other categories vary their applicable facts and prices.

Each advert has a generated, original category illustration and a 15-second MP4
processed through the normal HLS encoder. These are illustrations, not photographic
walkarounds. Four added clips contain a quiet synthetic test tone for mute/unmute
checks; all playback starts muted. Titles, descriptions and artwork identify the
synthetic nature of the catalogue. Nothing is represented as a real item for sale.

Stable seller, advert and asset keys make the command repeatable: a verified second
run added zero adverts. Completed assets are reused; closed demo adverts are not
reactivated. The loader refuses non-development environments and disabled seeding.
It does not run on every startup, so the default six-sample initialization stays small.

For a real pilot, sellers still need to upload videos they own through the app. No
seller footage, stock adverts or third-party inventory was scraped or purchased.

## Browser checks

From `frontend/`:

```sh
npm run test:mobile
```

Both Playwright configs respect the root `.env` WEB_PORT / PUBLIC_ORIGIN settings;
BASE_URL can override the target. Eight checks run across Pixel 7 Chromium and
iPhone 13 WebKit profiles. They cover session loading/failure/retry, render recovery,
draft retention offline, file selection, keyboard-sized dialogs, page overflow and
end-of-feed refresh. Chromium checks actual playback and pause/resume; the Windows
WebKit build is not a physical iPhone codec/audio certification.

The controlled refresh test proves that no-new-results preserves the current advert,
that new adverts beyond repeated first-page results are found, and that Previous
returns to the original set. Its synthetic feed requests deliberately bypass the
service worker to keep request interception deterministic. The other mobile tests
retain the normal service-worker path. CI now installs Chromium and WebKit and runs
the dedicated mobile suite after the existing desktop scenarios.

## Physical phone acceptance — pending

No physical phone was available for this session. Browser profiles do not verify a
phone's real camera/gallery, keyboard, media codecs, background suspension or network
handoff. Use the [physical-device checklist](recovery-and-mobile.md#physical-device-acceptance--pending)
when hardware is available and record device, OS/browser, tester, date and result.

Keep the simulated-auth development stack private. For Android USB testing, authorized
ADB forwarding of both the configured web port and storage port can keep the PC's
loopback bindings intact. An iPhone needs an appropriate private device-access setup
or a secured review deployment. Do not expose the fixed-OTP demo publicly to make a
phone connection work.

Before any public pilot, finish real authentication/provider abuse controls and the
other [release gates](09-scaffold.md#production-release-gates). Measure saves, real
seller conversations and accepted viewings; the demo catalogue cannot establish
marketplace demand or recommendation quality.
