# Discovery, direct adverts and saved cars

## Finding an advert

The discovery page searches title, make, model, coarse area, year, fuel and transmission. Search is case-insensitive, collapses repeated whitespace and accepts up to eight words / 100 characters. Each word must match somewhere in those fields. Percent and underscore characters are treated literally, not as SQL wildcards. Descriptions and private seller details are not searched.

The make selector comes from published inventory, replacing the original three hard-coded brands. Budget and distance controls remain available alongside advanced minimum/maximum price and year, fuel, transmission and mileage filters. Reversed price/year ranges are rejected. Active chips can be cleared individually or together.

The search URL retains these settings across reloads, browser history and shared links. Defaults are omitted from newly created URLs, and malformed incoming filter values fall back to usable bounds. Opening an advert from discovery provides a Back to discovery link that restores the search.

## Sorting and pagination

- **Recommended** keeps the existing five-minute ranked snapshot of up to 150 candidates, with a recency fallback when Redis/ranking is unavailable.
- **Newest first**, **Lowest price** and **Highest price** use database ordering and signed keyset cursors. They paginate through all matching inventory without the recommendation window's 150-candidate cap.
- Price sorts break ties by newest publication time and then descending UUID. Newest uses publication time and descending UUID. Cursors bind the full filter set and the account, so changing search/account requires a fresh page.
- Pages fill around hidden adverts in bounded batches. Current price/specification/visibility/block/account rules are checked when a ranked snapshot is read, so an edited advert outside the active budget is not returned from an old snapshot.
- Live price changes can move adverts between SQL pages. The client deduplicates IDs across loaded pages; refresh results to obtain the current ordering. Loading failures or expired recommendation snapshots offer a fresh-results action instead of repeating failed requests automatically.

Search and ordering run in PostgreSQL, not against a small client-side slice. Existing geographic, region/filter and recency indexes remain in use; no migration is needed for this pass. Keyword/fuel/transmission/mileage predicates currently read the public JSON projection. Representative query plans and dedicated search/order indexes remain measured scaling work before large-inventory deployment.

## Direct advert pages and sharing

`/cars/{listing_id}` opens an advert's video, complete details and seller controls. It supports browser reloads and opening in another browser context. Sold adverts remain readable with a sold message and disabled buyer contact. Removed, private or blocked adverts show an unavailable state according to the existing backend access rules; the route does not bypass them.

**Share advert** copies a URL on the current origin and confirms success. If clipboard access is unavailable or denied, a selectable read-only link is shown for manual copying. The URL contains the advert ID, not credentials or signed storage links. A localhost link works on the device hosting this local app; sharing with other people requires a deployed origin.

The advert page polls live state while open and receives owner status invalidations. Buyer save controls prevent duplicate submissions and synchronize discovery, advert and saved-list caches. Owners have a Manage advert link and can mark published adverts sold; buyers cannot start a new contact from sold adverts.

## Saved cars

The shortlist includes posters, live/sold labels, direct advert links, owner management, buyer messaging and removal. **Load more saved cars** uses the API cursor rather than stopping after the first page. Hidden adverts are skipped while filling a page, and a member can remove their own saved reference even if the original advert is no longer visible. Saved cursors are bound to the member. Opening an advert from the shortlist offers Back to saved cars.

## Verification

The integration suite creates disposable inventory with equal price/publication-time ties, traverses all three explicit sort orders across multiple pages, checks literal wildcard search and combined filters, rejects cross-account/filter cursors, verifies snapshot price rechecks, and fills a 20-item saved page around hidden entries. It removes its synthetic public projections afterward.

The new browser journey exercises URL/filter reloads, an actual clipboard copy, a direct advert link in a separate browser context, unavailable pages, save/reopen/remove and empty-search recovery. Existing upload, chat, viewing and seller journeys remain in the regression suite. See [validation.md](validation.md) for current results and screenshots.
