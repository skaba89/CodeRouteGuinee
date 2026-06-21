/**
 * Service Worker — CodeRoute Guinée
 *
 * Stratégie de cache :
 *   - App shell (HTML/CSS/JS) : Cache First, fallback réseau
 *   - API /api/v1/ : Network First, pas de cache (données en temps réel)
 *   - Questions entraînement : Cache avec revalidation (200 questions stables)
 *   - Assets statiques (fonts, images) : Cache long terme (stale-while-revalidate)
 *
 * Permet :
 *   - Navigation offline sur les pages déjà visitées
 *   - Entraînement offline (questions en cache)
 *   - Installation PWA sur Android/iOS sans app store
 */

const CACHE_VERSION = 'v1';
const SHELL_CACHE   = `coderoute-shell-${CACHE_VERSION}`;
const ASSETS_CACHE  = `coderoute-assets-${CACHE_VERSION}`;
const QUESTIONS_CACHE = `coderoute-questions-${CACHE_VERSION}`;

// ── App shell à pré-cacher ────────────────────────────────────────
const SHELL_URLS = [
  '/',
  '/index.html',
];

// ── Install : pré-cache l'app shell ──────────────────────────────
self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(SHELL_CACHE)
      .then(cache => cache.addAll(SHELL_URLS))
      .then(() => self.skipWaiting())
  );
});

// ── Activate : purger les anciens caches ─────────────────────────
self.addEventListener('activate', event => {
  event.waitUntil(
    caches.keys().then(keys =>
      Promise.all(
        keys
          .filter(k => ![SHELL_CACHE, ASSETS_CACHE, QUESTIONS_CACHE].includes(k))
          .map(k => caches.delete(k))
      )
    ).then(() => self.clients.claim())
  );
});

// ── Fetch : stratégie par type de ressource ───────────────────────
self.addEventListener('fetch', event => {
  const url = new URL(event.request.url);

  // API : toujours réseau, jamais cache (données temps réel)
  if (url.pathname.startsWith('/api/')) {
    event.respondWith(fetch(event.request));
    return;
  }

  // Questions entraînement : cache avec revalidation en arrière-plan
  if (url.pathname.startsWith('/api/v1/training/questions')) {
    event.respondWith(staleWhileRevalidate(QUESTIONS_CACHE, event.request));
    return;
  }

  // Assets hashés (JS/CSS avec hash dans le nom) : cache long terme
  if (/\.(js|css|woff2|png|svg|ico)$/.test(url.pathname)) {
    event.respondWith(cacheFirst(ASSETS_CACHE, event.request));
    return;
  }

  // App shell : cache first, fallback vers /index.html pour SPA
  event.respondWith(
    cacheFirst(SHELL_CACHE, event.request)
      .catch(() => caches.match('/index.html'))
  );
});

// ── Stratégies de cache ───────────────────────────────────────────

async function cacheFirst(cacheName, request) {
  const cached = await caches.match(request);
  if (cached) return cached;
  const response = await fetch(request);
  if (response.ok) {
    const cache = await caches.open(cacheName);
    cache.put(request, response.clone());
  }
  return response;
}

async function staleWhileRevalidate(cacheName, request) {
  const cache = await caches.open(cacheName);
  const cached = await cache.match(request);

  // Lancer la revalidation en arrière-plan
  const networkFetch = fetch(request).then(response => {
    if (response.ok) cache.put(request, response.clone());
    return response;
  }).catch(() => null);

  // Retourner immédiatement le cache si disponible, sinon attendre le réseau
  return cached || networkFetch;
}

// ── Message : forcer la mise à jour ──────────────────────────────
self.addEventListener('message', event => {
  if (event.data?.type === 'SKIP_WAITING') self.skipWaiting();
});

// ── Push notifications (convocations J-48h) ───────────────────────
self.addEventListener('push', event => {
  if (!event.data) return;
  const data = event.data.json();
  event.waitUntil(
    self.registration.showNotification(data.title || 'CodeRoute Guinée', {
      body:    data.body  || 'Notification CodeRoute',
      icon:    '/icon-192.png',
      badge:   '/badge-72.png',
      tag:     data.tag   || 'coderoute',
      data:    data.url   ? { url: data.url } : {},
      actions: data.actions || [],
      vibrate: [200, 100, 200],
    })
  );
});

// Clic sur notification → ouvrir la bonne page
self.addEventListener('notificationclick', event => {
  event.notification.close();
  const url = event.notification.data?.url || '/';
  event.waitUntil(
    clients.matchAll({ type: 'window' }).then(wins => {
      const existing = wins.find(w => w.url === url);
      if (existing) return existing.focus();
      return clients.openWindow(url);
    })
  );
});
