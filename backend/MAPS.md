# Travel discovery maps

Serenity is a watch → find the place → travel there product, not a live friend-location service. `/map.html` is a fifth toolbar destination. It displays only trips that have both a saved destination pin and at least one public video. Private trips, private clips, unpublished notes, emails, and unpinned legacy destinations never appear in its API. There is no device geolocation or live tracking. Video location metadata is read only when the app owner runs the local, opt-in tool described in **Pins from video location data** below.

## Creator workflow

Clip Studio's manual form, saved-trip editor, and categorized collection review use the shared destination picker. Search for a public city/landmark and explicitly select a result; alternatively open the map and click a point, or enter a name and latitude/longitude with the keyboard. Search text alone is not a pin. Stored values are numeric coordinates, a readable place label, provider/source, and an optional provider reference. Creator-selected coordinates are not verified GPS evidence that a clip was filmed there.

Pins on published trips are public, as explained beside the field. Editing the destination of an already-public trip changes its map location and published destination labels. Removing its pin removes the trip from Map but does not unpublish its Feed videos. Making all videos private removes the trip from Map; its saved private pin is retained for the owner. Existing published trips without coordinates remain on Feed until the creator chooses **Add destination pin for Map** on their preview.

Dates and highlights are retired from trip forms and `/api/feeds/ID/details` responses. New writes ignore those legacy fields, and new posts no longer append them. SQLite's old columns and existing historical caption text are retained for backwards compatibility/data preservation; no old caption is automatically rewritten or personal data erased. A trip now consists of a name, an experience/story, an optional destination pin, and videos. Private planning notes remain separate from published travel information.

## Pins from video location data

Phones record where a video was filmed (ISO 6709, e.g. `+35.0116+135.7681/`). The owner can turn that into
Map pins for existing trips with a local command; it never runs inside the web app or on upload:

```bash
python3 backend/video_locations.py
python3 backend/video_locations.py --source-root '/path/to/Photos Library.photoslibrary/originals'
python3 backend/video_locations.py --apply
```

- The first command is a dry run: it lists, per trip, how many clips carry GPS and the proposed pin. Nothing is written.
- `--source-root` also reads the original files of demo clips created by `seed_demo.py`, in case conversion dropped the metadata.
- `--apply` saves pins only for trips without one (creator pins are kept unless `--replace`) after a private SQLite backup.
- One pin per trip: the clip location closest to all the others, so one stray clip cannot move it. Trips whose clips span more than 50 km are flagged.
- Coordinates are rounded to `--precision` decimals (default 2, about 1 km) so an exact spot such as a home is never published. Labels read "Filmed near 35.01°N, 135.77°E" unless `--reverse-geocode` is given, which sends the rounded coordinates to the configured Photon server to name the place.
- These pins are stored with source `video`. Map and the Feed travel panel describe them as approximate spots from the videos' location data. Clients cannot mark their own pins as `video`; moving such a pin in Clip Studio turns it into an ordinary creator pin.
- As with every pin, it appears on Map only while the trip has public videos.

## Your 3D world and private travel journal

The map feed uses a white interface with restrained warm accents. MapLibre GL JS
5.15.0 renders a globe that can be dragged, rotated, tilted, spun, and zoomed into
real terrain. Library CSS and JavaScript are version-pinned with SHA-384
integrity. The Clip Studio destination picker continues using Leaflet; the React
prototype is unchanged.

The default satellite layer is **EOxCloudless 2016** (the CC BY 4.0 vintage),
not recent/live imagery. Elevation uses Mapzen Terrarium tiles from AWS Open
Data at natural scale (1×). OpenFreeMap's OpenMapTiles building footprints render
as extrusions from zoom 14; available heights vary and missing heights use a
3 m illustration. This is terrain and building visualization, not photogrammetry,
surveying, or a navigation-grade height model. Streets can be selected separately.
The mountain preview demonstrates terrain in the Swiss Alps. Globe framing adapts
to the available viewport.

Birds and planes are optional, geographically anchored SVG animations. Aircraft
follow illustrative great-circle routes; birds appear at close zoom. They are
ambient artwork, not actual aircraft or wildlife observations or altitude models.
Animations stop in hidden tabs and respect reduced motion. Users can also turn
them off in Scene settings. Spin is explicit and stops when the user interacts.

**My places** is separate from public posts. Signed-in users explicitly add a
visited destination from a public trip, a place-search result, a clicked pin, or
manual name/coordinates. A visit may include a date and up to 1,000 characters
of private notes. History persists in SQLite per account, without localStorage,
and never appears in map discovery or public profiles. Saving a place does not
publish anything. Removing a saved place updates its count without deleting trips.

The counter represents distinct **saved coordinate cells**, rounded to four
decimal places (about 11 m north/south), not countries or independently verified
visits. Duplicate saves retain the first saved name, date, and note and do not
inflate the count. Pins on opposite sides of the antimeridian and longitude
variants at a pole share identity. Adjacent cells can still represent different
pins within the same named city. History loads in pages of 100, while the count
always covers all saved places.

Private details, drafts and markers are cleared if the account changes or cannot
be verified; stale asynchronous responses cannot revive a prior account's data.
If WebGL, library loading, or map providers fail, public trip lists, previews,
directions, journal history, and manual coordinate entry still work. Offline
terrain and imagery are not supplied.

## Viewing public destinations

Map can be browsed without an account. Pan/zoom, search published trip/place names, choose a marker or accessible trip-list button, watch its public preview, open the trip's videos, and open **Get directions**. Trips at the same point remain individually selectable in the list. A maximum of 200 trips is returned per request; zoom and choose **Search this area**, or search to narrow large result sets. Trip pages and the Feed travel panel also link to the saved destination and directions. Directions open Google Maps URLs with only the selected destination coordinates; no origin or user GPS is collected by Serenity and no Maps API key is needed.

## APIs and modules

- `GET /api/map/trips`: public pinned trips. Optional `bbox=west,south,east,north`, `q`, and `trip` filters. Supports bounds crossing the antimeridian. Reads public captions only, never private story edits or notes. Returns `has_more` when more than 200 matches exist.
- `GET /api/map/config`: configurable tile URL and attribution.
- `GET /api/map/visits?offset=0`: authenticated owner's private history (100 per page), total count, and `has_more`.
- `PUT /api/map/visits`: authenticated, same-origin idempotent save with `{location,visited_on?,note?}`; creates a new place or returns the existing one unchanged.
- `DELETE /api/map/visits/ID`: authenticated, same-origin owner-only removal. Another account's IDs return 404.
- `GET /api/places/search?q=...`: sign-in required, explicit Photon search. No autocomplete or batch geocoding.
- `PUT /api/feeds/ID/details`: owner-only atomic story and destination update. `location` is either `null` (remove), or `{lat,lng,label,provider,source,place_id}`. Omitting it preserves an existing pin for old clients. Coordinates must be finite, numeric, and in range; labels are limited to 240 characters. The canonical destination text follows the selected pin.
- Collection imports accept the same `location` object on each group and create it in the same transaction as that trip.

Code is isolated in `backend/trip_locations.py`, `backend/visited_locations.py`,
`map-world.js`, `map-core.js`, `destination-picker.js/.css`, and `travel-map.js/.css`;
the map page is `map.html`. The shared destination-picker runtime loads Leaflet
1.9.4 with the official integrity hashes. Place search is proxied through the local
backend, so the provider does not receive account cookies, videos, or user IDs.

## No-cost local testing and service limits

The default integration requires no account, API key, subscription, or paid API. It uses browser-rendered [OpenStreetMap tiles](https://operations.osmfoundation.org/policies/tiles/) and the [Photon public demo service](https://github.com/komoot/photon#demo-server). These are best-effort community resources, not unlimited production infrastructure. Photon permits reasonable project use and may throttle/ban extensive use or change its service. Search is explicit only, authenticated, globally limited to one upstream request per 1.1 seconds in this single local server process, and cached for 30 days (up to 1,000 entries). Offline/upstream failures leave manual pin and coordinate entry available. Do not enter private addresses or confidential queries.

Map tiles are requested only for the visible interactive map, use normal browser HTTP caching, carry the browser referrer, and display OpenStreetMap attribution. They are never bulk downloaded, precached by the app service worker, or offered offline. Do not add offline city downloads or automated tile scans against the community tile server.

To switch providers without changing application code, configure
`SERENITY_MAP_TILE_URL` and `SERENITY_MAP_ATTRIBUTION` for Streets. The globe also
accepts `SERENITY_MAP_IMAGERY_URL` / `SERENITY_MAP_IMAGERY_ATTRIBUTION`,
`SERENITY_MAP_TERRAIN_URL` / `SERENITY_MAP_TERRAIN_ATTRIBUTION` (256 px Terrarium,
maximum source zoom 15), and `SERENITY_MAP_BUILDINGS_URL` (OpenMapTiles TileJSON).
Default imagery is 256 px XYZ through zoom 14; preserve that source contract or
adjust `map-world.js` when changing providers. Provide accurate attribution for
custom sources. Never silently substitute later, commercially licensed EOX vintages.

`SERENITY_PHOTON_URL` can point to a compatible HTTPS Photon instance. The default
is `https://photon.komoot.io/api/`. An invalid/unconfigured search endpoint fails
safely. A public, larger-scale deployment must choose appropriately licensed tile
and geocoding capacity or self-host them, review current provider policies, and
coordinate rate limits across processes. Defaults require no account, token,
paid API, or new infrastructure; public endpoints have no availability guarantee.
No public deployment or billable resource is created by this change. The public
Nominatim API is not used.

Provider references checked for this implementation:
[MapLibre terrain](https://maplibre.org/maplibre-gl-js/docs/examples/3d-terrain/),
[Mapzen elevation](https://registry.opendata.aws/terrain-tiles/),
[EOX maps](https://maps.eox.at/),
[EOX vintage licensing](https://cloudless.eox.at/documentation/faq), and
[OpenFreeMap](https://openfreemap.org/quick_start/).

## Verification

`python3 backend/test_server.py` also verifies private history ownership,
unauthenticated and cross-origin rejection, concurrent duplicate saves, count
accuracy, validation, restart persistence, paging and antimeridian/pole identity.

`node backend/test_travel_map_browser.js` is an optional Playwright regression
check against a running local app. All APIs are intercepted with synthetic data,
and service workers are blocked; it never reads/writes real account data. It
checks WebGL fallback links and saving from trips, mobile preview visibility,
clearing private details/drafts on account changes or identity failure, retained
outage notices, and isolation of delayed save responses. `SERENITY_TEST_URL`
defaults to `http://127.0.0.1:8765`; optional `SERENITY_PLAYWRIGHT_MODULE` and
`SERENITY_BROWSER_PATH` select an existing Playwright installation/browser.

`python3 backend/test_server.py` includes map storage, import pin persistence, authorization, public/private filtering, missing locations, invalid/NaN coordinates, bounds validation and antimeridian queries, removed trip fields, provider parsing, cached searches, rate limiting, and upstream failure fallback. Feed interaction tests check the new visit/map panel alongside the existing swipe/keyboard/playback behavior. Browser QA uses a separate temporary database with clearly labelled sample footage; it does not pin or publish any real user trip.

Edge browser QA verified the Map toolbar state, world map with two public destinations (excluding an unpinned private trip), selecting a trip, preview playback, opening its trip page, and the correct Google Maps destination link. It also verified live Photon search, explicitly choosing a result, saving its exact coordinates in Clip Studio, and the private-pin indicator. The saved browser-selected destination was then published through the same visibility API and retrieved from Map with identical coordinates. `node backend/test_destination_picker.js` covers preserving legacy destination text, explicit search/selection, valid zero coordinates, invalid bounds, and explicit removal.
