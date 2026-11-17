/* Optional browser regressions. All APIs are intercepted; no real account/data is read or written.
 * Start the local app, install Playwright, then: node backend/test_travel_map_browser.js
 * SERENITY_TEST_URL, SERENITY_PLAYWRIGHT_MODULE and SERENITY_BROWSER_PATH can override defaults.
 */
const assert = require('node:assert/strict');
const { chromium } = require(process.env.SERENITY_PLAYWRIGHT_MODULE || 'playwright');
const base = process.env.SERENITY_TEST_URL || 'http://127.0.0.1:8765';
const privatePlace = { id: 123, lat: 45, lng: -65, label: 'Synthetic private place', visited_on: '2026-01-01', note: 'Synthetic private note' };
const publicTrip = { id: 234, lat: 51.1784, lng: -115.5708, label: 'Banff', name: 'Synthetic public trip', creator_name: 'QA Creator', creator_username: 'qa_creator', creator_public_id: '0123456789abcdef', preview_post_id: '00000000000000000000000000000000', video_count: 1, summary: 'Synthetic public summary' };

(async () => {
  const browser = await chromium.launch({ headless: true, ...(process.env.SERENITY_BROWSER_PATH ? { executablePath: process.env.SERENITY_BROWSER_PATH } : {}) });
  try {
    async function fixture(locations = []) {
      const context = await browser.newContext({ viewport: { width: 390, height: 844 }, serviceWorkers: 'block' });
      // Refuse every API not explicitly mocked below, including future endpoints.
      await context.route('**/api/**', route => route.abort());
      await context.route('https://**', route => route.abort());
      const page = await context.newPage(), state = { owner: 1, failIdentity: false, reads: 0, put: null }, errors = [];
      page.on('pageerror', error => errors.push(error.message));
      await page.route('**/map-world.js', route => route.fulfill({ contentType: 'text/javascript', body: 'window.SerenityWorld={create:async()=>{throw Error("Synthetic WebGL unavailable")}}' }));
      await page.route('**/api/me', route => state.failIdentity ? route.abort() : route.fulfill({ json: { user: { id: state.owner, name: 'Synthetic traveller' } } }));
      await page.route('**/api/map/visits?*', route => { state.reads++; return route.fulfill({ json: { locations: state.owner === 1 ? locations : [], total: state.owner === 1 ? locations.length : 0, has_more: false } }); });
      await page.route('**/api/map/trips?*', route => route.fulfill({ json: { trips: [publicTrip], has_more: false } }));
      await page.route('**/api/map/visits', async route => {
        assert.equal(route.request().method(), 'PUT');
        const body = route.request().postDataJSON();
        await new Promise(resolve => { state.put = resolve; });
        await route.fulfill({ status: 201, json: { created: true, total: 1, location: { id: 456, ...body.location, note: body.note, visited_on: body.visited_on } } });
      });
      await page.goto(`${base}/map.html`);
      await page.waitForFunction(() => document.querySelector('#mapVisitCount').textContent !== '—');
      await page.waitForFunction(() => !document.querySelector('#mapNotice').hidden);
      return { context, page, state, errors };
    }

    const first = await fixture([privatePlace]);
    try {
      const { page, state } = first;
      await page.locator('#mapVisitedTab').click(); await page.locator('#mapVisits .map-place-button').click();
      assert((await page.locator('#mapDetail').boundingBox()).y >= 0, 'mobile preview must scroll into view');
      assert((await page.locator('#mapDetail').boundingBox()).y < 100, 'mobile preview should be near the viewport top');
      assert((await page.locator('#mapDetail').textContent()).includes(privatePlace.note));
      state.failIdentity = true;
      await page.evaluate(() => document.dispatchEvent(new Event('visibilitychange')));
      await page.waitForFunction(() => document.querySelector('#mapVisitCount').textContent === '—');
      assert.equal(await page.locator('#mapDetail').textContent(), '');
      assert.equal(await page.locator('#mapDetail').isVisible(), false);
      assert.equal(await page.locator('#mapVisits').textContent(), '');
      assert((await page.locator('#mapNotice').textContent()).includes('Synthetic WebGL unavailable'), 'renderer failure must survive account refresh');
      assert.deepEqual(first.errors, []);
    } finally { await first.context.close(); }

    const second = await fixture();
    try {
      const { page, state } = second;
      await page.locator('#mapTrips .map-place-button').click();
      assert.equal(await page.getByRole('link', { name: 'Watch 1 video ↗' }).getAttribute('href'), 'feed.html?feed=234');
      const directions = new URL(await page.getByRole('link', { name: 'Get directions ↗' }).getAttribute('href'));
      assert.equal(directions.searchParams.get('destination'), '51.1784,-115.5708');
      await page.getByRole('button', { name: '✓ I’ve been here' }).click();
      assert.equal(await page.locator('#mapPlaceLat').inputValue(), '51.1784');
      assert.equal(await page.locator('#mapPlaceLng').inputValue(), '-115.5708');
      assert((await page.locator('#mapNotice').textContent()).includes('Synthetic WebGL unavailable'), 'opening the form must retain the outage notice');
      await page.locator('#mapVisitNote').fill('Previous-account draft');
      state.owner = 2;
      await page.evaluate(() => document.dispatchEvent(new Event('visibilitychange')));
      await page.waitForFunction(() => !document.querySelector('#mapVisitDialog').open);
      assert.equal(await page.locator('#mapPlaceLabel').inputValue(), '');
      assert.equal(await page.locator('#mapVisitNote').inputValue(), '');
      assert.deepEqual(second.errors, []);
    } finally { await second.context.close(); }

    const third = await fixture();
    try {
      const { page, state } = third;
      await page.locator('#mapRecordPlace').click();
      await page.locator('#mapPlaceLabel').fill('Delayed account A place'); await page.locator('#mapPlaceLat').fill('45'); await page.locator('#mapPlaceLng').fill('-65'); await page.locator('#mapVisitNote').fill('Delayed account A secret');
      await page.locator('#mapVisitSave').click();
      await new Promise((resolve, reject) => {
        const timeout = setTimeout(() => { clearInterval(poll); reject(Error('Save request did not start')); }, 5000);
        const poll = setInterval(() => { if (state.put) { clearTimeout(timeout); clearInterval(poll); resolve(); } }, 10);
      });
      state.owner = 2;
      await page.evaluate(() => document.dispatchEvent(new Event('visibilitychange')));
      await page.waitForFunction(() => !document.querySelector('#mapVisitDialog').open);
      const response = page.waitForResponse(response => response.url().endsWith('/api/map/visits') && response.request().method() === 'PUT');
      state.put(); await response; await page.waitForTimeout(100);
      assert.equal(await page.locator('#mapVisitCount').textContent(), '0');
      assert.equal(await page.locator('#mapVisits').textContent(), '');
      assert(!(await page.locator('#mapJournalStatus').textContent()).includes('account A'));
      assert.deepEqual(third.errors, []);
    } finally { await third.context.close(); }
    console.log('Travel map browser regressions passed: mobile preview, private identity cleanup, fallback links, draft isolation, persistent failure notices, and delayed save isolation.');
  } finally { await browser.close(); }
})().catch(error => { console.error(error); process.exitCode = 1; });
