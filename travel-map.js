/* Destination discovery: only public, pinned trips are returned by the server. */
(() => {
  const $ = selector => document.querySelector(selector);
  let map, L, layer, trips = [], selectedId, requestNumber = 0, timer, controller;
  const node = (tag, className, text) => { const el = document.createElement(tag); el.className = className || ''; if (text !== undefined) el.textContent = text; return el; };
  function closeDetail() {
    $('#mapDetail').querySelector('video')?.pause(); $('#mapDetail').hidden = true; selectedId = null;
    for (const button of $('#mapTrips').children) { button.classList.remove('is-selected'); button.setAttribute('aria-pressed', 'false'); }
  }
  function select(trip) {
    selectedId = trip.id;
    const detail = $('#mapDetail'); detail.querySelector('video')?.pause(); detail.replaceChildren(); detail.hidden = false;
    const close = node('button', 'map-close', '×'); close.type = 'button'; close.setAttribute('aria-label', 'Close trip preview'); close.onclick = closeDetail;
    const video = node('video'); video.controls = true; video.playsInline = true; video.preload = 'none'; video.src = window.RoamApp.postVideoUrl(trip.preview_post_id); video.setAttribute('aria-label', `Published preview of ${trip.name}`);
    const creator = node('a', '', `By ${trip.creator_name} · @${trip.creator_username}`); creator.href = `profile.html?id=${encodeURIComponent(trip.creator_public_id)}`;
    const actions = node('div', 'map-detail-actions');
    const watch = node('a', '', `Watch ${trip.video_count} ${trip.video_count === 1 ? 'video' : 'videos'} ↗`); watch.href = `feed.html?feed=${trip.id}`;
    const directions = node('a', '', 'Get directions ↗'); directions.href = window.SerenityMaps.directions(trip); directions.target = '_blank'; directions.rel = 'noopener';
    actions.append(watch, directions);
    detail.append(close, video, node('h2', '', trip.name), creator, node('p', '', trip.label), node('p', '', trip.summary), node('small', '', 'Creator-chosen destination. Check the exact place, access rules, and conditions before travelling.'), actions);
    for (const button of $('#mapTrips').children) { const active = button.dataset.trip === String(trip.id); button.classList.toggle('is-selected', active); button.setAttribute('aria-pressed', String(active)); }
  }
  function render() {
    $('#mapTrips').replaceChildren(); layer?.clearLayers();
    const clusters = new Map();
    trips.forEach((trip, index) => {
      const button = node('button', 'map-trip-button'); button.type = 'button'; button.dataset.trip = trip.id;
      button.classList.toggle('is-selected', selectedId === trip.id); button.setAttribute('aria-pressed', String(selectedId === trip.id));
      const copy = node('span', 'map-trip-copy'); copy.append(node('strong', '', trip.name), node('small', '', `${trip.label} · ${trip.video_count} ${trip.video_count === 1 ? 'video' : 'videos'}`));
      button.append(node('span', 'map-trip-number', String(index + 1)), copy);
      button.onclick = () => { select(trip); map?.setView([trip.lat, trip.lng], Math.max(map.getZoom(), 12), { animate: false }); };
      $('#mapTrips').append(button);
      if (map) {
        const point = map.project([trip.lat, trip.lng], map.getZoom()), key = `${Math.floor(point.x / 44)}:${Math.floor(point.y / 44)}`;
        if (!clusters.has(key)) clusters.set(key, []); clusters.get(key).push({ trip, index });
      }
    });
    for (const group of clusters.values()) {
      const first = group[0];
      const icon = L.divIcon({ className: 'serenity-map-marker', html: `<span>${group.length > 1 ? `${group.length} trips` : first.index + 1}</span>`, iconSize: [44, 46], iconAnchor: [22, 42] });
      const marker = L.marker([first.trip.lat, first.trip.lng], { icon, title: group.length > 1 ? `${group.length} published trips. Zoom to explore; choose a trip from the list.` : first.trip.name, keyboard: true }).addTo(layer);
      marker.on('click', () => {
        if (group.length === 1 || map.getZoom() >= 17 || group.every(item => item.trip.lat === first.trip.lat && item.trip.lng === first.trip.lng)) select(first.trip);
        else map.fitBounds(group.map(item => [item.trip.lat, item.trip.lng]), { maxZoom: 17, padding: [60, 60], animate: false });
      });
    }
  }
  async function load({ worldwide = false, trip } = {}) {
    const id = ++requestNumber; controller?.abort(); controller = new AbortController();
    const query = new URLSearchParams(), text = $('#mapQuery').value.trim();
    if (text) query.set('q', text);
    if (trip) query.set('trip', trip);
    if (map && !worldwide && !text && !trip) {
      const bounds = map.getBounds(), west = bounds.getWest(), east = bounds.getEast();
      const wrap = number => ((number + 180) % 360 + 360) % 360 - 180;
      query.set('bbox', `${east - west >= 360 ? -180 : wrap(west)},${Math.max(-90, bounds.getSouth())},${east - west >= 360 ? 180 : wrap(east)},${Math.min(90, bounds.getNorth())}`);
    }
    $('#mapStatus').textContent = 'Finding published trips…';
    try {
      const response = await fetch(`/api/map/trips?${query}`, { signal: controller.signal, cache: 'no-store' }); const data = await response.json();
      if (!response.ok) throw new Error(data.error || 'Trips could not load.');
      if (id !== requestNumber) return;
      trips = data.trips;
      if (selectedId && !trips.some(item => item.id === selectedId)) closeDetail();
      render();
      $('#mapStatus').textContent = trips.length ? `${trips.length} published ${trips.length === 1 ? 'trip' : 'trips'}${data.has_more ? ' · Zoom in to see more' : ' · Choose a pin or trip'}` : 'No pinned public trips here yet. Explore worldwide, or add a destination to your published trip in Clip Studio.';
      if ((worldwide || trip) && trips.length && map) {
        map.fitBounds(trips.map(item => [item.lat, item.lng]), { maxZoom: trip ? 13 : 7, padding: [70, 70], animate: false });
        if (trip) select(trips[0]);
      }
    } catch (error) { if (id === requestNumber && error.name !== 'AbortError') $('#mapStatus').textContent = error.message; }
  }
  $('#mapSearch').onsubmit = event => { event.preventDefault(); closeDetail(); load({ worldwide: true }); };
  $('#mapWorld').onclick = () => { $('#mapQuery').value = ''; closeDetail(); load({ worldwide: true }); };
  $('#mapRefresh').onclick = () => { $('#mapQuery').value = ''; load(); };
  document.addEventListener('keydown', event => { if (event.key === 'Escape') closeDetail(); });
  document.addEventListener('visibilitychange', () => { if (document.hidden) $('#mapDetail video')?.pause(); else load(); });
  window.SerenityMaps.create($('#travelMap'), { zoomControl: false }).then(result => {
    ({ map, L } = result); L.control.zoom({ position: 'topright' }).addTo(map); layer = L.layerGroup().addTo(map); map.setView([22, 5], 2);
    let failed = false; result.tiles.on('tileerror', () => { if (!failed) { failed = true; $('#mapStatus').textContent = 'Map tiles are unavailable. Published trips and directions still work below.'; } });
    map.on('moveend', () => { clearTimeout(timer); timer = setTimeout(() => load(), 350); });
    load({ worldwide: true, trip: new URLSearchParams(location.search).get('trip') });
  }).catch(error => { $('#mapStatus').textContent = error.message; load({ worldwide: true }); });
})();
