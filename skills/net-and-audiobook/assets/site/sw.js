/* Cache the application shell, never media, range requests, error pages or HTML fallbacks for assets. */
const PREFIX = "nba-__PROJECT_ID__-", CACHE = PREFIX + "__BUILD_VERSION__";
const SHELL = ["./index.html", "./styles.css", "./app.js", "./project.js", "./app.webmanifest", "./audiobook/index.html", "./audiobook/app.js", "./audiobook/catalog.js"];
self.addEventListener("install", e => { e.waitUntil(caches.open(CACHE).then(c => c.addAll(SHELL)).then(() => self.skipWaiting())); });
self.addEventListener("activate", e => { e.waitUntil(caches.keys().then(keys => Promise.all(keys.filter(k => k.startsWith(PREFIX) && k !== CACHE).map(k => caches.delete(k)))).then(() => self.clients.claim())); });
self.addEventListener("fetch", e => {
  const r = e.request, u = new URL(r.url);
  if (r.method !== "GET" || r.headers.has("range") || u.origin !== self.location.origin || /\.(mp3|wav|zip|m3u8|pdf)$/i.test(u.pathname) || /\/audiobook\/(catalog\.json|scripts\/)/.test(u.pathname)) return;
  // Only cache the declared shell. Source crops remain honest network/file requests.
  const allowed = SHELL.some(path => new URL(path, self.registration.scope).pathname === u.pathname) || u.pathname === new URL("./", self.registration.scope).pathname;
  if (!allowed) return;
  e.respondWith(fetch(r).then(response => {
    if (response.ok && response.type === "basic") { const copy = response.clone(); e.waitUntil(caches.open(CACHE).then(c => c.put(r, copy))); }
    return response;
  }).catch(async () => (await caches.match(r)) || (r.mode === "navigate" ? await caches.match(new URL("./index.html", self.registration.scope).href) : Response.error())));
});
