/* Le Coupon - service worker de nettoyage.
   Cette version annule l'ancien service worker qui gardait une vieille
   page en cache. Elle vide tous les caches, se desenregistre, puis
   recharge la page pour afficher la version en ligne, toujours a jour.
   Tes pronostics (stockage local) ne sont pas touches. */
self.addEventListener('install', () => self.skipWaiting());

self.addEventListener('activate', (e) => {
  e.waitUntil((async () => {
    try {
      const keys = await caches.keys();
      await Promise.all(keys.map(k => caches.delete(k)));
      await self.registration.unregister();
      const clients = await self.clients.matchAll({ type: 'window' });
      for (const c of clients) { try { c.navigate(c.url); } catch (_) {} }
    } catch (_) {}
  })());
});

/* Plus aucune interception: tout passe par le reseau. */
self.addEventListener('fetch', () => {});
