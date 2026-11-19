/* Published destination discovery and an account-private travel journal. */
(() => {
  const $ = selector => document.querySelector(selector), api = window.RoamApp;
  const node = (tag, className = '', text) => { const element = document.createElement(tag); element.className = className; if (text !== undefined) element.textContent = text; return element; };
  let world, trips = [], visits = [], total = null, user = null, journal = false, selected, detailTrigger, mapWarning = '';
  let tripRequest = 0, visitRequest = 0, accountRequest = 0, searchRequest = 0, identityVersion = 0, tripController, placeController, candidate, picking = false, loadingWorld = false;
  const mapButtons = ['mapRefresh', 'mapSatellite', 'mapStreets', 'mapSpin', 'mapRotateLeft', 'mapRotateRight', 'mapTilt', 'mapReset', 'mapAlps', 'mapDropPin'];
  function displayNotice(message) { $('#mapNotice').textContent = message; $('#mapNotice').hidden = !message; }
  function notice(message) { mapWarning = message; if (!picking) displayNotice(message); }
  function closeDetail(restoreFocus = true) {
    $('#mapDetail').querySelector('video')?.pause(); $('#mapDetail').hidden = true; selected = null;
    document.querySelectorAll('.map-place-button').forEach(button => { button.classList.remove('is-selected'); button.setAttribute('aria-pressed', 'false'); });
    if (restoreFocus && detailTrigger?.isConnected) detailTrigger.focus();
  }
  function renderMarkers() {
    world?.setMarkers(journal ? visits.map(place => ({ ...place, key: `visit:${place.id}`, visited: true })) : trips.map(trip => ({ ...trip, key: `trip:${trip.id}`, visited: false })), place => showDetail(place, place.visited));
  }
  function listButton(place, visited) {
    const button = node('button', 'map-place-button'); button.type = 'button'; button.dataset.key = `${visited ? 'visit' : 'trip'}:${place.id}`;
    button.setAttribute('aria-pressed', String(selected === button.dataset.key)); button.classList.toggle('is-selected', selected === button.dataset.key);
    const copy = node('span', 'map-place-copy');
    copy.append(node('strong', '', visited ? place.label : place.name), node('small', '', visited ? place.visited_on ? `Visited ${place.visited_on}` : 'A memory on your map' : `${place.label} · ${place.video_count} ${place.video_count === 1 ? 'video' : 'videos'}`));
    button.append(node('span', 'map-place-icon', visited ? '✓' : '⌖'), copy);
    button.onclick = () => { showDetail(place, visited, button); world?.focus(place); };
    return button;
  }
  function renderVisits() {
    $('#mapVisitCount').textContent = total === null ? '—' : total.toLocaleString(); $('#mapVisitLabel').textContent = total === 1 ? 'place visited' : 'places visited';
    $('#mapVisits').replaceChildren(...visits.map(place => listButton(place, true))); $('#mapSignIn').hidden = Boolean(user);
    renderMarkers();
  }
  function switchView(value) {
    journal = value; closeDetail(false);
    $('#mapExploreTab').setAttribute('aria-pressed', String(!value)); $('#mapVisitedTab').setAttribute('aria-pressed', String(value));
    $('#mapDiscoverPanel').hidden = value; $('#mapJournalPanel').hidden = !value;
    renderMarkers();
  }
  function showDetail(place, visited = false, trigger = document.activeElement) {
    closeDetail(false); detailTrigger = trigger; selected = `${visited ? 'visit' : 'trip'}:${place.id}`;
    const detail = $('#mapDetail'); detail.replaceChildren(); detail.hidden = false;
    const close = node('button', 'map-detail-close', '×'); close.type = 'button'; close.setAttribute('aria-label', 'Close place preview'); close.onclick = () => closeDetail(); detail.append(close);
    if (!visited) {
      const video = node('video'); video.controls = true; video.playsInline = true; video.preload = 'none'; video.src = api.postVideoUrl(place.preview_post_id); video.setAttribute('aria-label', `Published preview of ${place.name}`); detail.append(video);
    }
    detail.append(node('span', 'map-eyebrow', visited ? 'A place in your story' : 'Through a traveller’s lens'), node('h2', '', visited ? place.label : place.name));
    if (visited) {
      if (place.visited_on) detail.append(node('p', '', `Visited ${place.visited_on}`));
      if (place.note) detail.append(node('p', '', place.note));
      detail.append(node('small', '', 'Saved in your private travel journal. Only you can see this place.'));
    } else {
      const creator = node('a', '', `By ${place.creator_name} · @${place.creator_username}`); creator.href = `profile.html?id=${encodeURIComponent(place.creator_public_id)}`;
      detail.append(creator, node('p', '', place.label), node('p', '', place.summary), node('small', '', 'Creator-chosen destination. Check access and conditions before travelling.'));
    }
    const actions = node('div', 'map-detail-actions');
    const directions = node('a', '', 'Get directions ↗'); directions.href = window.SerenityMaps.directions(place); directions.target = '_blank'; directions.rel = 'noopener';
    if (!visited) { const watch = node('a', '', `Watch ${place.video_count} ${place.video_count === 1 ? 'video' : 'videos'} ↗`); watch.href = `feed.html?feed=${place.id}`; actions.append(watch); }
    actions.append(directions);
    const action = node('button', 'map-save-place', visited ? 'Remove from my places' : '✓ I’ve been here'); action.type = 'button';
    action.onclick = async () => {
      if (!visited) { openVisit(place); return; }
      const owner = user?.id, identity = identityVersion;
      const current = () => user?.id === owner && identityVersion === identity;
      action.disabled = true;
      try {
        const data = await api.removeVisitedPlace(place.id); if (!current()) return;
        total = data.total; visits = visits.filter(item => item.id !== place.id); renderVisits(); closeDetail(false); await loadVisits();
        if (!current()) return;
        $('#mapJournalStatus').textContent = 'Place removed from your journal.';
      } catch (error) { if (current()) { action.disabled = false; action.textContent = 'Try removing again'; notice(error.message); } }
    };
    actions.append(action); detail.append(actions);
    document.querySelectorAll('.map-place-button').forEach(button => { const active = button.dataset.key === selected; button.classList.toggle('is-selected', active); button.setAttribute('aria-pressed', String(active)); });
    detail.focus({ preventScroll: true });
    if (window.matchMedia('(max-width: 760px)').matches) $('.map-stage').scrollIntoView({ block: 'start', behavior: 'instant' });
  }
  async function loadTrips({ worldwide = false, trip } = {}) {
    const request = ++tripRequest; tripController?.abort(); tripController = new AbortController();
    const query = new URLSearchParams(), text = $('#mapQuery').value.trim();
    if (text) query.set('q', text); if (trip) query.set('trip', trip);
    if (world && !worldwide && !text && !trip && world.map.getZoom() >= 4) {
      const bounds = world.map.getBounds(), west = bounds.getWest(), east = bounds.getEast(), wrap = number => ((number + 180) % 360 + 360) % 360 - 180;
      query.set('bbox', `${east - west >= 360 ? -180 : wrap(west)},${Math.max(-90, bounds.getSouth())},${east - west >= 360 ? 180 : wrap(east)},${Math.min(90, bounds.getNorth())}`);
    }
    $('#mapStatus').textContent = 'Finding published journeys…';
    try {
      const response = await fetch(`/api/map/trips?${query}`, { signal: tripController.signal, cache: 'no-store' }), data = await response.json();
      if (!response.ok) throw new Error(data.error || 'Trips could not load.'); if (request !== tripRequest) return;
      trips = data.trips;
      if (selected?.startsWith('trip:') && !trips.some(place => selected === `trip:${place.id}`)) closeDetail(false);
      $('#mapTrips').replaceChildren(...trips.map(place => listButton(place, false))); renderMarkers();
      $('#mapStatus').textContent = trips.length ? `${trips.length} published ${trips.length === 1 ? 'journey' : 'journeys'}${data.has_more ? ' · Search or zoom in to find more' : ' to discover'}` : 'No published journeys here yet. Try another destination or add a place to your own journal.';
      if (trip && trips.length) { showDetail(trips[0]); world?.focus(trips[0]); }
    } catch (error) { if (request === tripRequest && error.name !== 'AbortError') $('#mapStatus').textContent = error.message; }
  }
  async function loadVisits(more = false) {
    const request = ++visitRequest, owner = user?.id;
    if (!owner) { visits = []; total = null; $('#mapMoreVisits').hidden = true; $('#mapJournalStatus').textContent = 'Your next chapter starts with a place.'; renderVisits(); return; }
    $('#mapJournalStatus').textContent = 'Opening your travel journal…';
    $('#mapMoreVisits').disabled = true;
    try {
      const data = await api.visitedPlaces(more ? visits.length : 0); if (request !== visitRequest || user?.id !== owner) return;
      visits = more ? [...new Map([...visits, ...data.locations].map(place => [place.id, place])).values()] : data.locations; total = data.total;
      $('#mapMoreVisits').hidden = !data.has_more; $('#mapJournalStatus').textContent = total ? `${total} ${total === 1 ? 'place' : 'places'} in your story${data.has_more ? ` · Showing ${visits.length}` : ''}.` : 'Your map is a blank page. Add your first visited place.';
      renderVisits();
    } catch (error) { if (request === visitRequest) $('#mapJournalStatus').textContent = `${error.message} Your places will appear when the connection returns.`; }
    finally { if (request === visitRequest) $('#mapMoreVisits').disabled = false; }
  }
  async function refreshAccount() {
    const request = ++accountRequest;
    try {
      const account = await api.me(); if (request !== accountRequest) return;
      if (account?.id !== user?.id) { clearPrivateView(); visits = []; total = null; ++visitRequest; }
      user = account; renderVisits(); await loadVisits();
    } catch (_) {
      if (request !== accountRequest) return;
      clearPrivateView(); user = null; visits = []; total = null; ++visitRequest; renderVisits();
      $('#mapJournalStatus').textContent = 'Connect to the app to open your private travel journal.';
    }
  }
  function clearPrivateView() {
    ++identityVersion;
    closeDetail(false); $('#mapDetail').replaceChildren();
    $('#mapVisitDialog').close(); $('#mapVisitForm').reset(); setCandidate(null); $('#mapPlaceResults').replaceChildren();
    $('#mapVisitStatus').textContent = ''; $('#mapVisitSave').disabled = false; cancelPicking();
  }
  function setCandidate(place) {
    candidate = place ? { lat: place.lat, lng: place.lng, label: place.label, provider: place.provider || 'manual', source: place.source === 'place' ? 'place' : 'pin', place_id: place.place_id || '' } : null;
    $('#mapPlaceLabel').value = candidate?.label || ''; $('#mapPlaceLat').value = candidate ? candidate.lat : ''; $('#mapPlaceLng').value = candidate ? candidate.lng : '';
  }
  function openVisit(place) {
    cancelPicking(); $('#mapVisitForm').reset(); setCandidate(place); $('#mapPlaceResults').replaceChildren();
    $('#mapVisitAuth').hidden = Boolean(user); $('#mapVisitForm').hidden = !user;
    $('#mapVisitStatus').textContent = place ? 'This place will be saved privately to your journal.' : 'Choose a search result, drop a pin, or enter a name and coordinates.';
    if (!$('#mapVisitDialog').open) $('#mapVisitDialog').showModal();
  }
  function cancelPicking() { picking = false; $('.map-stage').classList.remove('is-picking'); displayNotice(mapWarning); }
  async function searchPlaces() {
    const text = $('#mapPlaceQuery').value.trim();
    if (text.length < 2) { $('#mapVisitStatus').textContent = 'Enter at least two characters to search.'; return; }
    const request = ++searchRequest; placeController?.abort(); placeController = new AbortController();
    $('#mapPlaceSearch').disabled = true; $('#mapPlaceResults').replaceChildren(); $('#mapVisitStatus').textContent = 'Looking for that somewhere…';
    try {
      const response = await fetch(`/api/places/search?${new URLSearchParams({ q: text })}`, { signal: placeController.signal, cache: 'no-store' }), data = await response.json();
      if (!response.ok) throw new Error(data.error || 'Place search is unavailable.'); if (request !== searchRequest) return;
      for (const place of data.places) {
        const button = node('button', '', place.label); button.type = 'button'; button.onclick = () => { setCandidate(place); world?.focus(place); $('#mapPlaceResults').replaceChildren(); $('#mapVisitStatus').textContent = `${place.label} selected.`; }; $('#mapPlaceResults').append(button);
      }
      $('#mapVisitStatus').textContent = data.places.length ? 'Choose a result. Search uses OpenStreetMap data via Photon.' : 'No places found. Try another name, drop a pin, or enter coordinates.';
    } catch (error) { if (request === searchRequest && error.name !== 'AbortError') $('#mapVisitStatus').textContent = `${error.message} You can enter coordinates instead.`; }
    finally { if (request === searchRequest) $('#mapPlaceSearch').disabled = false; }
  }
  $('#mapVisitForm').onsubmit = async event => {
    event.preventDefault(); if (!user) return;
    const owner = user.id, identity = identityVersion;
    const current = () => user?.id === owner && identityVersion === identity;
    const lat = Number($('#mapPlaceLat').value), lng = Number($('#mapPlaceLng').value), label = $('#mapPlaceLabel').value.trim();
    if (!label || !Number.isFinite(lat) || !Number.isFinite(lng) || Math.abs(lat) > 90 || Math.abs(lng) > 180) { $('#mapVisitStatus').textContent = 'Choose a named place with valid latitude and longitude.'; return; }
    const location = candidate && candidate.lat === lat && candidate.lng === lng && candidate.label === label ? candidate : { lat, lng, label, provider: 'manual', source: 'pin', place_id: '' };
    $('#mapVisitSave').disabled = true;
    try {
      const data = await api.saveVisitedPlace(location, $('#mapVisitedOn').value, $('#mapVisitNote').value);
      if (!current()) return;
      total = data.total; visits = [data.location, ...visits.filter(item => item.id !== data.location.id)]; renderVisits();
      $('#mapVisitDialog').close(); closeDetail(false); switchView(true); await loadVisits();
      if (!current()) return;
      $('#mapJournalStatus').textContent = data.created ? `${label} added. Another memory on your map.` : 'This place is already in your journal. Each place is counted once.';
      world?.focus(location); $('#mapVisitedTab').focus({ preventScroll: true });
    } catch (error) { if (current()) $('#mapVisitStatus').textContent = error.message; }
    finally { if (current()) $('#mapVisitSave').disabled = false; }
  };
  $('#mapPlaceSearch').onclick = searchPlaces;
  $('#mapPlaceQuery').onkeydown = event => { if (event.key === 'Enter') { event.preventDefault(); searchPlaces(); } };
  $('#mapVisitClose').onclick = () => $('#mapVisitDialog').close();
  $('#mapVisitDialog').addEventListener('close', () => { ++searchRequest; placeController?.abort(); $('#mapPlaceSearch').disabled = false; });
  $('#mapRecordPlace').onclick = () => openVisit(); $('#mapAddVisit').onclick = () => openVisit();
  $('#mapDropPin').onclick = () => { $('#mapVisitDialog').close(); closeDetail(false); picking = true; $('.map-stage').classList.add('is-picking'); displayNotice('Choose a point on the map. Press Escape to cancel. You can also enter coordinates in Add a place.'); world?.map.getCanvas().focus(); };
  $('#mapExploreTab').onclick = () => switchView(false); $('#mapVisitedTab').onclick = $('#mapJournalShortcut').onclick = () => switchView(true);
  $('#mapMoreVisits').onclick = () => loadVisits(true);
  $('#mapSearch').onsubmit = event => { event.preventDefault(); closeDetail(false); loadTrips({ worldwide: true }); };
  $('#mapWorld').onclick = () => { $('#mapQuery').value = ''; closeDetail(false); world?.world(); loadTrips({ worldwide: true }); };
  $('#mapRefresh').onclick = () => { $('#mapQuery').value = ''; loadTrips(); };
  $('#mapSatellite').onclick = () => setStreets(false); $('#mapStreets').onclick = () => setStreets(true);
  function setStreets(value) { world?.setStreets(value); $('#mapStreets').setAttribute('aria-pressed', String(value)); $('#mapSatellite').setAttribute('aria-pressed', String(!value)); }
  $('#mapSpin').onclick = () => world?.setSpin($('#mapSpin').getAttribute('aria-pressed') !== 'true');
  $('#mapRotateLeft').onclick = () => world?.rotate(-30); $('#mapRotateRight').onclick = () => world?.rotate(30); $('#mapTilt').onclick = () => world?.tilt(); $('#mapReset').onclick = () => world?.world();
  $('#mapAlps').onclick = () => world?.focus({ lat: 46.58, lng: 7.98 });
  const motion = window.matchMedia('(prefers-reduced-motion: reduce)');
  function updateMotion() { $('#mapMotionNotice').hidden = !motion.matches; $('#mapSpin').disabled = !world || motion.matches; $('#mapAmbient').disabled = motion.matches; }
  motion.addEventListener('change', updateMotion); updateMotion();
  $('#mapAmbient').onchange = () => world?.setAmbient($('#mapAmbient').checked);
  document.addEventListener('keydown', event => { if (event.key === 'Escape') { if (picking) cancelPicking(); else if (!$('#mapVisitDialog').open) closeDetail(); } });
  document.addEventListener('visibilitychange', () => { if (document.hidden) $('#mapDetail video')?.pause(); else { refreshAccount(); loadTrips({ worldwide: true }); } });
  async function startWorld() {
    if (loadingWorld) return; loadingWorld = true; $('#mapRetry').hidden = true; notice('');
    try {
      world?.destroy(); world = null;
      world = await window.SerenityWorld.create($('#travelMap'), { onNotice: notice, onSpinChange: spinning => $('#mapSpin').setAttribute('aria-pressed', String(spinning)) });
      mapButtons.forEach(id => { $(`#${id}`).disabled = false; }); updateMotion();
      world.setAmbient($('#mapAmbient').checked); setStreets($('#mapStreets').getAttribute('aria-pressed') === 'true'); renderMarkers();
      world.map.on('click', event => {
        if (!picking || event.originalEvent?.target?.closest('.world-pin')) return;
        const lng = ((event.lngLat.lng + 180) % 360 + 360) % 360 - 180;
        openVisit({ lat: Number(event.lngLat.lat.toFixed(7)), lng: Number(lng.toFixed(7)), label: '', provider: 'manual', source: 'pin' }); $('#mapPlaceLabel').focus();
      });
      const requested = new URLSearchParams(location.search).get('trip'); if (requested && trips.length) world.focus(trips[0]);
    } catch (error) { mapButtons.forEach(id => { $(`#${id}`).disabled = true; }); notice(error.message); $('#mapRetry').hidden = false; }
    finally { loadingWorld = false; }
  }
  $('#mapRetry').onclick = startWorld;
  loadTrips({ worldwide: true, trip: new URLSearchParams(location.search).get('trip') }); refreshAccount(); startWorld();
})();
