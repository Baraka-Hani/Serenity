# White 3D map review

Recommendation: **approve** the isolated branch change. No unresolved blocking
findings remain in the reviewed implementation. Merge, public deployment and
production data changes remain subject to the human approval rule in `AGENTS.md`.

Reviewed: `feat/white-3d-travel-map`, 2026-11-16. This is an independent Reviewer
inspection of the Builder's uncommitted diff and new files; no implementation
changes were made by the Reviewer.

## Findings resolved during review

- **P1 — map container collapsed after library CSS loaded.** MapLibre's late
  `.maplibregl-map { position: relative }` overrode the page's positioning. The
  more specific `.map-stage .travel-map` rule now preserves the map dimensions;
  interface overlays use an explicit higher stacking order. Inspected the
  updated globe and Alps screenshots: both display real map content.
- **P2 — private UI survived failed identity refresh/account switches.**
  `clearPrivateView` now closes and empties the detail panel, closes/resets the
  visited-place dialog, clears candidates/results and cancels pin selection.
  Independently verified with synthetic account responses in headless Chrome.
- **P2 — late saved-place responses could revive another account's place.**
  Save/remove completions now check the originating account and identity
  generation before writing UI state, including after subsequent reads.
  Independently reproduced the timing with an intercepted, delayed account A
  PUT released after account B loaded: B retained zero places and an empty list.
- **P2 — mobile selection opened an offscreen preview.** Narrow layouts now
  scroll the map stage into view. Independently verified at 390 × 844: the
  selected preview appeared at the top of the viewport.
- **P3 — opening the visit dialog erased map failure messages.** Persistent
  renderer/data warnings are now separate from temporary pin-selection prompts.

## Independent verification

- `python3 backend/test_server.py`: **24 tests passed** against its isolated
  temporary database and loopback server. Includes private history isolation,
  save/delete ownership, duplicate/concurrent writes, restart persistence,
  validation, pagination and antimeridian/polar identity handling.
- `node backend/test_destination_picker.js`: **passed**.
- `node backend/test_feed_hub.js`: **passed**.
- Node syntax checks for `map-world.js` and `travel-map.js`: **passed**.
- Python compilation for `backend/visited_locations.py`, `backend/server.py`
  and `backend/trip_locations.py`: **passed**, with the bytecode cache redirected
  to `/private/tmp`. The first default-cache attempt was denied by the sandbox;
  no source error occurred.
- `git diff --check`: **passed**.
- `node backend/test_travel_map_browser.js`: **passed independently** using
  `SERENITY_TEST_URL=http://127.0.0.1:18785` and the existing Playwright/Chrome
  installations selected through its documented environment variables. Reviewed
  the test: unmatched API requests and external HTTPS requests are blocked,
  service workers are disabled, and all account/place responses are synthetic.
- HTML IDs: no duplicates or unmatched simple map-controller selectors.
- Independently computed SHA-384 digests of the downloaded pinned MapLibre
  **5.15.0** JS/CSS assets: both match the committed runtime integrity values.
- Disposable headless Chrome with synthetic intercepted responses verified:
  public trip/watch/directions remain accessible without WebGL; selecting a
  public trip prefills its exact coordinates in the visit form; account-switch
  draft clearing; identity-failure private-detail clearing; mobile preview
  visibility; delayed-save response isolation. These checks do not use real
  accounts or the user's data.

The live globe/Alps screenshots were inspected independently. Live tile fetches,
terrain interaction, resizing, and reduced-motion runtime checks were performed
by the Builder; the Reviewer did not rerun every external-provider interaction.
The separate React/Firebase prototype was not changed and its build was not run
as part of this review.

Final follow-up inspection included the viewport-based `homeZoom` calculation,
escaped custom imagery/elevation attribution overrides, expanded map-source
documentation and the unchanged account/identity guards. No additional findings.
The final backend suite rerun and browser regression passed after these changes.

## Boundaries and limitations

- The existing Python/SQLite and plain JavaScript PWA boundaries are preserved.
- Visit data is authenticated and owner-scoped, excluded from public discovery,
  served with the existing no-store policy, and never added to service-worker
  caches. Database writes are parameterized; mutations retain origin checks.
- A distinct place means a rounded coordinate cell, approximately 11 m at the
  equator, rather than a city/country count. Duplicate saves preserve the first
  saved visit date and note.
- Satellite imagery is the disclosed 2016 vintage; elevations and building
  heights depend on source coverage. Birds/planes are ambient illustrations,
  not current aircraft/wildlife observations.
- External CDN/map data is best-effort and needs a connection. This change
  creates no paid resources, credentials, hosting or public deployment.
- Rollback restores the previous map/client/server/service-worker code. Retain
  the unused private-history table and its data rather than deleting production
  records during a code rollback.
