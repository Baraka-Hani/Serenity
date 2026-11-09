# Travel discovery maps

Serenity is a watch → find the place → travel there product, not a live friend-location service. `/map.html` is a fifth toolbar destination. It displays only trips that have both a saved destination pin and at least one public video. Private trips, private clips, unpublished notes, emails, and unpinned legacy destinations never appear in its API. There is no device geolocation, live tracking, EXIF extraction, or automatic inference of cities from videos.

## Creator workflow

Clip Studio's manual form, saved-trip editor, and categorized collection review use the shared destination picker. Search for a public city/landmark and explicitly select a result; alternatively open the map and click a point, or enter a name and latitude/longitude with the keyboard. Search text alone is not a pin. Stored values are numeric coordinates, a readable place label, provider/source, and an optional provider reference. Creator-selected coordinates are not verified GPS evidence that a clip was filmed there.

Pins on published trips are public, as explained beside the field. Editing the destination of an already-public trip changes its map location and published destination labels. Removing its pin removes the trip from Map but does not unpublish its Home feed videos. Making all videos private removes the trip from Map; its saved private pin is retained for the owner. Existing published trips without coordinates remain on Home feed until the creator chooses **Add destination pin for Map** on their preview.

Dates and highlights are retired from trip forms and `/api/feeds/ID/details` responses. New writes ignore those legacy fields, and new posts no longer append them. SQLite's old columns and existing historical caption text are retained for backwards compatibility/data preservation; no old caption is automatically rewritten or personal data erased. A trip now consists of a name, an experience/story, an optional destination pin, and videos. Private planning notes remain separate from published travel information.

## Viewing and visiting

Map can be browsed without an account. Pan/zoom, search published trip/place names, choose a marker or accessible trip-list button, watch its public preview, open the trip's videos, and open **Get directions**. Nearby markers cluster visually; trips at the same point remain individually selectable in the list. A maximum of 200 trips is returned per request; zoom or search to narrow large result sets. Trip pages and the Home feed travel panel also link to the saved destination and directions. Directions open Google Maps URLs with only the selected destination coordinates; no origin or user GPS is collected by Serenity and no Maps API key is needed.

## APIs and modules

- `GET /api/map/trips`: public pinned trips. Optional `bbox=west,south,east,north`, `q`, and `trip` filters. Supports bounds crossing the antimeridian. Reads public captions only, never private story edits or notes. Returns `has_more` when more than 200 matches exist.
- `GET /api/map/config`: configurable tile URL and attribution.
- `GET /api/places/search?q=...`: sign-in required, explicit Photon search. No autocomplete or batch geocoding.
- `PUT /api/feeds/ID/details`: owner-only atomic story and destination update. `location` is either `null` (remove), or `{lat,lng,label,provider,source,place_id}`. Omitting it preserves an existing pin for old clients. Coordinates must be finite, numeric, and in range; labels are limited to 240 characters. The canonical destination text follows the selected pin.
- Collection imports accept the same `location` object on each group and create it in the same transaction as that trip.

Code is isolated in `backend/trip_locations.py`, `map-core.js`, `destination-picker.js/.css`, and `travel-map.js/.css`; the map page is `map.html`. The shared map runtime loads Leaflet 1.9.4 with the official integrity hashes. Place search is proxied through the local backend, so the provider does not receive account cookies, videos, or user IDs.

## No-cost local testing and service limits

The default integration requires no account, API key, subscription, or paid API. It uses browser-rendered [OpenStreetMap tiles](https://operations.osmfoundation.org/policies/tiles/) and the [Photon public demo service](https://github.com/komoot/photon#demo-server). These are best-effort community resources, not unlimited production infrastructure. Photon permits reasonable project use and may throttle/ban extensive use or change its service. Search is explicit only, authenticated, globally limited to one upstream request per 1.1 seconds in this single local server process, and cached for 30 days (up to 1,000 entries). Offline/upstream failures leave manual pin and coordinate entry available. Do not enter private addresses or confidential queries.

Map tiles are requested only for the visible interactive map, use normal browser HTTP caching, carry the browser referrer, and display OpenStreetMap attribution. They are never bulk downloaded, precached by the app service worker, or offered offline. Do not add offline city downloads or automated tile scans against the community tile server.

To switch providers without changing application code, configure `SERENITY_MAP_TILE_URL` and `SERENITY_MAP_ATTRIBUTION` on the server. `SERENITY_PHOTON_URL` can point to a compatible HTTPS Photon instance. The default is `https://photon.komoot.io/api/`. An invalid/unconfigured search endpoint fails safely. A public, larger-scale deployment must choose appropriately licensed tile and geocoding capacity or self-host them, review current provider policies, and coordinate rate limits across processes. No public deployment or billable resource is created by this change. The public Nominatim API is not used.

## Verification

`python3 backend/test_server.py` includes map storage, import pin persistence, authorization, public/private filtering, missing locations, invalid/NaN coordinates, bounds validation and antimeridian queries, removed trip fields, provider parsing, cached searches, rate limiting, and upstream failure fallback. Feed interaction tests check the new visit/map panel alongside the existing swipe/keyboard/playback behavior. Browser QA uses a separate temporary database with clearly labelled sample footage; it does not pin or publish any real user trip.

Edge browser QA verified the Map toolbar state, world map with two public destinations (excluding an unpinned private trip), selecting a trip, preview playback, opening its trip page, and the correct Google Maps destination link. It also verified live Photon search, explicitly choosing a result, saving its exact coordinates in Clip Studio, and the private-pin indicator. The saved browser-selected destination was then published through the same visibility API and retrieved from Map with identical coordinates. `node backend/test_destination_picker.js` covers preserving legacy destination text, explicit search/selection, valid zero coordinates, invalid bounds, and explicit removal.
