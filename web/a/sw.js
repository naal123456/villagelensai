const SHARED_IMAGE = '/a/shared-image';
const SHARED_CACHE = 'villagelens-shared-image-v1';
const APP_VERSION = '2026-09-10.2';

self.addEventListener('install', event => {
  event.waitUntil(self.skipWaiting());
});

self.addEventListener('activate', event => {
  event.waitUntil((async () => {
    await self.clients.claim();
    const clients = await self.clients.matchAll({type: 'window'});
    clients.forEach(client => client.postMessage({type: 'APP_UPDATED', version: APP_VERSION}));
  })());
});

self.addEventListener('fetch', event => {
  const url = new URL(event.request.url);
  if (event.request.method === 'POST' && url.pathname === '/a/share-target') {
    event.respondWith((async () => {
      const form = await event.request.formData();
      const image = form.get('image');
      if (!(image instanceof Blob) || !image.type.startsWith('image/')) {
        return Response.redirect(new URL('/a/?share-error=1', self.location.origin), 303);
      }
      const cache = await caches.open(SHARED_CACHE);
      await cache.put(SHARED_IMAGE, new Response(image, {
        headers: {'Content-Type': image.type || 'image/jpeg', 'Cache-Control': 'no-store'}
      }));
      return Response.redirect(new URL('/a/?shared=1', self.location.origin), 303);
    })());
    return;
  }
  if (event.request.method === 'GET' && url.pathname === SHARED_IMAGE) {
    event.respondWith((async () => {
      const cache = await caches.open(SHARED_CACHE);
      const response = await cache.match(SHARED_IMAGE);
      if (!response) return new Response('', {status: 404});
      const copy = response.clone();
      await cache.delete(SHARED_IMAGE);
      return copy;
    })());
  }
});
