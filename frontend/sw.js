/* Le Coupon - service worker
   Reseau d'abord pour la page (mises a jour immediates quand tu es en ligne),
   cache de secours hors-ligne, et l'IA (/api/) passe toujours par le reseau. */
const CACHE = 'lecoupon-v1';
const SHELL = ['/', '/static/manifest.json', '/static/icon-192.png', '/static/icon-512.png'];

self.addEventListener('install', e => {
  self.skipWaiting();
  e.waitUntil(caches.open(CACHE).then(c => c.addAll(SHELL).catch(() => {})));
});

self.addEventListener('activate', e => {
  e.waitUntil(
    caches.keys().then(ks => Promise.all(ks.filter(k => k !== CACHE).map(k => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', e => {
  const req = e.request;
  if (req.method !== 'GET') return;
  const url = new URL(req.url);
  if (url.pathname.startsWith('/api/')) return; // IA en direct, jamais en cache
  if (req.mode === 'navigate') {
    e.respondWith(
      fetch(req).then(r => { const cp = r.clone(); caches.open(CACHE).then(c => c.put('/', cp)); return r; })
        .catch(() => caches.match('/'))
    );
    return;
  }
  e.respondWith(
    caches.match(req).then(c => c || fetch(req).then(r => {
      if (r.ok && url.origin === location.origin) { const cp = r.clone(); caches.open(CACHE).then(ch => ch.put(req, cp)); }
      return r;
    }))
  );
});
