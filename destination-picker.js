/* Reusable trip destination field: explicit place search, map pin, or keyboard coordinates. */
(() => {
  let serial = 0;
  function create({ value = null, text = '', onChange = () => {} } = {}) {
    const id = `destination-${++serial}`;
    let selected = value ? { ...value } : null, legacy = text, map, marker, controller, destroyed = false;
    const element = document.createElement('div'); element.className = 'destination-picker';
    element.innerHTML = `<label for="${id}-search">Destination on the map</label><div class="destination-search"><input id="${id}-search" type="search" maxlength="120" placeholder="Search a city, beach, landmark…" autocomplete="off"><button type="button" data-search>Search</button></div><p class="destination-privacy">Search sends the place name to Photon. Use public travel places, not private addresses. A pin on a published trip is public. No live location is collected.</p><div data-results class="destination-results"></div><p data-selected class="destination-selected"></p><button type="button" data-clear>Remove destination</button><details class="destination-map-panel"><summary>Choose on map or enter coordinates</summary><div data-map class="destination-map" aria-label="Choose a trip destination by clicking the map"></div><div class="destination-coordinates"><label>Place name<input data-name maxlength="240" placeholder="Name this spot"></label><label>Latitude<input data-lat type="number" min="-90" max="90" step="any" placeholder="e.g. 38.7071"></label><label>Longitude<input data-lng type="number" min="-180" max="180" step="any" placeholder="e.g. -9.1355"></label><button type="button" data-coordinates>Use this pin</button></div></details><p data-status role="status" class="destination-status"></p><small>Place data © <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noopener">OpenStreetMap contributors</a> · Photon</small>`;
    const $ = selector => element.querySelector(selector);
    function update(value, notify = true) {
      selected = value;
      if (!value && notify) legacy = '';
      $('[data-selected]').textContent = value ? `${value.label} · ${value.lat.toFixed(5)}, ${value.lng.toFixed(5)}` : legacy ? `${legacy} · Add a map pin to make this trip discoverable on Map.` : 'No destination pin yet. Add one to appear on Map when published.';
      $('[data-clear]').hidden = !value && !legacy;
      $('[data-name]').value = value?.label || '';
      $('[data-lat]').value = value?.lat ?? ''; $('[data-lng]').value = value?.lng ?? '';
      if (map) {
        if (marker) marker.remove();
        marker = value ? window.L.circleMarker([value.lat, value.lng], { radius: 10, color: '#fff', weight: 3, fillColor: '#ff6945', fillOpacity: 1 }).addTo(map) : null;
      }
      if (notify) onChange(value);
    }
    async function openMap() {
      if (destroyed) return;
      if (!map) try {
        const result = await window.SerenityMaps.create($('[data-map]'), { scrollWheelZoom: false });
        if (destroyed) { result.map.remove(); return; }
        map = result.map;
        map.setView(selected ? [selected.lat, selected.lng] : [22, 5], selected ? 13 : 2);
        map.on('click', event => {
          update({ lat: Number(event.latlng.lat.toFixed(7)), lng: Number(event.latlng.wrap().lng.toFixed(7)), label: $('[data-name]').value.trim() || 'Pinned location', source: 'pin', provider: 'manual', place_id: '' });
          $('[data-status]').textContent = 'Pin selected. Check the place name and position before saving.';
        });
        update(selected, false);
      } catch (error) { if (!destroyed) $('[data-status]').textContent = error.message + ' You can enter coordinates below.'; }
      map?.invalidateSize();
    }
    $('.destination-map-panel').ontoggle = () => { if ($('.destination-map-panel').open) openMap(); };
    async function search() {
      const q = $(`#${id}-search`).value.trim();
      if (q.length < 2) { $('[data-status]').textContent = 'Enter at least two characters, then search.'; return; }
      controller?.abort(); const activeController = new AbortController(); controller = activeController;
      $('[data-results]').replaceChildren();
      $('[data-search]').disabled = true; $('[data-status]').textContent = 'Finding public places…';
      try {
        const response = await fetch(`/api/places/search?q=${encodeURIComponent(q)}`, { signal: activeController.signal });
        const data = await response.json(); if (!response.ok) throw new Error(data.error || 'Place search failed.');
        if (destroyed || controller !== activeController) return;
        $('[data-results]').replaceChildren();
        for (const place of data.places) {
          const button = document.createElement('button'); button.type = 'button'; button.textContent = `${place.label} · ${place.kind || 'place'} · ${place.lat.toFixed(4)}, ${place.lng.toFixed(4)}`;
          button.onclick = () => { update(place); $('[data-results]').replaceChildren(); if (map) map.setView([place.lat, place.lng], 13); $('[data-status]').textContent = 'Destination selected. You can refine its position on the map.'; };
          $('[data-results]').append(button);
        }
        $('[data-status]').textContent = data.places.length ? 'Choose the place you mean.' : 'No place found. Try a nearby landmark or drop a pin.';
      } catch (error) { if (error.name !== 'AbortError' && !destroyed && controller === activeController) $('[data-status]').textContent = error.message; }
      finally { if (!destroyed && controller === activeController) $('[data-search]').disabled = false; }
    }
    $('[data-search]').onclick = search;
    $(`#${id}-search`).onkeydown = event => { if (event.key === 'Enter') { event.preventDefault(); search(); } };
    $('[data-clear]').onclick = () => { update(null); $('[data-status]').textContent = 'Destination removed. This trip will not appear on Map.'; };
    $('[data-coordinates]').onclick = () => {
      const latText = $('[data-lat]').value, lngText = $('[data-lng]').value;
      const lat = Number(latText), lng = Number(lngText), label = $('[data-name]').value.trim();
      if (!latText || !lngText || !Number.isFinite(lat) || !Number.isFinite(lng) || lat < -90 || lat > 90 || lng < -180 || lng > 180 || !label) { $('[data-status]').textContent = 'Enter a place name, latitude −90 to 90, and longitude −180 to 180.'; return; }
      update({ lat, lng, label, source: 'pin', provider: 'manual', place_id: '' });
      map?.setView([lat, lng], 14); $('[data-status]').textContent = 'Destination pin selected.';
    };
    update(selected, false);
    return { element, get value() { return selected ? { ...selected } : null; }, get destination() { return selected?.label.slice(0, 120) || legacy; },
      reset() { update(null); $(`#${id}-search`).value = ''; }, destroy() { destroyed = true; controller?.abort(); map?.remove(); } };
  }
  window.SerenityDestinationPicker = { create };
})();
