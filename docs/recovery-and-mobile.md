# Recovery and mobile readiness

Implemented locally on 3 November 2026. Changes remain uncommitted and unpushed.

## Crash and session recovery

A root React error boundary provides recovery if the application tree fails to render. A second boundary isolates page rendering so navigation remains available. The recovery screen offers Try again, Reload Motorloop and Back to discover, without displaying raw exception text. Page retries reset query state and load fresh data. Navigation to another route resets a failed page boundary. As with React error boundaries generally, event-handler and asynchronous failures still need their existing try/catch handling; the boundary does not claim to catch all JavaScript errors.

Authentication distinguishes checking, authenticated, signed-out and temporarily unavailable. Protected pages show a loading state while the initial refresh is pending. A network error or server failure offers retry instead of being treated as a confirmed sign-out. The initial refresh has a ten-second timeout. Explicit invalid-session responses remain signed-out, and the previous version guards still prevent a delayed startup result from undoing a newer login.

## Connection and unfinished work

The interface shows a persistent offline banner and a short reconnected notice. Reconnection refreshes reads; it does not submit messages, proposals or adverts automatically. Sending messages, new viewing proposals and upload submission are disabled while the browser reports offline. Request failures have a readable connection/retry message. An online browser indicator is not proof that the server is reachable, so actual request failures remain handled too.

Unsent conversation text and message operation keys are saved by member and conversation in tab-scoped session storage. Reopening the inbox or refreshing in the same tab restores the text, and a retry of an unchanged message retains its key after a lost response. Unsubmitted advert fields are saved in the same way, including incomplete forms. The existing durable pending-advert key and multipart resume flow are preserved. Videos themselves are not stored in browser draft storage; choose the original video again after reopening.

Explicit successful sign-out clears that member's tab drafts. Other members' entries are not removed. Storage failures preserve the in-memory form and show a warning to keep the page open. These local drafts are not a server backup and may disappear when the tab/browser storage is cleared. Closing a tab is not guaranteed recovery. Profile edits, dealer import files and viewing-form text are not newly persisted across reloads by this change. Previously submitted adverts and upload parts remain server-side.

This is connection recovery for an already loaded interface, not an offline marketplace. The service worker still only caches the icon/manifest; a fresh offline page navigation may not load the application. Private API data and message histories are not added to an offline cache.

## Browser checks and their limits

The dedicated suite uses a Pixel 7 Chromium profile and an iPhone 13 WebKit profile. It checks delayed/failed session restoration, retry after a deliberately injected rendering failure, retained navigation, inline-video markup, MOV file assignment, offline advert editing/reopening, disabled submission and a synthetic reduced visual viewport. Chromium also checks actual sample-video playback and pause/resume. The WebKit Windows port is not an actual iPhone and does not certify iOS HLS codecs, autoplay or audio. Programmatic file assignment does not certify a phone's gallery/camera picker. Synthetic viewport changes do not certify an actual on-screen keyboard.

Dialogs use the visual viewport height/offset when available to keep their scroll region and close control within the visible area. The viewport metadata enables safe-area layout and requests content resize for supported mobile keyboards. Existing 16-pixel mobile input sizing and bottom safe-area spacing are retained.

Repeat the checks from `frontend/`:

```sh
npx playwright install chromium webkit
npm run test:mobile
npm run test:e2e
npm test
```

The local API's OTP rate limits apply to browser tests. The full desktop suite uses seven sign-ins and the mobile suite two; avoid repeatedly running them within the same ten-minute quota window. Failure injection is test-only request interception, with no production debug/crash route.

## Physical-device acceptance — pending

No connected iPhone or Android hardware testing facility was available in this Windows workspace. The following remain required before calling hardware testing complete. Record the tester, exact device model, OS/browser version, date and outcome for each.

| Check | iPhone Safari | Android Chrome |
| --- | --- | --- |
| Browse, pause/resume, mute/unmute an audible owned clip, rotate screen | Pending | Pending |
| Select an owned MP4/MOV through the actual system picker | Pending | Pending |
| Open keyboard for phone, OTP, price, long description and chat; reach focused field, submit and close controls | Pending | Pending |
| Scroll dialogs and long pages; inspect notches, home indicator and bottom navigation | Pending | Pending |
| Toggle airplane mode while drafting; reconnect and verify no automatic send | Pending | Pending |
| Interrupt a multipart upload, background/lock the phone, return and resume the same advert | Pending | Pending |
| Refresh after a lost response; confirm one message/advert and retained draft | Pending | Pending |

The default development stack binds to the PC's loopback interface, and its API/media URLs and origin checks are configured for localhost. A phone cannot reach it by entering its own localhost address. Physical testing needs an appropriately configured private review environment or device forwarding; do not simply expose the simulated-auth development stack publicly.

References: [React error boundaries](https://react.dev/reference/react/Component#catching-rendering-errors-with-an-error-boundary), [Playwright emulation](https://playwright.dev/docs/emulation) and [browser engines](https://playwright.dev/docs/browsers).
