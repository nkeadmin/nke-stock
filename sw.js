// Keeps the app shell available offline. The stock itself is fetched live and cached by the page.
var CACHE = 'nke-stock-v2';
var FILES = ['./', './index.html', './config.js', './xlsx.full.min.js', './manifest.webmanifest', './icon-192.png', './icon-512.png'];
self.addEventListener('install', function (e) { e.waitUntil(caches.open(CACHE).then(function (c) { return c.addAll(FILES); }).then(function () { return self.skipWaiting(); })); });
self.addEventListener('activate', function (e) { e.waitUntil(caches.keys().then(function (ks) { return Promise.all(ks.filter(function (k) { return k !== CACHE; }).map(function (k) { return caches.delete(k); })); }).then(function () { return self.clients.claim(); })); });
self.addEventListener('fetch', function (e) {
  var url = new URL(e.request.url);
  if (url.origin !== location.origin) return;            // other sites go straight to the network
  if (/stock[.]dat$/.test(url.pathname)) return;           // live stock: never cached here, the page keeps its own copy
  e.respondWith(fetch(e.request).then(function (r) { var copy = r.clone(); caches.open(CACHE).then(function (c) { c.put(e.request, copy); }); return r; })
    .catch(function () { return caches.match(e.request); }));
});
