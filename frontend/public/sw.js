/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
let API_BASE = ''

function setApiBaseFromUrl(url) {
  if (API_BASE) return API_BASE;
  const parts = url.pathname.split('/').filter(Boolean);
  if (parts.length >= 2 && parts[0] === 'api') {
    API_BASE = `/${parts[0]}/${parts[1]}`;
  }
  return API_BASE;
}
/**
 * Service Worker for L30 Library
 *
 * Provides offline capability for the circulation desk with:
 * - Cache-first strategy for static assets
 * - Network-first with cache fallback for API calls
 * - Offline queue for checkout/checkin operations
 * - Background sync when back online
 *
 * SECURITY: This service worker is designed to NOT cache sensitive data:
 * - Patron PII (names, addresses, phone numbers, emails)
 * - Session tokens and authentication data
 * - Financial/payment information
 * - Reading history and patron activity
 *
 * All patron-related endpoints are excluded from caching to prevent
 * sensitive data from persisting in browser storage after logout.
 */

// Cache version - increment to force cache refresh.
// Bumped to v1.3.0 alongside the navigation-network-first fix so users
// stuck with old v1.2.0 caches (which served stale HTML cache-first) get
// a clean slate on next visit. Future: auto-bump from build-time git SHA.
const CACHE_VERSION = 'v1.3.0';

// Cache names
const STATIC_CACHE = `lsc-static-${CACHE_VERSION}`;
const API_CACHE = `lsc-api-${CACHE_VERSION}`;
const FONT_CACHE = `lsc-fonts-${CACHE_VERSION}`;

// All cache names for cleanup
const CACHE_NAMES = [STATIC_CACHE, API_CACHE, FONT_CACHE];

// Static assets to cache on install
const STATIC_ASSETS = [
  '/',
  '/favicon.svg',
  '/og-image.png',
  '/manifest.json',
  // Icons for PWA
  '/icons/icon-72x72.png',
  '/icons/icon-96x96.png',
  '/icons/icon-128x128.png',
  '/icons/icon-144x144.png',
  '/icons/icon-152x152.png',
  '/icons/icon-192x192.png',
  '/icons/icon-384x384.png',
  '/icons/icon-512x512.png',
];

// SECURITY: Sensitive endpoint patterns that must NEVER be cached
// These patterns match API endpoints that return PII, session data, or financial info
const SENSITIVE_ENDPOINT_PATTERNS = [
  // Authentication and session endpoints
  /\/api\/v\d+\/auth\//,
  // User profile endpoints (contains PII)
  /\/api\/v\d+\/me$/,
  /\/api\/v\d+\/users\/\d+$/,
  // Patron data endpoints (contains PII: email, address, phone, etc.)
  /\/api\/v\d+\/staff\/patrons/,
  /\/api\/v\d+\/patrons/,
  // Checkout/circulation endpoints (contains patron activity)
  /\/api\/v\d+\/staff\/checkout/,
  /\/api\/v\d+\/staff\/checkin/,
  /\/api\/v\d+\/circulation/,
  /\/api\/v\d+\/checkouts/,
  // Financial and payment endpoints
  /\/api\/v\d+\/fines/,
  /\/api\/v\d+\/payments/,
  /\/api\/v\d+\/financial/,
  /\/api\/v\d+\/billing/,
  // Session management
  /\/api\/v\d+\/sessions/,
  // Privacy-related endpoints
  /\/api\/v\d+\/privacy/,
  // Account settings
  /\/api\/v\d+\/account/,
  // Dashboard with potentially sensitive stats
  /\/api\/v\d+\/staff\/dashboard/,
  // Holds and reservations (tied to patron identity)
  /\/api\/v\d+\/holds/,
  /\/api\/v\d+\/reservations/,
  // Reading history (sensitive patron activity)
  /\/api\/v\d+\/reading-history/,
  // Favorites/reading lists when authenticated
  /\/api\/v\d+\/favorites/,
  /\/api\/v\d+\/reading-lists/,
];

// API endpoints to cache for offline use (NON-SENSITIVE only)
// SECURITY: These endpoints do NOT contain patron PII or sensitive data
const CACHEABLE_API_PATTERNS = [
  /\/api\/v1\/catalog\/barcode\//,              // Barcode lookups (item info only, no patron data)
  /\/api\/v1\/catalog\/search/,                 // Catalog search results (public item data)
  /\/api\/v1\/catalog\/items\/\d+$/,            // Individual catalog item details
  /\/api\/v1\/branches/,                        // Branch locations (public data)
  /\/api\/v1\/hours/,                           // Library hours (public data)
];

// API endpoints for stale-while-revalidate (NON-SENSITIVE only)
// SECURITY: These endpoints do NOT contain patron PII or sensitive data
const STALE_WHILE_REVALIDATE_PATTERNS = [
  /\/api\/v1\/catalog\/featured/,               // Featured items (public data)
  /\/api\/v1\/events/,                          // Library events (public data)
  /\/api\/v1\/announcements/,                   // Public announcements
];

// Offline queue storage key
const OFFLINE_QUEUE_KEY = 'lsc_circulation_offline_queue';

// ==================== Install Event ====================

self.addEventListener('install', (event) => {
  console.log('[SW] Installing service worker version:', CACHE_VERSION);

  event.waitUntil(
    Promise.all([
      // Cache static assets (with individual error handling for missing files)
      caches.open(STATIC_CACHE).then(async (cache) => {
        console.log('[SW] Caching static assets');
        // Cache each asset individually to handle missing files gracefully
        const cachePromises = STATIC_ASSETS.map(async (url) => {
          try {
            await cache.add(url);
            console.log('[SW] Cached:', url);
          } catch (error) {
            console.warn('[SW] Failed to cache (may not exist):', url);
          }
        });
        return Promise.all(cachePromises);
      }),
      // Pre-create other caches
      caches.open(API_CACHE),
      caches.open(FONT_CACHE),
    ]).then(() => {
      console.log('[SW] Installation complete');
      // Force activation without waiting for old SW to release
      return self.skipWaiting();
    })
  );
});

// ==================== Activate Event ====================

self.addEventListener('activate', (event) => {
  console.log('[SW] Activating service worker version:', CACHE_VERSION);

  event.waitUntil(
    Promise.all([
      // Clean up old caches
      caches.keys().then((cacheNames) => {
        return Promise.all(
          cacheNames
            .filter((name) => !CACHE_NAMES.includes(name))
            .map((name) => {
              console.log('[SW] Deleting old cache:', name);
              return caches.delete(name);
            })
        );
      }),
      // Take control of all clients immediately
      self.clients.claim(),
    ]).then(() => {
      console.log('[SW] Activation complete');
      // Notify all clients that the SW is active
      return self.clients.matchAll().then((clients) => {
        clients.forEach((client) => {
          client.postMessage({ type: 'SW_ACTIVATED', version: CACHE_VERSION });
        });
      });
    })
  );
});

// ==================== Fetch Event ====================

self.addEventListener('fetch', (event) => {
  const { request } = event;
  const url = new URL(request.url);

  if (isAPIRequest(url)) {
    setApiBaseFromUrl(url);
  }

  // Skip non-GET requests except for circulation operations
  if (request.method !== 'GET') {
    if (isCirculationOperation(request)) {
      event.respondWith(handleCirculationOperation(request));
    }
    return;
  }

  // SECURITY: Never cache sensitive endpoints containing PII, session data, or financial info
  // Always go to network for these requests
  if (isSensitiveEndpoint(url)) {
    event.respondWith(fetch(request));
    return;
  }

  // Navigation requests (typed URLs, clicked links, address-bar navigation)
  // MUST use network-first, otherwise users see stale HTML referencing dead
  // chunk hashes after every deploy. The cached app shell is the offline
  // fallback only. See issue #646.
  if (isNavigationRequest(request)) {
    event.respondWith(networkFirstNavigationStrategy(request));
    return;
  }

  // Handle different request types
  if (isStaticAsset(url)) {
    event.respondWith(cacheFirstStrategy(request, STATIC_CACHE));
  } else if (isFontRequest(url)) {
    event.respondWith(cacheFirstStrategy(request, FONT_CACHE));
  } else if (isStaleWhileRevalidateAPI(url)) {
    event.respondWith(staleWhileRevalidateStrategy(request));
  } else if (isCacheableAPI(url)) {
    event.respondWith(networkFirstStrategy(request));
  } else if (isAPIRequest(url)) {
    // Other API requests: network only, no caching
    event.respondWith(fetch(request));
  }
  // Let default browser behavior handle everything else
});

// ==================== Message Event ====================

self.addEventListener('message', (event) => {
  const { type, payload } = event.data || {};

  switch (type) {
    case 'SKIP_WAITING':
      self.skipWaiting();
      break;

    case 'GET_VERSION':
      event.source.postMessage({ type: 'VERSION', version: CACHE_VERSION });
      break;

    case 'SYNC_OFFLINE_QUEUE':
      syncOfflineQueue().then((result) => {
        event.source.postMessage({ type: 'SYNC_COMPLETE', ...result });
      });
      break;

    case 'CLEAR_CACHES':
      clearAllCaches().then(() => {
        event.source.postMessage({ type: 'CACHES_CLEARED' });
      });
      break;

    case 'GET_QUEUE_STATUS':
      getQueueStatus().then((status) => {
        event.source.postMessage({ type: 'QUEUE_STATUS', ...status });
      });
      break;

    case 'SET_API_BASE':
      if (payload?.apiBase) {
        API_BASE = payload.apiBase;
      }
      break;

    // SECURITY: Clear all potentially sensitive data from cache on logout
    // This ensures no patron PII or session data persists after logout
    case 'USER_LOGOUT':
      clearSensitiveData().then(() => {
        console.log('[SW] Cleared sensitive data on logout');
        event.source.postMessage({ type: 'SENSITIVE_DATA_CLEARED' });
      });
      break;

    // Panic alert handling (integrated from panic-alert-sw.js)
    case 'PANIC_ALERT':
      handlePanicAlert(event.data).then(() => {
        console.log('[SW] Panic alert processed');
      });
      break;

    default:
      console.log('[SW] Unknown message type:', type);
  }
});

// ==================== Background Sync Event ====================

self.addEventListener('sync', (event) => {
  console.log('[SW] Background sync triggered:', event.tag);

  if (event.tag === 'circulation-sync') {
    event.waitUntil(syncOfflineQueue());
  } else if (event.tag === 'sync-panic-alerts') {
    event.waitUntil(syncPendingPanicAlerts());
  }
});

// ==================== Helper Functions ====================

/**
 * SECURITY: Check if the endpoint contains sensitive data that must never be cached
 * This includes patron PII, session tokens, financial data, etc.
 */
function isSensitiveEndpoint(url) {
  if (!isAPIRequest(url)) return false;
  const fullUrl = url.pathname + url.search;
  return SENSITIVE_ENDPOINT_PATTERNS.some((pattern) => pattern.test(fullUrl));
}

/**
 * SECURITY: Check if response headers indicate the data should not be cached
 * Respects Cache-Control: no-store, no-cache directives from the server
 */
function shouldNotCacheResponse(response) {
  const cacheControl = response.headers.get('Cache-Control');
  if (!cacheControl) return false;

  const noCacheDirectives = ['no-store', 'no-cache', 'private'];
  return noCacheDirectives.some((directive) => cacheControl.includes(directive));
}

/**
 * Check if the request is a navigation (the browser asking for a document).
 * Catches typed URLs, clicked links, and refreshes — anything where the
 * user expects the latest HTML, not whatever happened to be cached.
 */
function isNavigationRequest(request) {
  return request.mode === 'navigate' || request.destination === 'document';
}

/**
 * Check if the request is for a static asset
 */
function isStaticAsset(url) {
  const staticExtensions = ['.js', '.css', '.png', '.jpg', '.jpeg', '.gif', '.svg', '.ico', '.webp'];
  const pathname = url.pathname;

  // Check for Vite/bundled assets
  if (pathname.startsWith('/assets/')) return true;

  // Check file extensions
  // Excludes .html on purpose: HTML is served via the navigation handler
  // (network-first), never cache-first.
  return staticExtensions.some((ext) => pathname.endsWith(ext));
}

/**
 * Check if the request is for a font
 */
function isFontRequest(url) {
  const fontExtensions = ['.woff', '.woff2', '.ttf', '.otf', '.eot'];
  const fontHosts = ['fonts.googleapis.com', 'fonts.gstatic.com'];

  if (fontHosts.includes(url.hostname)) return true;
  return fontExtensions.some((ext) => url.pathname.endsWith(ext));
}

/**
 * Check if the request is an API request
 */
function isAPIRequest(url) {
  return url.pathname.startsWith('/api/');
}

/**
 * Check if the API request should be cached
 */
function isCacheableAPI(url) {
  if (!isAPIRequest(url)) return false;
  return CACHEABLE_API_PATTERNS.some((pattern) => pattern.test(url.pathname));
}

/**
 * Check if the API request should use stale-while-revalidate
 */
function isStaleWhileRevalidateAPI(url) {
  if (!isAPIRequest(url)) return false;
  const fullUrl = url.pathname + url.search;
  return STALE_WHILE_REVALIDATE_PATTERNS.some((pattern) => pattern.test(fullUrl));
}

/**
 * Check if this is a circulation operation (checkout/checkin)
 */
function isCirculationOperation(request) {
  if (request.method !== 'POST') return false;

  const url = new URL(request.url);
  const apiBase = setApiBaseFromUrl(url);
  if (!apiBase) return false;

  const circulationEndpoints = [
    `${apiBase}/staff/checkout`,
    `${apiBase}/staff/checkin-barcode`,
    `${apiBase}/circulation/checkout`,
    `${apiBase}/circulation/checkin`,
  ];

  return circulationEndpoints.some((endpoint) => url.pathname.includes(endpoint));
}

// ==================== Caching Strategies ====================

/**
 * Cache-first strategy: Try cache, fallback to network
 * Best for static assets that don't change often
 */
async function cacheFirstStrategy(request, cacheName) {
  try {
    const cachedResponse = await caches.match(request);
    if (cachedResponse) {
      return cachedResponse;
    }

    const networkResponse = await fetch(request);

    // Cache successful responses
    if (networkResponse.ok) {
      const cache = await caches.open(cacheName);
      cache.put(request, networkResponse.clone());
    }

    return networkResponse;
  } catch (error) {
    console.error('[SW] Cache-first strategy failed:', error);

    // Return cached response if available, even if stale
    const cachedResponse = await caches.match(request);
    if (cachedResponse) {
      return cachedResponse;
    }

    // Return offline fallback for HTML requests
    if (request.headers.get('Accept')?.includes('text/html')) {
      return createOfflineFallbackResponse();
    }

    throw error;
  }
}

/**
 * Network-first strategy: Try network, fallback to cache
 * Best for API data that should be fresh but available offline
 *
 * SECURITY: Respects Cache-Control headers from the server.
 * If response includes no-store/no-cache, it will not be cached.
 */
/**
 * Network-first for navigation: always try network so users see fresh HTML
 * after a deploy. Cache the response into STATIC_CACHE so the cached app
 * shell can serve when the network is offline. On network failure, fall
 * back to the cached HTML or to the offline page.
 *
 * Caches the *request* under '/' so any future navigation gets the same
 * fallback, regardless of URL path -- SPA routing means '/' renders
 * whatever the user wanted anyway.
 */
async function networkFirstNavigationStrategy(request) {
  try {
    const networkResponse = await fetch(request);
    if (networkResponse.ok) {
      const cache = await caches.open(STATIC_CACHE);
      // Cache under '/' so the offline fallback works for any client-side route
      cache.put('/', networkResponse.clone());
    }
    return networkResponse;
  } catch (error) {
    console.warn('[SW] Network failed for navigation; falling back to cached shell:', error);
    const cached = (await caches.match('/')) || (await caches.match(request));
    if (cached) return cached;
    return createOfflineFallbackResponse();
  }
}

async function networkFirstStrategy(request) {
  try {
    const networkResponse = await fetch(request);

    // SECURITY: Only cache if response doesn't have no-store/no-cache directives
    // This respects server-side cache control for sensitive data
    if (networkResponse.ok && !shouldNotCacheResponse(networkResponse)) {
      const cache = await caches.open(API_CACHE);
      cache.put(request, networkResponse.clone());
    }

    return networkResponse;
  } catch (error) {
    console.log('[SW] Network failed, trying cache:', request.url);

    const cachedResponse = await caches.match(request);
    if (cachedResponse) {
      // Add header to indicate this is from cache
      const headers = new Headers(cachedResponse.headers);
      headers.set('X-SW-Cache', 'true');
      headers.set('X-SW-Cache-Date', cachedResponse.headers.get('date') || 'unknown');

      return new Response(cachedResponse.body, {
        status: cachedResponse.status,
        statusText: cachedResponse.statusText,
        headers,
      });
    }

    // Return offline error response for API requests
    return createOfflineAPIResponse(error.message);
  }
}

/**
 * Stale-while-revalidate strategy: Return cache immediately, update in background
 * Best for data that can be slightly stale
 *
 * SECURITY: Respects Cache-Control headers from the server.
 * If response includes no-store/no-cache, it will not be cached.
 */
async function staleWhileRevalidateStrategy(request) {
  const cache = await caches.open(API_CACHE);
  const cachedResponse = await cache.match(request);

  // Start network request in background
  const networkPromise = fetch(request)
    .then((response) => {
      // SECURITY: Only cache if response doesn't have no-store/no-cache directives
      if (response.ok && !shouldNotCacheResponse(response)) {
        cache.put(request, response.clone());
      }
      return response;
    })
    .catch((error) => {
      console.log('[SW] Background revalidation failed:', error);
      return null;
    });

  // If we have a cached response, return it immediately
  if (cachedResponse) {
    // Fire and forget the network request
    networkPromise;

    // Add header to indicate this might be stale
    const headers = new Headers(cachedResponse.headers);
    headers.set('X-SW-Cache', 'stale-while-revalidate');

    return new Response(cachedResponse.body, {
      status: cachedResponse.status,
      statusText: cachedResponse.statusText,
      headers,
    });
  }

  // No cache, wait for network
  const networkResponse = await networkPromise;
  if (networkResponse) {
    return networkResponse;
  }

  return createOfflineAPIResponse('No cached data available');
}

// ==================== Offline Queue Management ====================

/**
 * Handle circulation operations (checkout/checkin) with offline support
 */
async function handleCirculationOperation(request) {
  try {
    // Try network first
    const response = await fetch(request.clone());
    return response;
  } catch (error) {
    console.log('[SW] Circulation operation failed, queueing for later:', error);

    // Queue the operation for later
    try {
      const body = await request.clone().json();
      const queuedOperation = {
        id: generateId(),
        url: request.url,
        method: request.method,
        body,
        headers: Object.fromEntries(request.headers.entries()),
        timestamp: new Date().toISOString(),
        retryCount: 0,
      };

      await addToOfflineQueue(queuedOperation);

      // Register for background sync if available
      if ('sync' in self.registration) {
        await self.registration.sync.register('circulation-sync');
      }

      // Return a success response indicating the operation was queued
      return new Response(
        JSON.stringify({
          queued: true,
          message: 'Operation queued for sync when back online',
          queueId: queuedOperation.id,
          ...createOptimisticResponse(request.url, body),
        }),
        {
          status: 202, // Accepted
          headers: {
            'Content-Type': 'application/json',
            'X-SW-Queued': 'true',
          },
        }
      );
    } catch (queueError) {
      console.error('[SW] Failed to queue operation:', queueError);
      return createOfflineAPIResponse('Failed to queue operation');
    }
  }
}

/**
 * Add operation to offline queue
 */
async function addToOfflineQueue(operation) {
  const queue = await getOfflineQueue();
  queue.push(operation);
  await saveOfflineQueue(queue);

  // Notify clients
  const clients = await self.clients.matchAll();
  clients.forEach((client) => {
    client.postMessage({
      type: 'OPERATION_QUEUED',
      operation: {
        id: operation.id,
        url: operation.url,
        timestamp: operation.timestamp,
      },
    });
  });
}

/**
 * Get offline queue from IndexedDB
 */
async function getOfflineQueue() {
  try {
    const db = await openDatabase();
    return new Promise((resolve, reject) => {
      const transaction = db.transaction(['offlineQueue'], 'readonly');
      const store = transaction.objectStore('offlineQueue');
      const request = store.getAll();

      request.onsuccess = () => resolve(request.result || []);
      request.onerror = () => reject(request.error);
    });
  } catch (error) {
    console.error('[SW] Failed to get offline queue:', error);
    return [];
  }
}

/**
 * Save offline queue to IndexedDB
 */
async function saveOfflineQueue(queue) {
  try {
    const db = await openDatabase();
    return new Promise((resolve, reject) => {
      const transaction = db.transaction(['offlineQueue'], 'readwrite');
      const store = transaction.objectStore('offlineQueue');

      // Clear existing entries
      store.clear();

      // Add all items
      queue.forEach((item) => store.add(item));

      transaction.oncomplete = () => resolve();
      transaction.onerror = () => reject(transaction.error);
    });
  } catch (error) {
    console.error('[SW] Failed to save offline queue:', error);
  }
}

/**
 * Open IndexedDB database
 */
function openDatabase() {
  return new Promise((resolve, reject) => {
    const request = indexedDB.open('lsc-service-worker', 1);

    request.onerror = () => reject(request.error);
    request.onsuccess = () => resolve(request.result);

    request.onupgradeneeded = (event) => {
      const db = event.target.result;
      if (!db.objectStoreNames.contains('offlineQueue')) {
        db.createObjectStore('offlineQueue', { keyPath: 'id' });
      }
    };
  });
}

/**
 * Sync offline queue when back online
 */
async function syncOfflineQueue() {
  console.log('[SW] Starting offline queue sync');

  const queue = await getOfflineQueue();
  if (queue.length === 0) {
    console.log('[SW] No operations to sync');
    return { synced: 0, failed: 0, remaining: 0 };
  }

  let synced = 0;
  let failed = 0;
  const failedOperations = [];

  for (const operation of queue) {
    try {
      const response = await fetch(operation.url, {
        method: operation.method,
        headers: {
          'Content-Type': 'application/json',
          ...operation.headers,
        },
        body: JSON.stringify(operation.body),
      });

      if (response.ok) {
        synced++;
        console.log('[SW] Synced operation:', operation.id);

        // Notify clients of successful sync
        const clients = await self.clients.matchAll();
        const responseData = await response.json();
        clients.forEach((client) => {
          client.postMessage({
            type: 'OPERATION_SYNCED',
            operation: {
              id: operation.id,
              url: operation.url,
            },
            response: responseData,
          });
        });
      } else {
        throw new Error(`HTTP ${response.status}`);
      }
    } catch (error) {
      console.error('[SW] Failed to sync operation:', operation.id, error);

      operation.retryCount = (operation.retryCount || 0) + 1;
      operation.lastError = error.message;
      operation.lastRetry = new Date().toISOString();

      // Keep retrying up to 5 times
      if (operation.retryCount < 5) {
        failedOperations.push(operation);
      } else {
        failed++;
        // Notify clients of permanent failure
        const clients = await self.clients.matchAll();
        clients.forEach((client) => {
          client.postMessage({
            type: 'OPERATION_FAILED',
            operation: {
              id: operation.id,
              url: operation.url,
              error: error.message,
            },
          });
        });
      }
    }
  }

  // Save remaining operations
  await saveOfflineQueue(failedOperations);

  const result = {
    synced,
    failed,
    remaining: failedOperations.length,
  };

  console.log('[SW] Sync complete:', result);

  // Notify all clients
  const clients = await self.clients.matchAll();
  clients.forEach((client) => {
    client.postMessage({ type: 'SYNC_COMPLETE', ...result });
  });

  return result;
}

/**
 * Get queue status
 */
async function getQueueStatus() {
  const queue = await getOfflineQueue();
  return {
    count: queue.length,
    operations: queue.map((op) => ({
      id: op.id,
      url: op.url,
      timestamp: op.timestamp,
      retryCount: op.retryCount || 0,
    })),
  };
}

// ==================== Utility Functions ====================

/**
 * Generate unique ID
 */
function generateId() {
  return `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
}

/**
 * Create optimistic response for queued operations
 */
function createOptimisticResponse(url, body) {
  // Checkout operation
  if (url.includes('/checkout')) {
    return {
      id: -Date.now(), // Temporary negative ID
      status: 'active',
      checked_out_at: new Date().toISOString(),
      due_date: new Date(Date.now() + 21 * 24 * 60 * 60 * 1000).toISOString(), // 21 days from now
      item_title: 'Pending sync...',
      offline_checkout: true,
    };
  }

  // Check-in operation
  if (url.includes('/checkin')) {
    return {
      message: 'Check-in queued (will sync when online)',
      checkout: {
        status: 'returned',
        returned_at: new Date().toISOString(),
      },
      offline_checkin: true,
    };
  }

  return {};
}

/**
 * Create offline fallback HTML response
 */
function createOfflineFallbackResponse() {
  const html = `
    <!DOCTYPE html>
    <html lang="en">
    <head>
      <meta charset="UTF-8">
      <meta name="viewport" content="width=device-width, initial-scale=1.0">
      <title>Offline - L30 Library</title>
      <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
          font-family: 'Atkinson Hyperlegible', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
          min-height: 100vh;
          display: flex;
          align-items: center;
          justify-content: center;
          background: #faf9f6;
          color: #2d2d2d;
          padding: 2rem;
        }
        .container {
          text-align: center;
          max-width: 500px;
        }
        h1 {
          font-family: 'Lora', Georgia, serif;
          font-size: 2rem;
          margin-bottom: 1rem;
          color: #e07d4c;
        }
        p {
          margin-bottom: 1rem;
          line-height: 1.6;
        }
        .icon {
          font-size: 4rem;
          margin-bottom: 1.5rem;
        }
        button {
          background: #e07d4c;
          color: white;
          border: none;
          padding: 0.75rem 1.5rem;
          border-radius: 2rem;
          font-size: 1rem;
          cursor: pointer;
          margin-top: 1rem;
        }
        button:hover {
          background: #c66a3d;
        }
      </style>
    </head>
    <body>
      <div class="container">
        <div class="icon">&#128214;</div>
        <h1>You're Offline</h1>
        <p>It looks like you've lost your internet connection. Don't worry - any checkout or check-in operations you perform will be saved and synced automatically when you're back online.</p>
        <p>You can still access recently viewed pages and patron information that has been cached.</p>
        <button onclick="location.reload()">Try Again</button>
      </div>
    </body>
    </html>
  `;

  return new Response(html, {
    status: 200,
    headers: { 'Content-Type': 'text/html' },
  });
}

/**
 * Create offline API error response
 */
function createOfflineAPIResponse(message = 'You are offline') {
  return new Response(
    JSON.stringify({
      error: 'offline',
      message,
      offline: true,
    }),
    {
      status: 503,
      headers: {
        'Content-Type': 'application/json',
        'X-SW-Offline': 'true',
      },
    }
  );
}

/**
 * Clear all caches
 */
async function clearAllCaches() {
  const cacheNames = await caches.keys();
  await Promise.all(cacheNames.map((name) => caches.delete(name)));
  console.log('[SW] All caches cleared');
}

/**
 * SECURITY: Clear sensitive data from caches on logout
 *
 * This function is called when the user logs out to ensure no sensitive
 * data remains in browser storage. It clears:
 * - All API cache entries (may contain authenticated responses)
 * - Offline queue data (may contain patron identifiers)
 *
 * Static assets and fonts are preserved as they contain no sensitive data.
 */
async function clearSensitiveData() {
  console.log('[SW] Clearing sensitive data from caches');

  try {
    // Clear the entire API cache (safest approach - ensures no sensitive data persists)
    const apiCacheDeleted = await caches.delete(API_CACHE);
    if (apiCacheDeleted) {
      console.log('[SW] API cache cleared');
    }

    // Re-create an empty API cache for future use
    await caches.open(API_CACHE);

    // Clear offline queue which may contain patron identifiers
    await clearOfflineQueue();

    console.log('[SW] Sensitive data cleared successfully');
  } catch (error) {
    console.error('[SW] Error clearing sensitive data:', error);
    // Even if there's an error, try to clear the API cache directly
    try {
      await caches.delete(API_CACHE);
    } catch (e) {
      console.error('[SW] Failed to delete API cache:', e);
    }
  }
}

/**
 * Clear the offline queue
 */
async function clearOfflineQueue() {
  try {
    const db = await openDatabase();
    return new Promise((resolve, reject) => {
      const transaction = db.transaction(['offlineQueue'], 'readwrite');
      const store = transaction.objectStore('offlineQueue');
      const request = store.clear();

      request.onsuccess = () => {
        console.log('[SW] Offline queue cleared');
        resolve();
      };
      request.onerror = () => {
        console.error('[SW] Failed to clear offline queue:', request.error);
        reject(request.error);
      };
    });
  } catch (error) {
    console.error('[SW] Failed to clear offline queue:', error);
  }
}

// ==================== Panic Alert Support ====================

/**
 * Handle incoming panic alert
 * Stores locally and ensures it's sent to backend
 */
async function handlePanicAlert(alertData) {
  try {
    await storePanicAlertLocally(alertData);

    if (navigator.onLine) {
      await sendPanicAlertToBackend(alertData);
    } else {
      self.addEventListener('online', () => {
        sendPanicAlertToBackend(alertData);
      }, { once: true });
    }
  } catch (error) {
    console.error('[SW] Error handling panic alert:', error);
  }
}

/**
 * Store panic alert locally for recovery
 */
async function storePanicAlertLocally(alertData) {
  try {
    const db = await openPanicAlertDatabase();
    return new Promise((resolve, reject) => {
      const tx = db.transaction('panicAlerts', 'readwrite');
      const store = tx.objectStore('panicAlerts');
      store.add({
        ...alertData,
        storedAt: new Date().toISOString(),
        status: 'pending',
      });
      tx.oncomplete = () => resolve();
      tx.onerror = () => reject(tx.error);
    });
  } catch (error) {
    console.error('[SW] Error storing panic alert locally:', error);
  }
}

/**
 * Send panic alert to backend
 */
async function sendPanicAlertToBackend(alertData) {
  try {
    const response = await fetch(`${API_BASE}/panic-alerts`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        activation_source: alertData.activation_source || 'hidden_ui_button',
        situation_notes: alertData.situation_notes,
        metadata: {
          ...alertData.metadata,
          sentViaServiceWorker: true,
          timestamp: new Date().toISOString(),
        },
      }),
    });

    if (response.ok) {
      const data = await response.json();
      console.log('[SW] Panic alert sent successfully:', data.id);

      await markPanicAlertAsSent(alertData.alertId);

      const clients = await self.clients.matchAll();
      clients.forEach((client) => {
        client.postMessage({
          type: 'PANIC_ALERT_SENT',
          alertId: data.id,
        });
      });
      return true;
    } else {
      console.error('[SW] Failed to send panic alert:', response.status);
      return false;
    }
  } catch (error) {
    console.error('[SW] Error sending panic alert to backend:', error);
    return false;
  }
}

/**
 * Mark panic alert as sent in IndexedDB
 */
async function markPanicAlertAsSent(alertId) {
  try {
    const db = await openPanicAlertDatabase();
    return new Promise((resolve, reject) => {
      const tx = db.transaction('panicAlerts', 'readwrite');
      const store = tx.objectStore('panicAlerts');
      const request = store.getAll();
      request.onsuccess = () => {
        const records = request.result || [];
        const record = records.find((r) => r.alertId === alertId);
        if (record) {
          record.status = 'sent';
          store.put(record);
        }
        resolve();
      };
      request.onerror = () => reject(request.error);
    });
  } catch (error) {
    console.error('[SW] Error marking panic alert as sent:', error);
  }
}

/**
 * Open IndexedDB for panic alerts
 */
function openPanicAlertDatabase() {
  return new Promise((resolve, reject) => {
    const request = indexedDB.open('PanicAlerts', 1);
    request.onerror = () => reject(request.error);
    request.onsuccess = () => resolve(request.result);
    request.onupgradeneeded = (event) => {
      const db = event.target.result;
      if (!db.objectStoreNames.contains('panicAlerts')) {
        db.createObjectStore('panicAlerts', { keyPath: 'id', autoIncrement: true });
      }
    };
  });
}

/**
 * Sync any pending panic alerts that haven't been sent yet
 */
async function syncPendingPanicAlerts() {
  try {
    const db = await openPanicAlertDatabase();
    const alerts = await new Promise((resolve, reject) => {
      const tx = db.transaction('panicAlerts', 'readonly');
      const store = tx.objectStore('panicAlerts');
      const request = store.getAll();
      request.onsuccess = () => resolve(request.result || []);
      request.onerror = () => reject(request.error);
    });

    const pending = alerts.filter((a) => a.status === 'pending');
    for (const alert of pending) {
      await sendPanicAlertToBackend(alert);
    }
  } catch (error) {
    console.error('[SW] Error syncing pending panic alerts:', error);
  }
}

console.log('[SW] Service worker script loaded, version:', CACHE_VERSION);
// ============================================================================
// Push Notification Handling - SOS/Panic Alert Aware
// ============================================================================

self.addEventListener('push', (event) => {
  if (!event.data) return

  const data = event.data.json()
  const isSOS = data.tag === 'panic-alert' || data.alertType === 'panic_alert'

  const options = {
    body: data.body || 'Emergency alert triggered',
    icon: '/icon-192x192.png',
    badge: '/badge-72x72.png',
    vibrate: isSOS ? [200, 100, 200, 100, 200, 100, 200] : [100, 50, 100],
    tag: data.tag || (isSOS ? 'panic-alert' : 'general'),
    renotify: isSOS,
    requireInteraction: isSOS,
    silent: false,
    data: {
      dateOfArrival: Date.now(),
      url: data.url || '/',
      alertId: data.alertId,
    },
    actions: isSOS
      ? [
          { action: 'respond', title: 'Respond Now' },
          { action: 'dismiss', title: 'Dismiss' },
        ]
      : [
          { action: 'view', title: 'View' },
          { action: 'close', title: 'Close' },
        ],
  }

  event.waitUntil(self.registration.showNotification(data.title || 'Alert', options))
})

self.addEventListener('notificationclick', (event) => {
  event.notification.close()

  const data = event.notification.data || {}
  let targetUrl = '/'

  if (event.action === 'respond' || event.notification.tag === 'panic-alert') {
    targetUrl = '/staff/panic-alerts'
  } else if (data.url) {
    targetUrl = data.url
  }

  event.waitUntil(
    clients.matchAll({ type: 'window', includeUncontrolled: true }).then((clientList) => {
      for (const client of clientList) {
        if (client.url.includes(self.location.origin) && 'focus' in client) {
          client.navigate(targetUrl)
          return client.focus()
        }
      }
      return clients.openWindow(targetUrl)
    })
  )
})
