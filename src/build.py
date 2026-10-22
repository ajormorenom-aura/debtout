"""Build the DebtOut beta PWA into a folder that can be dropped on Netlify as-is.

Inputs (this folder): app.html (styles + markup + script), legal_beta.html.
Output: ../web (index.html, manifest, service worker, headers, 404 and, only if missing, the owner data file).
Usage: python3 src/build.py   (Netlify publishes the web/ folder as it is; there is no build step on Netlify.)
Fonts, icons and screenshots are produced by their own scripts into the same output folder.
"""
import hashlib, json, os, re, sys

SRC = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else os.path.join(SRC, "..", "web"))
VERSION = "0.9.0"

DESC = ("Reparte tu sueldo entre gastos fijos, deudas, ahorro y dinero libre, y mira cuándo "
        "terminarás de pagar tus deudas. Sin conectar tu banco. Gratis durante la beta.")
TITLE = "DebtOut · Tu plan para salir de deudas"


def read(p):
    with open(os.path.join(SRC, p), encoding="utf-8") as f:
        return f.read()


def write(rel, text):
    path = os.path.join(OUT, rel)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)


# ---------- legal texts ----------
legal_src = read("legal_beta.html")
parts = re.split(r"<!--doc:(\w+)\|([^>]+)-->", legal_src)
docs = {}
for i in range(1, len(parts), 3):
    key, title, html = parts[i], parts[i + 1], parts[i + 2].strip()
    html = html.replace("<table>", '<div class="tbl"><table>').replace("</table>", "</table></div>")
    docs[key] = {"t": title, "h": html}
assert set(docs) == {"aviso", "privacidad", "cookies", "terminos"}, docs.keys()
legal_json = json.dumps(docs, ensure_ascii=False).replace("</", "<\\/")

# ---------- app ----------
app = read("app.html")
assert app.count("/*LEGAL_START*/{}/*LEGAL_END*/") == 1
app = app.replace("/*LEGAL_START*/{}/*LEGAL_END*/", "/*LEGAL_START*/" + legal_json + "/*LEGAL_END*/")
assert app.count('"__VERSION__"') == 1
app = app.replace('"__VERSION__"', json.dumps(VERSION))
style_end = app.index("</style>") + len("</style>")
style, body = app[:style_end].strip(), app[style_end:].strip()
assert style.startswith("<style>") and "<script>" in body

head = f"""<!doctype html>
<html lang="es" dir="ltr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>{TITLE}</title>
<meta name="description" content="{DESC}">
<meta name="theme-color" content="#070b08">
<meta name="color-scheme" content="dark">
<meta name="application-name" content="DebtOut">
<meta name="mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-title" content="DebtOut">
<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
<meta name="format-detection" content="telephone=no">
<meta property="og:type" content="website">
<meta property="og:locale" content="es_ES">
<meta property="og:site_name" content="DebtOut">
<meta property="og:title" content="{TITLE}">
<meta property="og:description" content="{DESC}">
<link rel="manifest" href="manifest.webmanifest">
<link rel="icon" href="icons/favicon.svg" type="image/svg+xml">
<link rel="icon" href="icons/favicon-32.png" sizes="32x32" type="image/png">
<link rel="apple-touch-icon" href="icons/apple-touch-icon.png">
<link rel="preload" href="fonts/inter-400.v1.woff" as="font" type="font/woff" crossorigin>
<link rel="preload" href="fonts/inter-display-700.v1.woff" as="font" type="font/woff" crossorigin>
<script src="datos-titular.js"></script>
"""
index = (head + style + "\n</head>\n<body>\n"
         '<noscript><p style="margin:0;padding:40px 24px;text-align:center;font:16px/1.5 system-ui,sans-serif;color:#ecf4e8;background:#030504">'
         "DebtOut necesita JavaScript para funcionar. Actívalo en tu navegador y vuelve a cargar la página.</p></noscript>\n"
         + body + "\n</body>\n</html>\n")
write("index.html", index)

# ---------- owner details (edited by the owner; never overwritten once it exists) ----------
if not os.path.exists(os.path.join(OUT, "datos-titular.js")):
    write("datos-titular.js", """/*
  DATOS DEL TITULAR DE DEBTOUT
  ----------------------------
  Rellena tus datos entre las comillas antes de publicar. Salen en el Aviso legal,
  en la Política de privacidad y en los Términos de la app.

  - Escribe solo dentro de las comillas "" y no borres las comas del final.
  - Si no eres una empresa, deja "registro" vacío: esa línea desaparecerá sola.
  - Mientras un dato esté vacío, la app lo muestra resaltado en amarillo
    para que no se te olvide.
  - Con el correo relleno aparece en Ajustes el botón "Enviar comentarios".
*/
window.DEBTOUT_TITULAR = {
  nombre: "",      // Nombre y apellidos, o razón social si es una empresa
  nif: "",         // NIF o DNI
  domicilio: "",   // Calle, número, código postal y ciudad
  email: "",       // Correo de contacto, por ejemplo hola@tudominio.com
  registro: ""     // Solo empresas: Registro Mercantil, tomo, folio y hoja
};
""")

# ---------- web app manifest ----------
manifest = {
    "id": "./",
    "name": "DebtOut: tu plan para salir de deudas",
    "short_name": "DebtOut",
    "description": DESC,
    "lang": "es",
    "dir": "ltr",
    "start_url": "./",
    "scope": "./",
    "display": "standalone",
    "background_color": "#070b08",
    "theme_color": "#070b08",
    "categories": ["finance", "productivity"],
    "icons": [
        {"src": "icons/icon-192.png", "sizes": "192x192", "type": "image/png", "purpose": "any"},
        {"src": "icons/icon-512.png", "sizes": "512x512", "type": "image/png", "purpose": "any"},
        {"src": "icons/icon-maskable-192.png", "sizes": "192x192", "type": "image/png", "purpose": "maskable"},
        {"src": "icons/icon-maskable-512.png", "sizes": "512x512", "type": "image/png", "purpose": "maskable"},
    ],
    "screenshots": [
        {"src": "screenshots/inicio.png", "sizes": "780x1688", "type": "image/png", "form_factor": "narrow", "label": "Tu plan del mes: cuándo sales de deudas y cómo se reparte tu sueldo"},
        {"src": "screenshots/pagos.png", "sizes": "780x1688", "type": "image/png", "form_factor": "narrow", "label": "Calendario de pagos del mes"},
        {"src": "screenshots/escritorio.png", "sizes": "1280x800", "type": "image/png", "form_factor": "wide", "label": "DebtOut en el ordenador"},
    ],
}
write("manifest.webmanifest", json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")

# ---------- Netlify headers ----------
csp = ("default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; "
       "img-src 'self' data: blob:; font-src 'self'; connect-src 'self'; manifest-src 'self'; worker-src 'self'; "
       "base-uri 'none'; form-action 'none'; frame-ancestors 'none'; object-src 'none'")
write("_headers", f"""/*
  X-Content-Type-Options: nosniff
  Referrer-Policy: strict-origin-when-cross-origin
  X-Frame-Options: DENY
  Permissions-Policy: camera=(), microphone=(), geolocation=(), payment=(), usb=()
  Content-Security-Policy: {csp}

/sw.js
  Cache-Control: no-cache

/datos-titular.js
  Cache-Control: no-cache

/manifest.webmanifest
  Content-Type: application/manifest+json; charset=utf-8
  Cache-Control: no-cache

/fonts/*
  Cache-Control: public, max-age=31536000, immutable
""")

# ---------- 404 ----------
mark = ('<svg width="72" height="72" viewBox="0 0 120 120" aria-hidden="true"><defs><mask id="m" maskUnits="userSpaceOnUse" x="0" y="0" width="120" height="120">'
        '<rect width="120" height="120" fill="#fff"/><rect x="19" y="44" width="82" height="32" rx="5" fill="none" stroke="#000" stroke-width="4.5"/>'
        '<circle cx="60" cy="60" r="10" fill="#000"/></mask></defs><g mask="url(#m)" fill="#8cc63f"><rect x="43" y="8" width="34" height="104" rx="9"/>'
        '<rect x="8" y="33" width="104" height="54" rx="9"/></g><circle cx="60" cy="60" r="5" fill="#8cc63f"/></svg>')
write("404.html", f"""<!doctype html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Página no encontrada · DebtOut</title>
<meta name="robots" content="noindex">
<meta name="theme-color" content="#070b08">
<link rel="icon" href="/icons/favicon.svg" type="image/svg+xml">
<style>
@font-face{{font-family:"Inter";font-weight:400;font-display:swap;src:url("/fonts/inter-400.v1.woff") format("woff")}}
@font-face{{font-family:"Inter";font-weight:700;font-display:swap;src:url("/fonts/inter-700.v1.woff") format("woff")}}
:root{{color-scheme:dark}}
*{{box-sizing:border-box}}
body{{margin:0;min-height:100vh;min-height:100svh;display:grid;place-items:center;padding:24px;background:#030504;color:#ecf4e8;font:16px/1.5 "Inter",system-ui,sans-serif;text-align:center}}
main{{max-width:340px;display:flex;flex-direction:column;align-items:center;gap:10px}}
h1{{font-size:24px;line-height:1.2;margin:10px 0 0}}
p{{color:#8c9e8f;margin:0 0 14px}}
a{{display:inline-flex;align-items:center;justify-content:center;min-height:52px;padding:0 24px;border-radius:16px;background:#8cc63f;color:#0a1206;font-weight:700;text-decoration:none}}
a:hover{{background:#b6ea6e}}
a:focus-visible{{outline:2px solid #b6ea6e;outline-offset:3px}}
</style>
</head>
<body>
<main>
{mark}
<h1>Esta página no existe</h1>
<p>Puede que el enlace esté mal escrito o que la página ya no esté disponible.</p>
<a href="/">Abrir DebtOut</a>
</main>
</body>
</html>
""")

# ---------- service worker ----------
CORE = ["./", "manifest.webmanifest", "datos-titular.js",
        "fonts/inter-400.v1.woff", "fonts/inter-600.v1.woff", "fonts/inter-700.v1.woff", "fonts/inter-800.v1.woff",
        "fonts/inter-display-600.v1.woff", "fonts/inter-display-700.v1.woff",
        "icons/favicon.svg", "icons/favicon-32.png", "icons/apple-touch-icon.png", "icons/icon-192.png"]
for rel in CORE[1:]:
    if rel != "datos-titular.js":
        assert os.path.exists(os.path.join(OUT, rel)), "missing " + rel

h = hashlib.sha256()
for rel in ["index.html"] + CORE[1:]:
    with open(os.path.join(OUT, rel), "rb") as f:
        h.update(rel.encode() + b"\0" + f.read())
build = VERSION + "-" + h.hexdigest()[:10]

sw = """/* DebtOut service worker.
   Keeps a copy of the app's own files (code, font, icons) so it opens fast and works offline.
   It never stores or sends personal data: your plan lives only in this device's local storage. */
"use strict";
var BUILD = "__BUILD__";
var CACHE = "debtout-app-" + BUILD;
var CORE = __CORE__;
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
function networkFirst(request, key) {
  var net = fetch(request).then(function (res) { keep(key, res); return res; });
  var timer = new Promise(function (resolve) { setTimeout(resolve, NET_TIMEOUT, null); });
  return Promise.race([net.catch(function () { return null; }), timer]).then(function (res) {
    if (res) return res;
    return caches.match(key).then(function (hit) { return hit || net; });
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
  if (req.mode === "navigate") {
    var isApp = url.pathname === scope.pathname || url.pathname === scope.pathname + "index.html";
    event.respondWith(isApp ? networkFirst(req, scope.href) : fetch(req).catch(function () { return caches.match(scope.href); }));
    return;
  }
  if (/\\/(fonts|icons)\\//.test(url.pathname)) { event.respondWith(cacheFirst(req)); return; }
  url.search = "";
  event.respondWith(networkFirst(req, url.href));
});
"""
sw = sw.replace("__BUILD__", build).replace("__CORE__", json.dumps(CORE))
write("sw.js", sw)

print("build", build)
for rel in ["index.html", "sw.js", "manifest.webmanifest", "_headers", "404.html", "datos-titular.js"]:
    print(f"  {rel:22s} {os.path.getsize(os.path.join(OUT, rel)):>8,d} B")
