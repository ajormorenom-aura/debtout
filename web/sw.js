/* DebtOut service worker.
   Keeps a copy of the app's own files (code, font, icons) and of the home page so they open fast and work offline.
   It never stores or sends personal data: your plan lives only in this device's local storage. */
"use strict";
var BUILD = "0.10.0-d19ecbe345";
var CACHE = "debtout-app-" + BUILD;
var CORE = ["./", "app/", "manifest.webmanifest", "datos-titular.js", "fonts/inter-400.v1.woff", "fonts/inter-600.v1.woff", "fonts/inter-700.v1.woff", "fonts/inter-800.v1.woff", "fonts/inter-display-600.v1.woff", "fonts/inter-display-700.v1.woff", "icons/favicon.svg", "icons/favicon-32.png", "icons/apple-touch-icon.png", "icons/icon-192.png"];
var NET_TIMEOUT = 3500;

self.addEventListener("install", function (event) {
  event.waitUntil(caches.open(CACHE).then(function (cache) {
    return Promise.all(CORE.map(function (url) {
      return cache.add(new Request(url, { cache: "reload" })).catch(function () { /* optional file */ });
    }));
  }).then(function () { return self.skipWaiting(); }));
});

self.addEventListener("activate", function (event) {
  event.waitUntil(caches.keys().then(function (keys) {
    return Promise.all(keys.filter(function (k) { return k.indexOf("debtout-app-") === 0 && k !== CACHE; })
      .map(function (k) { return caches.delete(k); }));
  }).then(function () { return self.clients.claim(); }));
});

function keep(key, res) {
  if (!res || !res.ok || res.type !== "basic") return;
  var copy = res.clone();
  caches.open(CACHE).then(function (cache) { return cache.put(key, copy); }).catch(function () {});
}

/* Fresh when online (so a new deploy shows up on the next open), cached when offline or slow. */
function networkFirst(request, key, fallback) {
  var net = fetch(request).then(function (res) { keep(key, res); return res; });
  var timer = new Promise(function (resolve) { setTimeout(resolve, NET_TIMEOUT, null); });
  return Promise.race([net.catch(function () { return null; }), timer]).then(function (res) {
    if (res) return res;
    return caches.match(key).then(function (hit) {
      if (hit) return hit;
      return net.catch(function (e) {
        return fallback ? caches.match(fallback).then(function (f) { if (f) return f; throw e; }) : Promise.reject(e);
      });
    });
  });
}

/* Fonts and icons never change under the same name. */
function cacheFirst(request) {
  return caches.match(request).then(function (hit) {
    return hit || fetch(request).then(function (res) { keep(request, res); return res; });
  });
}

self.addEventListener("fetch", function (event) {
  var req = event.request;
  if (req.method !== "GET") return;
  var url = new URL(req.url);
  if (url.origin !== self.location.origin) return;
  var scope = new URL(self.registration.scope);
  var app = new URL("app/", scope);
  if (req.mode === "navigate") {
    /* One cached copy per page, whatever the query string; offline, app pages fall back to the app. */
    var key = url.origin + url.pathname.replace(/index\.html$/, "");
    var inApp = url.pathname.indexOf(app.pathname) === 0;
    event.respondWith(networkFirst(req, key, inApp ? app.href : scope.href));
    return;
  }
  if (/\/(fonts|icons)\//.test(url.pathname)) { event.respondWith(cacheFirst(req)); return; }
  url.search = "";
  event.respondWith(networkFirst(req, url.href));
});
