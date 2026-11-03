# Seller dashboard and resilient uploads

Open [My cars](http://localhost:8080/my-cars) after signing in. On desktop it is in the sidebar; on mobile open Account, then My cars.

## Managing adverts

- **Edit details:** update the price, description, area or car specification. Saving checks the latest revision; another tab or processing update produces a conflict instead of overwriting changes. Reopen the editor to load the current details. Clean live edits update the feed projection. Flagged text goes back to human review, including a new edit with previously reviewed text.
- **Pause advert:** hide an approved advert from discovery while keeping its details/video. **Resume advert** restores it. Neither action bypasses moderation, and approval preserves a seller’s pause preference.
- **Mark as sold:** closes a live or paused advert and removes it from discovery. Closed adverts cannot be edited or accept another video.
- **Retry processing:** uses the retained private original, without another upload. Three seller retries are allowed per uploaded video; replacing the video starts a new retry budget. A missing source requires choosing the video again.
- **Replace video:** explicitly discards an unfinished upload or replaces a failed video on the same advert. Successfully approved videos cannot be replaced through this flow.

## Recovering an interrupted upload

1. Open the saved advert in My cars and choose **Resume upload**, or reopen Sell a car to continue its saved draft.
2. Select the **original file**. After a refresh, browser security requires selecting it again; file bytes are never saved in localStorage.
3. The browser hashes the complete file in bounded 4 MiB chunks. The server checks its SHA-256 and size, lists actual stored parts and returns refreshed signed URLs. Already saved 8 MiB parts are skipped.
4. Pause, close the dialog or leave the page at any time. Resume reconciles storage again, including a part whose successful response was lost. An interrupted part is resent in full.
5. Once all parts are finalized, processing continues in the background. The dashboard polls processing adverts and also receives status notifications.

If the upload has expired, choose **Replace video** on the same advert. Storage is configured to abort abandoned multipart uploads after one day; actual cleanup timing depends on the storage provider. Signed part URLs expire after 15 minutes and are refreshed during resume. Network retries are bounded, so a persistent outage produces a resumable error instead of looping indefinitely.

Draft details are persisted in PostgreSQL. A small per-account browser record stores the exact create request, idempotency key, original filename and returned draft ID before uploading. This also recovers a draft whose creation committed but whose response was lost. It stores no credentials, signed URLs or video bytes. **Start another advert** deliberately starts a new advert; the previous server draft remains available in My cars. Clearing browser storage loses that local hint; committed server drafts remain in the dashboard.

## Audio and processing

New videos map the optional original audio track to AAC at 96 kb/s in both 360×640 and 720×1280 HLS renditions. Silent videos remain valid. Playback starts muted for browser autoplay and offers an unmute button for audible videos; silent clips show No audio. Existing silent derivatives stay silent until regenerated from an original that contains sound.

The worker verifies the original’s SHA-256 before encoding, strips metadata and quarantines outputs until approval. Upload generations guard completion and job finalization: old callbacks/jobs cannot complete, publish or fail a replacement/retry. This remains a local development ffmpeg adapter; the production gates in the scaffold documentation still apply. Completed originals and old processed versions currently remain in local storage; production retention/purge enforcement is still required.

## Validation

See [validation.md](validation.md) for exact checks. The browser test forces a lost successful draft response, aborts storage PUTs after the first part, refreshes, rejects a same-name/same-size file with different bytes, resumes without resending the saved part, then exercises edit, pause/resume and sold. A separate journey exercises failed processing and a retained-source retry. Real ffmpeg tests probe both HLS renditions for AAC and verify silent input.
