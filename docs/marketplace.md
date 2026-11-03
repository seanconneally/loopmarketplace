# Loop Marketplace: mixed inventory

Implemented locally on 3 November 2026.

## Product behaviour

Anyone eligible to sell can upload a video of something they have the right to advertise, subject to the existing safety checks. The default For you page mixes all live listings. The optional Cars, Homes and Golf clubs tabs narrow the feed. Something else is a seller choice, not a browse tab: those listings appear in the mixed FYP. Search and direct shared links continue to work for every listing.

The upload flow starts at Something else, so unrelated items never need invented car facts. Cars require make, model, year, mileage, fuel and gearbox. Homes offer property type, bedrooms, bathrooms and floor area. Golf clubs offer brand, club type, hand and condition. Other items offer optional brand and a condition. Price, title, description, approximate location, seller and video remain common. Category-specific details are validated by the API, including rejecting facts that belong to another category.

Current launch constraints remain Dublin, EUR, positive asking prices up to €20 million and owned MP4/MOV videos of 15–60 seconds up to 500 MiB. This does not add rentals, property transactions, payments or arbitrary prohibited inventory support. The existing moderation and production release gates still apply. Illustrations are marked sample inventory, not real adverts. Photos remain deferred.

## Data and compatibility

Migration 0006 adds a validated attributes JSON object to listings, a category column and region/category/recency index to feed candidates, and allows absent car make/year in that projection. Existing cars retain their separate typed car_details records. Downgrade refuses to discard category facts while non-car inventory exists. No existing database volumes or original migrations are replaced.

All categories share publication, moderation, processing, multipart resume, revisions, seller controls, saves, chat and viewings. Editing the category replaces its category facts and adds/removes the car record as appropriate. Car filters are shown in Cars; general filters never silently exclude non-car rows by requiring a year.

Canonical URLs are /listings/:id and /my-listings. Old /cars/:id and /my-cars links remain accepted. Internal motorloop names and local draft keys remain for data compatibility. The existing Dealer studio CSV template is explicitly car-specific; other listings use Sell something.

## Adding another category

Add its schema to backend/app/modules/listings/categories.py and the listing category type, then add the form/spec metadata to frontend/src/features/listing/categories.ts. Add it to the explicit browse filter enum and tabs if it should be filterable. Regenerate OpenAPI/frontend types and cover creation, category-specific validation, editing, feed projection/filtering and shared links. New attribute-only categories do not need a database migration. A category requiring complex querying may justify typed fields or another table rather than unlimited JSON indexing.

The ranker automatically includes category affinity and a separate price preference per category. Add explicit bounded feature extraction for any additional useful facts. Do not infer interests from free-text titles, private messages or sensitive attributes.
