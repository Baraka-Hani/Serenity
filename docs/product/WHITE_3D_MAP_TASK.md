# White 3D travel map

Risk: medium — new browser map rendering and authenticated private location storage.

## Acceptance criteria

- Map feed has a white, quiet interface with restrained warm accents.
- Users can rotate, tilt and zoom a globe with real elevation data and imagery.
- Optional birds and planes animate geographically; they are ambient illustrations, not live tracking.
- Signed-in users can explicitly save and remove visited places, independently of public posts.
- A distinct-place count persists per account; duplicates do not increase it.
- Other users and anonymous discovery cannot read private travel history.
- Published trip discovery, previews and directions remain available when WebGL or external map data fails.
- Keyboard, mobile and reduced-motion use remain supported.
- No paid accounts, infrastructure, production data edits, publishing or default-branch push.

## Implementation and verification

Isolated branch: `feat/white-3d-travel-map`. All acceptance criteria above are
implemented. Independent review: [approve](WHITE_3D_MAP_REVIEW.md).

### Changed files

- `map.html`, `travel-map.css`, `travel-map.js`: white map feed, discover/journal
  views, visit form, counter, private detail/draft cleanup and guarded responses.
- `map-world.js`: MapLibre globe, satellite/Streets, natural-scale elevation,
  buildings, spin/rotation/tilt, optional ambient animations and failure handling.
- `backend/visited_locations.py`, `backend/server.py`, `backend/trip_locations.py`:
  private owner-scoped saved history and configurable 3D source metadata.
- `app-client.js`, `service-worker.js`: history API methods and shell revision;
  private APIs and third-party map data remain excluded from caches.
- `backend/test_server.py`, `backend/test_travel_map_browser.js`: history and
  browser regressions; `backend/MAPS.md` documents data, providers and semantics.
- This task and the independent reviewer record.
- `.github/workflows/ci.yml`: corrected one existing unindented test command
  that prevented the verification workflow from parsing; commands are unchanged.

### Verification

- `python3 backend/test_server.py`: **24 passed**.
- `python3 backend/test_messaging.py`: **6 passed**.
- `python3 backend/test_account_discovery.py`: **4 passed**.
- Existing Node destination-picker, feed-hub, chat, studio-grouping and
  studio-publication tests: **all passed**.
- `node backend/test_travel_map_browser.js`: **passed**. All API responses are
  synthetic/intercepted; checks mobile visibility, identity failure, account
  switching, late-save isolation, failure notices and WebGL fallback.
- JavaScript syntax, Python compilation and `git diff --check`: **passed**.
- CI YAML parsing with Ruby's YAML parser: **passed** after the indentation repair.
- Headless Chrome against a separate local-only temporary database verified a
  rendered globe, real Swiss Alps terrain, creating/restoring a private place
  with date/note after reload, counter persistence, mobile layout without
  horizontal overflow, and reduced-motion spin disabling. Final run had **zero
  page JavaScript errors**. Normal tile-request cancellations occur during
  camera movements. A missing favicon returned 404; it does not affect the app.
- Downloaded pinned MapLibre 5.15.0 assets independently match runtime SRI.
- React/Firebase prototype build: **not applicable; no prototype files changed**.

The provided workspace path was unavailable; implementation and local preview
use a temporary checkout at `/private/tmp/serenity-map-feed`. Node/Playwright
were supplied by the existing local app runtime; no package/service was installed.
Browser checks use existing Chrome, not the user's browser profile.

### Limitations and cost/security impact

Satellite imagery is the explicitly disclosed **2016** free-license vintage.
Terrain and building detail depend on provider coverage; missing building heights
use an illustrative 3 m height. Ambient SVG aircraft/birds are not live tracking
or full 3D object/altitude simulation. Counts mean distinct coordinate cells
(approximately 11 m), not cities/countries or verified physical visits. WebGL
and network access are needed for the globe; lists, links and manual journal
entry work without it.

No paid resources, credentials, accounts, infrastructure, production-data writes,
default-branch push, merge or deployment were performed. Default map endpoints
are publicly accessible best-effort services. Private history is authenticated,
owner-scoped and never included in public APIs or browser storage.

### Rollback

Revert the feature commit to restore the prior map/client/server/service-worker
code. Keep the unused `visited_locations` table so saved history is not destroyed.
No existing trip data needs conversion or deletion. Merge/deployment remain for
the human owner to approve under `AGENTS.md`.
