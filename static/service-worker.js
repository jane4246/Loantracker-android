const CACHE_NAME = "loantrack-demo-v1";
// Do not cache authenticated pages or loan information on the device.
const APP_SHELL = ["/static/manifest.webmanifest", "/static/icon.svg", "/static/offline.html"];

self.addEventListener("install", event => event.waitUntil(caches.open(CACHE_NAME).then(cache => cache.addAll(APP_SHELL))));
self.addEventListener("activate", event => event.waitUntil(self.clients.claim()));
self.addEventListener("fetch", event => {
  if (event.request.method !== "GET") return;
  event.respondWith(fetch(event.request).catch(() => caches.match(event.request).then(hit => hit || caches.match("/static/offline.html"))));
});
