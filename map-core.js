/* Shared map runtime; no device location, tracking, prefetch, or offline tile downloads. */
(() => {
  let ready;
  async function load() {
    if (!ready) ready = (async () => {
      const css = document.createElement('link'); css.rel = 'stylesheet'; css.href = 'https://unpkg.com/leaflet@1.9.4/dist/leaflet.css';
      css.integrity = 'sha256-p4NxAoJBhIIN+hmNHrzRCf9tD/miZyoHS5obTRR9BMY='; css.crossOrigin = '';
      const styleReady = new Promise((resolve, reject) => {
        const timer = setTimeout(() => { css.remove(); reject(new Error('Map styles could not load. Check your connection.')); }, 15000);
        css.onload = () => { clearTimeout(timer); resolve(); }; css.onerror = () => { clearTimeout(timer); reject(new Error('Map styles could not load. Check your connection.')); };
      });
      document.head.append(css);
      const scriptReady = window.L ? Promise.resolve() : new Promise((resolve, reject) => {
        const script = document.createElement('script'); script.src = 'https://unpkg.com/leaflet@1.9.4/dist/leaflet.js';
        script.integrity = 'sha256-20nQCchB9co0qIjJZRGuk2/Z9VM+kNiyxNV1lvTlZBo='; script.crossOrigin = '';
        const timer = setTimeout(() => { script.remove(); reject(new Error('The map library could not load. Check your connection.')); }, 15000);
        script.onload = () => { clearTimeout(timer); resolve(); };
        script.onerror = () => { clearTimeout(timer); script.remove(); reject(new Error('The map library is unavailable. Coordinates and trip links still work.')); };
        document.head.append(script);
      });
      await Promise.all([styleReady, scriptReady]);
      const response = await fetch('/api/map/config');
      if (!response.ok) throw new Error('The map configuration is unavailable.');
      return { L: window.L, config: await response.json() };
    })().catch(error => { ready = null; throw error; });
    return ready;
  }
  async function create(container, options = {}) {
    const { L, config } = await load();
    const map = L.map(container, { worldCopyJump: true, minZoom: 2, maxZoom: 19, ...options });
    const tiles = L.tileLayer(config.tile_url, { maxZoom: 19, updateWhenIdle: true, keepBuffer: 1,
      attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors' + (config.attribution !== '© OpenStreetMap contributors' ? ` · ${config.attribution}` : '') });
    tiles.addTo(map);
    return { L, map, tiles };
  }
  function directions(location) {
    return `https://www.google.com/maps/dir/?api=1&destination=${encodeURIComponent(`${location.lat},${location.lng}`)}`;
  }
  window.SerenityMaps = { load, create, directions };
})();
