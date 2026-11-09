const CACHE_NAME = 'serenity-shell-v12-people-chat';
const APP_PAGES = new Set([
  '/map.html',
  '/app.html',
  '/auth.html',
  '/account.html',
  '/feed.html',
  '/my-clips.html',
  '/profile.html',
  '/search.html',
  '/tile-01.html',
  '/tile-02.html',
  '/tile-03.html',
  '/tile-04.html',
  '/tile-05.html'
]);
const SHELL_ASSETS = [
  '/account-discovery.js',
  '/account-discovery.css',
  '/map.html',
  '/map-core.js',
  '/travel-map.js',
  '/travel-map.css',
  '/destination-picker.js',
  '/destination-picker.css',
  '/app.html',
  '/auth.html',
  '/account.html',
  '/feed.html',
  '/my-clips.html',
  '/profile.html',
  '/search.html',
  '/tile-01.html',
  '/tile-02.html',
  '/tile-03.html',
  '/tile-04.html',
  '/tile-05.html',
  '/manifest.webmanifest',
  '/serenity-logo.svg',
  '/serenity-icon-192.png',
  '/serenity-icon-512.png',
  '/shared-theme.js',
  '/auth-client.js',
  '/app-client.js',
  '/app-studio.js',
  '/studio-import.js',
  '/studio-import.css',
  '/studio-grouping.js',
  '/studio-video-analysis.js',
  '/studio-vision-worker.js',
  '/studio-publication.js',
  '/studio-publication.css',
  '/social-feed.js',
  '/social-feed.css',
  '/feed-hub.js',
  '/feed-hub.css',
  '/header-feed-picker.js',
  '/liquid-toolbar.js',
  '/liquid-toolbar.css',
  '/trip-sidebar.js',
  '/trip-sidebar.css',
  '/feed-view.js',
  '/feed-view.css',
  '/account.js',
  '/account.css',
  '/profile.js',
  '/profile.css',
  '/messages-client.js',
  '/messages.js',
  '/messages.css',
  '/app-pwa.js'
];
const SHELL_PATHS = new Set(SHELL_ASSETS);

self.addEventListener('install', event => {
  event.waitUntil(caches.open(CACHE_NAME).then(cache => cache.addAll(SHELL_ASSETS)).then(() => self.skipWaiting()));
});

self.addEventListener('activate', event => {
  event.waitUntil(
    caches.keys().then(keys => Promise.all(
      keys.filter(key => key.startsWith('serenity-shell-') && key !== CACHE_NAME).map(key => caches.delete(key))
    )).then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', event => {
  const request = event.request;
  const url = new URL(request.url);
  if (request.method !== 'GET' || url.origin !== self.location.origin || url.pathname.startsWith('/api/')) return;

  const isPage = request.mode === 'navigate' && APP_PAGES.has(url.pathname);
  const isShellAsset = SHELL_PATHS.has(url.pathname);
  if (!isPage && !isShellAsset) return;

  const cacheKey = new Request(new URL(url.pathname, self.location.origin));
  event.respondWith((async () => {
    const cache = await caches.open(CACHE_NAME);
    try {
      const response = await fetch(request);
      if (response.ok && response.type === 'basic') {
        try {
          await cache.put(cacheKey, response.clone());
        } catch (error) {
          console.error('Serenity could not update an offline app resource:', error);
        }
      }
      return response;
    } catch (error) {
      const cached = await cache.match(cacheKey);
      if (cached) return cached;
      throw error;
    }
  })());
});
