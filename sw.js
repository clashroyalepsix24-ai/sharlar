/* Sharlar Saralash — service worker (network-first for HTML, offline-capable) */
const CACHE = "sharlar-v8";
const ASSETS = [
  "./",
  "./index.html",
  "./manifest.webmanifest",
  "./icon-192.png",
  "./icon-512.png",
  "./icon-192-maskable.png",
  "./icon-512-maskable.png",
  "./apple-touch-icon.png",
  "./favicon-64.png"
];

self.addEventListener("install", function(e){
  e.waitUntil(
    caches.open(CACHE).then(function(c){ return c.addAll(ASSETS); }).then(function(){ return self.skipWaiting(); })
  );
});

self.addEventListener("activate", function(e){
  e.waitUntil(
    caches.keys().then(function(keys){
      return Promise.all(keys.map(function(k){ if(k !== CACHE) return caches.delete(k); }));
    }).then(function(){ return self.clients.claim(); })
  );
});

self.addEventListener("fetch", function(e){
  const req = e.request;
  if(req.method !== "GET") return;

  const isNav = req.mode === "navigate" || req.destination === "document";
  if(isNav){
    // Network-first: always try the latest page when online; fall back to cache offline.
    e.respondWith(
      fetch(req).then(function(resp){
        const copy = resp.clone();
        caches.open(CACHE).then(function(c){ c.put("./index.html", copy); });
        return resp;
      }).catch(function(){
        return caches.match("./index.html").then(function(r){ return r || caches.match("./"); });
      })
    );
    return;
  }

  // Other assets: stale-while-revalidate (instant from cache, refresh in background).
  e.respondWith(
    caches.match(req, { ignoreSearch: true }).then(function(cached){
      const net = fetch(req).then(function(resp){
        caches.open(CACHE).then(function(c){ try{ c.put(req, resp.clone()); }catch(err){} });
        return resp;
      }).catch(function(){ return cached; });
      return cached || net;
    })
  );
});
