/* Globe renderer is separate from the Leaflet destination picker. No GPS or tile prefetch. */
(() => {
  const VERSION = '5.15.0';
  let library;
  function asset(tag, url, integrity) {
    return new Promise((resolve, reject) => {
      const element = document.createElement(tag);
      if (tag === 'link') { element.rel = 'stylesheet'; element.href = url; }
      else element.src = url;
      element.integrity = integrity; element.crossOrigin = 'anonymous';
      const timer = setTimeout(() => { element.remove(); reject(new Error('The 3D map could not load. Check your connection.')); }, 20000);
      element.onload = () => { clearTimeout(timer); resolve(); };
      element.onerror = () => { clearTimeout(timer); element.remove(); reject(new Error('The 3D map could not load. Your saved places and trip list are still available.')); };
      document.head.append(element);
    });
  }
  async function loadLibrary() {
    if (!library) library = Promise.all([
      asset('link', `https://unpkg.com/maplibre-gl@${VERSION}/dist/maplibre-gl.css`, 'sha384-mnM9NG1099tBMNxdDQNDKIxYcn/fmqQXFJvbT5l1MsrWvzfxBEffceBsw75/cW2R'),
      window.maplibregl ? Promise.resolve() : asset('script', `https://unpkg.com/maplibre-gl@${VERSION}/dist/maplibre-gl.js`, 'sha384-YhF9vhIfvucb/wOyTQ2aaSCaHO3Tzp/lb74ZMq7t2VBHZfrW3+FojKSxIEVynxN8')
    ]).then(() => window.maplibregl).catch(error => { library = null; throw error; });
    return library;
  }
  const wrap = value => ((value + 180) % 360 + 360) % 360 - 180;
  const radians = value => value * Math.PI / 180;
  const degrees = value => value * 180 / Math.PI;
  function flightPosition(from, to, progress) {
    const vector = ([lng, lat]) => [Math.cos(radians(lat)) * Math.cos(radians(lng)), Math.cos(radians(lat)) * Math.sin(radians(lng)), Math.sin(radians(lat))];
    const a = vector(from), b = vector(to), angle = Math.acos(Math.max(-1, Math.min(1, a.reduce((sum, x, i) => sum + x * b[i], 0))));
    if (angle < 0.000001) return from;
    const xyz = a.map((x, i) => (Math.sin((1 - progress) * angle) * x + Math.sin(progress * angle) * b[i]) / Math.sin(angle));
    return [degrees(Math.atan2(xyz[1], xyz[0])), degrees(Math.atan2(xyz[2], Math.hypot(xyz[0], xyz[1])))];
  }
  function heading(from, to) {
    const delta = radians(to[0] - from[0]), a = radians(from[1]), b = radians(to[1]);
    return degrees(Math.atan2(Math.sin(delta) * Math.cos(b), Math.cos(a) * Math.sin(b) - Math.sin(a) * Math.cos(b) * Math.cos(delta)));
  }
  function style(config) {
    return {
      version: 8,
      projection: { type: 'globe' },
      sky: { 'sky-color': '#f2eee4', 'horizon-color': '#dce4d8', 'fog-color': '#f2eee4', 'atmosphere-blend': 0.7 },
      light: { anchor: 'viewport', color: '#fff7e8', intensity: 0.35, position: [1.5, 210, 40] },
      sources: {
        imagery: { type: 'raster', tiles: [config.imagery_url], tileSize: 256, maxzoom: 14, attribution: config.imagery_attribution },
        streets: { type: 'raster', tiles: [config.tile_url], tileSize: 256, maxzoom: 19, attribution: config.attribution },
        elevation: { type: 'raster-dem', tiles: [config.terrain_url], tileSize: 256, maxzoom: 15, encoding: 'terrarium', attribution: config.terrain_attribution },
        buildings: { type: 'vector', url: config.buildings_url }
      },
      layers: [
        { id: 'earth', type: 'background', paint: { 'background-color': '#e5e0d4' } },
        { id: 'imagery', type: 'raster', source: 'imagery', paint: { 'raster-fade-duration': 300, 'raster-saturation': -0.12, 'raster-brightness-max': 0.96 } },
        { id: 'streets', type: 'raster', source: 'streets', layout: { visibility: 'none' } },
        { id: 'buildings', type: 'fill-extrusion', source: 'buildings', 'source-layer': 'building', minzoom: 14,
          paint: { 'fill-extrusion-color': '#e4dfd6', 'fill-extrusion-opacity': 0.85,
            'fill-extrusion-height': ['coalesce', ['get', 'render_height'], 3], 'fill-extrusion-base': ['coalesce', ['get', 'render_min_height'], 0] } }
      ],
      terrain: { source: 'elevation', exaggeration: 1 }
    };
  }
  async function create(container, { onNotice = () => {}, onSpinChange = () => {} } = {}) {
    const [gl, response] = await Promise.all([loadLibrary(), fetch('/api/map/config')]);
    if (!response.ok) throw new Error('Map configuration is unavailable. Your travel journal still works.');
    const config = await response.json();
    const homeZoom = () => Math.max(0.5, Math.min(1.8, Math.log2(Math.min(container.clientWidth, container.clientHeight) * 0.76 / 154)));
    let map;
    try {
      map = new gl.Map({ container, style: style(config), center: [12, 25], zoom: homeZoom(), minZoom: 0.5, maxZoom: 18,
        maxPitch: 75, attributionControl: false, canvasContextAttributes: { antialias: true }, renderWorldCopies: false });
      await new Promise((resolve, reject) => {
        const timeout = setTimeout(() => reject(new Error('The 3D world is taking too long to load. Try again, or use your travel journal.')), 20000);
        map.once('style.load', () => { clearTimeout(timeout); resolve(); });
      });
    } catch (error) { map?.remove(); throw new Error(error.message || '3D requires WebGL. Your saved places and public trips are still available.'); }
    map.addControl(new gl.NavigationControl({ visualizePitch: true }), 'top-right');
    map.addControl(new gl.AttributionControl({ compact: true }), 'bottom-right');
    map.getCanvas().setAttribute('aria-label', 'Interactive 3D world. Arrow keys pan; plus and minus zoom; Shift with arrow keys rotates and tilts.');
    const failed = new Set();
    map.on('error', event => {
      const source = event.sourceId || event.error?.sourceId || 'map';
      if (failed.has(source)) return;
      failed.add(source);
      onNotice(source === 'elevation' ? 'Elevation tiles are unavailable. Surface relief may be incomplete.' : source === 'buildings' ? 'Building detail is unavailable. The globe and travel journal still work.' : 'Some map data could not load. Try the Streets view or use the place list.');
    });
    container.addEventListener('webglcontextlost', event => { event.preventDefault(); onNotice('The 3D view was interrupted. Reload the map; your travel history is saved.'); }, true);
    const markers = new Map(), ambient = [];
    const motion = window.matchMedia('(prefers-reduced-motion: reduce)');
    let animate = !motion.matches, spinning = false, frame = 0, last = 0, elapsed = 0, birdOrigin = map.getCenter();
    const routes = [[[-73.78, 40.64], [-0.45, 51.47]], [[2.55, 49.01], [139.78, 35.55]], [[103.99, 1.36], [151.18, -33.95]]];
    routes.forEach((route, index) => {
      const element = document.createElement('div'); element.className = 'world-aircraft'; element.setAttribute('aria-hidden', 'true');
      element.innerHTML = '<svg viewBox="0 0 48 48"><path class="plane-shadow" d="M23 3 26 3 28 19 44 29 44 32 28 27 28 38 34 42 34 45 24 42 14 45 14 42 20 38 20 27 4 32 4 29 20 19Z"/><path d="M23 3 25 3 27 19 43 29 43 31 27 26 27 38 33 42 33 44 24 41 15 44 15 42 21 38 21 26 5 31 5 29 21 19Z"/><path class="plane-body" d="M23 4 25 4 26 39 24 41 22 39Z"/></svg>';
      ambient.push({ kind: 'plane', route, phase: index * 0.29, element, marker: new gl.Marker({ element, rotationAlignment: 'map', pitchAlignment: 'map' }).setLngLat(route[0]).addTo(map) });
    });
    for (let index = 0; index < 5; index++) {
      const element = document.createElement('div'); element.className = 'world-bird'; element.style.setProperty('--flap-delay', `${-index * 0.21}s`); element.setAttribute('aria-hidden', 'true');
      element.innerHTML = '<svg viewBox="0 0 40 20"><path class="wing-left" d="M20 13Q10 0 2 7Q12 7 20 13"/><path class="wing-right" d="M20 13Q30 0 38 7Q28 7 20 13"/></svg>';
      ambient.push({ kind: 'bird', phase: index / 5, element, marker: new gl.Marker({ element, rotationAlignment: 'map', pitchAlignment: 'map' }).setLngLat([birdOrigin.lng, birdOrigin.lat]).addTo(map) });
    }
    function setSpin(value) { spinning = Boolean(value) && !motion.matches; onSpinChange(spinning); schedule(); }
    function schedule() {
      cancelAnimationFrame(frame); frame = 0; last = 0;
      const active = !document.hidden && !motion.matches && (animate || spinning);
      for (const item of ambient) item.element.style.display = active && animate && (item.kind !== 'bird' || map.getZoom() >= 10) ? '' : 'none';
      if (active) frame = requestAnimationFrame(tick);
    }
    function tick(now) {
      if (last && now - last < 65) { frame = requestAnimationFrame(tick); return; }
      const delta = last ? Math.min(100, now - last) : 0; last = now; elapsed += delta / 1000;
      if (spinning) { const center = map.getCenter(); map.jumpTo({ center: [wrap(center.lng + delta * 0.0025), center.lat] }); }
      if (animate) for (const item of ambient) {
        if (item.kind === 'plane') {
          const progress = (elapsed / 240 + item.phase) % 1;
          const point = flightPosition(...item.route, progress), next = flightPosition(...item.route, Math.min(1, progress + 0.0001));
          item.marker.setLngLat(point).setRotation(heading(point, next));
        } else {
          item.element.style.display = map.getZoom() >= 10 ? '' : 'none';
          if (map.getZoom() < 10) continue;
          const angle = elapsed / 13 + item.phase * 2 * Math.PI, radius = 0.003 * Math.pow(2, 12 - map.getZoom());
          item.marker.setLngLat([wrap(birdOrigin.lng + Math.cos(angle) * radius / Math.max(0.1, Math.cos(radians(birdOrigin.lat)))), Math.max(-85, Math.min(85, birdOrigin.lat + Math.sin(angle) * radius * 0.6))]).setRotation(-degrees(angle));
        }
      }
      frame = requestAnimationFrame(tick);
    }
    map.on('moveend', () => { birdOrigin = map.getCenter(); });
    map.on('mousedown', () => setSpin(false)); map.on('touchstart', () => setSpin(false)); map.on('wheel', () => setSpin(false));
    map.getCanvas().addEventListener('keydown', () => setSpin(false));
    const visibility = () => schedule();
    const reducedMotion = () => { if (motion.matches) setSpin(false); schedule(); };
    document.addEventListener('visibilitychange', visibility); motion.addEventListener('change', reducedMotion);
    schedule();
    return {
      map,
      setMarkers(items, onSelect) {
        for (const marker of markers.values()) marker.remove(); markers.clear();
        for (const item of items) {
          const element = document.createElement('button'); element.type = 'button'; element.className = `world-pin ${item.visited ? 'is-visited' : ''}`;
          element.textContent = item.visited ? '✓' : '•'; element.setAttribute('aria-label', `${item.visited ? 'Visited: ' : 'Trip: '}${item.label}`);
          element.title = item.label; element.onclick = event => { event.stopPropagation(); onSelect(item); };
          markers.set(item.key, new gl.Marker({ element, anchor: 'bottom' }).setLngLat([item.lng, item.lat]).addTo(map));
        }
      },
      focus(place) { setSpin(false); map.flyTo({ center: [place.lng, place.lat], zoom: 12, pitch: 58, duration: motion.matches ? 0 : 1600 }); },
      world() { setSpin(false); map.flyTo({ center: [12, 25], zoom: homeZoom(), pitch: 0, bearing: 0, duration: motion.matches ? 0 : 1400 }); },
      setStreets(value) { map.setLayoutProperty('streets', 'visibility', value ? 'visible' : 'none'); },
      setAmbient(value) { animate = Boolean(value); schedule(); },
      setSpin,
      rotate(delta) { setSpin(false); map.easeTo({ bearing: map.getBearing() + delta, duration: motion.matches ? 0 : 350 }); },
      tilt() { setSpin(false); map.easeTo({ pitch: map.getPitch() > 25 ? 0 : 60, duration: motion.matches ? 0 : 500 }); },
      destroy() { cancelAnimationFrame(frame); document.removeEventListener('visibilitychange', visibility); motion.removeEventListener('change', reducedMotion); map.remove(); }
    };
  }
  window.SerenityWorld = { create, flightPosition };
})();
