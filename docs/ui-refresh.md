# Motorloop UI refresh

The November 2026 refresh gives the complete local application a shared visual language: forest green navigation, warm off-white surfaces, lime accents, rounded cards and clear typography. It covers Discover and filters, direct adverts, Saved cars, My cars, Dealer studio, Messages and viewings, Safety centre, moderation, authentication, profile and advert dialogs, plus signed-out, loading and empty states.

## Design and assets

- Shared `BrandMark`, `LoopArtwork` and `PageHeading` components keep page titles and brand artwork consistent. The icon and installed-PWA colours match the application.
- Core colours and spacing live in `frontend/src/styles.css`. Buttons, fields, cards, status pills, alerts, dialogs and navigation share styles and interaction states.
- [Manrope](https://github.com/google/fonts/tree/main/ofl/manrope) is self-hosted under `frontend/public/fonts/`, with its SIL Open Font License included. It is preloaded locally; browsers do not request Google Fonts at runtime.
- Existing illustrated sample video posters are retained. No photo-upload feature or replacement inventory photography was introduced.
- The shell cache is versioned for the updated icon and manifest. Its activation cleanup is limited to Motorloop shell caches.

## Page improvements

Discovery has a clearer search/filter hierarchy, cleaner video controls and a structured details panel. Advert and saved cards use the same specification, pricing and seller styles. My cars adds an overview scoped to the adverts loaded in the current view, with clearer status and editing actions.

Dealer studio explains the real CSV/video workflow, includes a downloadable template, shows selected files and makes the cents-based CSV price format explicit. Messages has clearer conversation headers, message bubbles and viewing cards; on mobile, an open conversation has an All conversations back button. The mobile profile also includes a sign-out action.

Forms have readable labels, section headings, consistent validation and scrollable dialogs. Dialog headings and close controls stay available while scrolling. A click in a dialog's padding no longer dismisses an unfinished form; clicking outside or pressing Escape still closes it.

## Responsive and accessibility checks

The browser suite checks desktop and 390×844 layouts, local font loading, horizontal overflow and the mobile feed price/navigation boundary. A focused final check also verified Discover at widths 320, 390, 768, 820, 1024 and 1440 pixels without horizontal overflow. Short desktop windows hide the decorative sidebar promo so navigation is not compressed. Screenshots cover public, member, dealer and moderator pages, including dialogs and empty states. Keyboard focus styles, a skip-to-content link, labelled dialogs, reduced-motion support and mobile form input sizing are included. These checks are not a full accessibility audit or physical-device certification.

The functional regression suite exercises the existing API and storage pipeline: search/share/saved cars, upload/chat/viewings, upload interruption/resume and seller controls, and failed-video recovery. The refresh stays local; it does not publish, commit or push changes.

## Screenshots

- [Discover on desktop](screenshots/ui-discover-desktop.png) and [mobile](screenshots/ui-discover-mobile.png)
- [Seller dashboard](screenshots/ui-seller-desktop.png)
- [Dealer studio](screenshots/ui-dealer-desktop.png)
- [Upload dialog](screenshots/ui-upload.png)
- [Profile dialog](screenshots/ui-profile.png)
- [Safety centre](screenshots/ui-safety-desktop.png)
- [Moderation](screenshots/ui-moderation-desktop.png)
