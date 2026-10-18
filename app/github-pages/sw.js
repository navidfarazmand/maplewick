// Maplewick service worker: fresh game when online, saved copy when offline.
const CACHE = 'maplewick-11.10';
const FILES = ['./', './index.html', './manifest.webmanifest', './icon-192.png', './icon-512.png', './apple-touch-icon.png', './fb.js'];
self.addEventListener('install', (e) => { e.waitUntil(caches.open(CACHE).then((c) => c.addAll(FILES)).then(() => self.skipWaiting())); });
self.addEventListener('activate', (e) => { e.waitUntil(caches.keys().then((keys) => Promise.all(keys.filter((k) => k !== CACHE && !k.startsWith('mw-music')).map((k) => caches.delete(k)))).then(() => self.clients.claim())); });
self.addEventListener('fetch', (e) => {
  const req = e.request;
  if (req.method !== 'GET') return;
  const url = new URL(req.url);
  // Firebase, Google sign-in and other services: straight to the network, never cached.
  if (url.origin !== location.origin && !/^fonts\.(googleapis|gstatic)\.com$/.test(url.hostname)) return;
  const isPage = req.mode === 'navigate' || url.pathname.endsWith('.html') || url.pathname.endsWith('/');
  if (isPage) {
    // Network first, so a new version shows up as soon as it is pushed.
    e.respondWith(fetch(req).then((res) => { const copy = res.clone(); caches.open(CACHE).then((c) => c.put(req, copy)); return res; }).catch(() => caches.match(req).then((r) => r || caches.match('./index.html'))));
    return;
  }
  // Everything else (icons, fonts): saved copy first, then the network.
  e.respondWith(caches.match(req).then((hit) => hit || fetch(req).then((res) => {
    if (res.ok && (url.origin === location.origin || url.hostname.endsWith('gstatic.com') || url.hostname.endsWith('googleapis.com'))) { const copy = res.clone(); caches.open(CACHE).then((c) => c.put(req, copy)); }
    return res;
  }).catch(() => hit)));
});

// Tapping a focus-block notification opens Maplewick.
self.addEventListener('notificationclick', (e) => { e.notification.close(); e.waitUntil(self.clients.matchAll({ type: 'window', includeUncontrolled: true }).then((ws) => (ws.length ? ws[0].focus() : self.clients.openWindow('./')))); });
