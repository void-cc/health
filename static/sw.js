// Service Worker for Health Tracker PWA

const CACHE_NAME = 'health-tracker-v1';

// App shell resources to cache on install
const APP_SHELL = [
  '/',
  '/static/styles.css',
  '/static/css/ui.css',
  '/static/js/ui.js',
  'https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css',
  'https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css'
];

// Offline fallback page (inline HTML served when no cache match is available)
const OFFLINE_HTML = `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Offline - Health Tracker</title>
  <style>
    body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
           background: #1a1a2e; color: #e0e0e0; display: flex; align-items: center;
           justify-content: center; min-height: 100vh; margin: 0; text-align: center; }
    .container { padding: 2rem; }
    h1 { color: #0f3460; font-size: 2rem; }
    p { font-size: 1.1rem; margin: 1rem 0; }
    button { background: #0f3460; color: #fff; border: none; padding: 0.75rem 1.5rem;
             border-radius: 8px; font-size: 1rem; cursor: pointer; margin-top: 1rem; }
    button:hover { background: #1a5276; }
  </style>
</head>
<body>
  <div class="container">
    <h1>You're Offline</h1>
    <p>Health Tracker requires a network connection for this page.</p>
    <p>Please check your connection and try again.</p>
    <button onclick="window.location.reload()">Retry</button>
  </div>
</body>
</html>`;

// --- Install: cache the app shell and skip waiting for immediate activation ---
self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      return cache.addAll(APP_SHELL);
    })
  );
  self.skipWaiting();
});

// --- Activate: clean up old caches and claim clients immediately ---
self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((cacheNames) => {
      return Promise.all(
        cacheNames
          .filter((name) => name !== CACHE_NAME)
          .map((name) => caches.delete(name))
      );
    })
  );
  self.clients.claim();
});

// --- Fetch: network-first for navigation/API, cache-first for static assets ---
self.addEventListener('fetch', (event) => {
  const { request } = event;

  // Never cache POST or other non-GET requests
  if (request.method !== 'GET') {
    return;
  }

  // Skip chrome-extension and other non-http(s) schemes
  if (!request.url.startsWith('http')) {
    return;
  }

  const url = new URL(request.url);

  // Static assets (/static/ path or CDN resources): cache-first strategy
  if (url.pathname.startsWith('/static/') || url.origin !== location.origin) {
    event.respondWith(cacheFirst(request));
    return;
  }

  // Navigation and API requests: network-first strategy
  event.respondWith(networkFirst(request));
});

/**
 * Cache-first strategy: serve from cache if available, otherwise fetch from
 * network and store the response in the cache for future use.
 */
async function cacheFirst(request) {
  const cached = await caches.match(request);
  if (cached) {
    return cached;
  }

  try {
    const response = await fetch(request);
    // Only cache successful responses
    if (response.ok) {
      const cache = await caches.open(CACHE_NAME);
      cache.put(request, response.clone());
    }
    return response;
  } catch {
    // For static assets with no cache and no network, return 503
    return new Response('Offline', { status: 503, statusText: 'Service Unavailable' });
  }
}

/**
 * Network-first strategy: try the network and cache successful responses.
 * Fall back to cache, then to an offline page if both fail.
 */
async function networkFirst(request) {
  try {
    const response = await fetch(request);
    // Cache successful navigation responses for offline access
    if (response.ok) {
      const cache = await caches.open(CACHE_NAME);
      cache.put(request, response.clone());
    }
    return response;
  } catch {
    // Network failed — try the cache
    const cached = await caches.match(request);
    if (cached) {
      return cached;
    }

    // No cache hit for a navigation request — show offline fallback
    if (request.mode === 'navigate') {
      return new Response(OFFLINE_HTML, {
        status: 503,
        headers: { 'Content-Type': 'text/html' }
      });
    }

    return new Response('Offline', { status: 503, statusText: 'Service Unavailable' });
  }
}
