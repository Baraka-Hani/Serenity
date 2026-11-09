async function runDestinationPickerTests(source) {
  const assert = (ok, text) => { if (!ok) throw new Error(text); };
  class Node {
    constructor() { this.nodes = new Map(); this.children = []; this.value = ''; this.textContent = ''; }
    querySelector(selector) { if (!this.nodes.has(selector)) this.nodes.set(selector, new Node()); return this.nodes.get(selector); }
    append(...nodes) { this.children.push(...nodes); }
    replaceChildren(...nodes) { this.children = nodes; }
  }
  const requests = [], changes = [];
  const window = { SerenityMaps: { create() { throw new Error('Maps must load only on explicit request'); } } };
  const fetch = async url => { requests.push(url); return { ok: true, json: async () => ({ places: [{ lat: 38.7, lng: -9.1, label: 'Lisbon, Portugal', provider: 'photon', source: 'place', place_id: 'R:1' }] }) }; };
  new Function('window', 'document', 'fetch', 'AbortController', source)(window, { createElement: () => new Node() }, fetch, class { constructor() { this.signal = {}; } abort() {} });
  const picker = window.SerenityDestinationPicker.create({ text: 'Existing text-only destination', onChange: value => changes.push(value) });
  assert(picker.destination === 'Existing text-only destination' && picker.value === null, 'Opening a legacy trip must not silently erase its destination');
  assert(changes.length === 0, 'Rendering a destination must not count as an edit');
  assert(requests.length === 0, 'Opening the field must not geocode automatically');
  const field = selector => picker.element.querySelector(selector);
  field('[data-name]').value = 'Equator waypoint'; field('[data-lat]').value = '0'; field('[data-lng]').value = '0';
  field('[data-coordinates]').onclick();
  assert(picker.value.lat === 0 && picker.value.lng === 0, 'Zero latitude/longitude are valid, not missing values');
  field('[data-lat]').value = '91'; field('[data-coordinates]').onclick();
  assert(picker.value.lat === 0, 'Invalid coordinates must not overwrite the saved selection');
  const searchInput = [...picker.element.nodes.entries()].find(([selector]) => selector.endsWith('-search'))[1];
  searchInput.value = 'Lisbon'; await field('[data-search]').onclick();
  assert(requests.length === 1 && requests[0].includes('q=Lisbon'), 'Search must be explicit and go through the local API');
  field('[data-results]').children[0].onclick();
  assert(picker.value.provider === 'photon' && picker.destination === 'Lisbon, Portugal', 'A place must be explicitly selected to become a pinned destination');
  field('[data-clear]').onclick();
  assert(picker.value === null && picker.destination === '', 'Explicit removal must clear the pin and destination');
  picker.destroy();
  return 'Destination picker tests passed: legacy preservation, explicit edits/search, valid zero coordinates, invalid bounds, and removal.';
}
if (typeof module !== 'undefined' && require.main === module) runDestinationPickerTests(require('fs').readFileSync(require('path').join(__dirname, '../destination-picker.js'), 'utf8')).then(console.log).catch(error => { console.error(error); process.exitCode = 1; });
