"""Build DebtOut: the promotional website, the installable web app and the app for iPhone and Android.

Inputs (this folder): landing.html (website home page), app.html (the app: styles + markup + script),
legal_beta.html (legal texts, shared by the app and the website).

Outputs:
  ../web          the website, ready to publish as it is on any static host (no build step needed there):
                    index.html            website home page
                    app/index.html        the app (installable; same identity as before, so old installs keep working)
                    aviso-legal/, privacidad/, cookies/, terminos/   legal pages of the website
                    manifest, service worker, 404, robots.txt, sitemap.xml (only with SITE_URL), site.js
                    and, only if missing, the owner data file (datos-titular.js)
  ../mobile/www   the app for Capacitor (iPhone/Android): no service worker or install prompts. native.js, the
                  bridge to the phone, is bundled from mobile/native/bridge.js when mobile/node_modules exists.

Usage: python3 src/build.py
Fonts, icons and screenshots are produced by their own scripts (make_fonts.py, make_icons.py, make_screens.py).
"""
import hashlib, json, os, re, shutil, subprocess, sys

SRC = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(SRC, ".."))
OUT = os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "web"))
MOBILE = os.path.join(ROOT, "mobile")
WWW = os.path.join(MOBILE, "www")

VERSION = "0.10.0"

# Public address of the website, for example "https://debtout.es" (without the final slash). With it the build adds
# canonical links, absolute images for link previews (WhatsApp, X, LinkedIn...) and sitemap.xml.
# The DEBTOUT_SITE_URL environment variable overrides it.
SITE_URL = (os.environ.get("DEBTOUT_SITE_URL") or "").strip().rstrip("/")

# Store pages, once the app is published. While empty, the website shows "Próximamente".
APP_STORE_URL = ""
PLAY_STORE_URL = ""

DESC = ("Reparte tu sueldo entre gastos fijos, deudas, ahorro y dinero libre, y mira cuándo "
        "terminarás de pagar tus deudas. Sin conectar tu banco. Gratis durante la beta.")
TITLE = "DebtOut · Tu plan para salir de deudas"
SITE_TITLE = "DebtOut · Sal de deudas con un plan para cada mes"
SITE_DESC = ("DebtOut reparte tu sueldo entre gastos fijos, deudas, ahorro y dinero libre, y te dice en qué mes "
             "terminarás de pagar tus deudas. Sin conectar tu banco, sin cuenta y gratis durante la beta.")
THEME = "#070b08"

FONTS = ["inter-400.v1.woff", "inter-600.v1.woff", "inter-700.v1.woff", "inter-800.v1.woff",
         "inter-display-600.v1.woff", "inter-display-700.v1.woff"]
LEGAL_PAGES = [("aviso", "aviso-legal"), ("privacidad", "privacidad"), ("cookies", "cookies"), ("terminos", "terminos")]
LEGAL_TITLES = {"aviso": "Aviso legal", "privacidad": "Política de privacidad", "cookies": "Política de cookies", "terminos": "Términos y condiciones"}


def read(p):
    with open(os.path.join(SRC, p), encoding="utf-8") as f:
        return f.read()


def write(rel, text, base=None):
    path = os.path.join(base or OUT, rel)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)


def swap(s, old, new, count=1):
    assert s.count(old) == count, (old[:80], s.count(old), count)
    return s.replace(old, new)


# Security policy of the website and the web app. It goes inside each page (a <meta> tag), so it works on any
# host. Nothing is loaded from other sites; inline code is ours (the pages are generated here).
CSP = ("default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; "
       "img-src 'self' data: blob:; font-src 'self'; connect-src 'self'; manifest-src 'self'; worker-src 'self'; "
       "base-uri 'none'; form-action 'none'; object-src 'none'")
SECURITY_META = (f'<meta http-equiv="Content-Security-Policy" content="{CSP}">\n'
                 '<meta name="referrer" content="strict-origin-when-cross-origin">\n')


def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def absolute(rel):
    """Absolute URL when SITE_URL is known; otherwise the relative path (good enough for most previews)."""
    return f"{SITE_URL}/{rel}" if SITE_URL else rel


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


# ---------- the app (web and native share the same source) ----------
def build_app(prefix, native):
    """prefix: path from the app page to the shared files ("../" on the website, "" inside the phone app)."""
    app = read("app.html")
    app = swap(app, "/*LEGAL_START*/{}/*LEGAL_END*/", "/*LEGAL_START*/" + legal_json + "/*LEGAL_END*/")
    app = swap(app, '"__VERSION__"', json.dumps(VERSION))
    app = swap(app, "__SW_URL__", prefix + "sw.js")
    app = swap(app, 'url("fonts/', f'url("{prefix}fonts/', count=len(FONTS))
    style_end = app.index("</style>") + len("</style>")
    style, body = app[:style_end].strip(), app[style_end:].strip()
    assert style.startswith("<style>") and "<script>" in body

    if native:
        links = '<script src="native.js"></script>\n'
    else:
        links = (SECURITY_META + f'<link rel="manifest" href="{prefix}manifest.webmanifest">\n'
                 f'<link rel="icon" href="{prefix}icons/favicon.svg" type="image/svg+xml">\n'
                 f'<link rel="icon" href="{prefix}icons/favicon-32.png" sizes="32x32" type="image/png">\n'
                 f'<link rel="apple-touch-icon" href="{prefix}icons/apple-touch-icon.png">\n'
                 '<meta property="og:type" content="website">\n'
                 '<meta property="og:locale" content="es_ES">\n'
                 '<meta property="og:site_name" content="DebtOut">\n'
                 f'<meta property="og:title" content="{TITLE}">\n'
                 f'<meta property="og:description" content="{DESC}">\n'
                 f'<meta property="og:image" content="{absolute("img/og.png")}">\n')
    head = f"""<!doctype html>
<html lang="es" dir="ltr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>{TITLE}</title>
<meta name="description" content="{DESC}">
<meta name="theme-color" content="{THEME}">
<meta name="color-scheme" content="dark">
<meta name="application-name" content="DebtOut">
<meta name="mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-title" content="DebtOut">
<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
<meta name="format-detection" content="telephone=no">
{links}<link rel="preload" href="{prefix}fonts/inter-400.v1.woff" as="font" type="font/woff" crossorigin>
<link rel="preload" href="{prefix}fonts/inter-display-700.v1.woff" as="font" type="font/woff" crossorigin>
<script src="{prefix}datos-titular.js"></script>
"""
    return (head + style + "\n</head>\n<body>\n"
            '<noscript><p style="margin:0;padding:40px 24px;text-align:center;font:16px/1.5 system-ui,sans-serif;color:#ecf4e8;background:#030504">'
            "DebtOut necesita JavaScript para funcionar. Actívalo en tu navegador y vuelve a cargar la página.</p></noscript>\n"
            + body + "\n</body>\n</html>\n")


write("app/index.html", build_app("../", native=False))

# ---------- owner details (edited by the owner; never overwritten once it exists) ----------
if not os.path.exists(os.path.join(OUT, "datos-titular.js")):
    write("datos-titular.js", """/*
  DATOS DEL TITULAR DE DEBTOUT
  ----------------------------
  Rellena tus datos entre las comillas antes de publicar. Salen en el Aviso legal,
  en la Política de privacidad y en los Términos de la app y de la web.

  - Escribe solo dentro de las comillas "" y no borres las comas del final.
  - Si no eres una empresa, deja "registro" vacío: esa línea desaparecerá sola.
  - Mientras un dato esté vacío, la app lo muestra resaltado en amarillo
    para que no se te olvide.
  - Con el correo relleno aparece en Ajustes el botón "Enviar comentarios"
    y el correo de contacto en el pie de la web.
*/
window.DEBTOUT_TITULAR = {
  nombre: "",      // Nombre y apellidos, o razón social si es una empresa
  nif: "",         // NIF o DNI
  domicilio: "",   // Calle, número, código postal y ciudad
  email: "",       // Correo de contacto, por ejemplo hola@tudominio.com
  registro: ""     // Solo empresas: Registro Mercantil, tomo, folio y hoja
};
""")

# ---------- shared pieces of the website ----------
MARK_SVG = ('<svg class="mark" viewBox="0 0 120 120" aria-hidden="true"><defs><mask id="mk-{id}" maskUnits="userSpaceOnUse" x="0" y="0" width="120" height="120">'
            '<rect width="120" height="120" fill="#fff"/><rect x="19" y="44" width="82" height="32" rx="5" fill="none" stroke="#000" stroke-width="4.5"/>'
            '<circle cx="60" cy="60" r="10" fill="#000"/></mask></defs><g mask="url(#mk-{id})" fill="currentColor"><rect x="43" y="8" width="34" height="104" rx="9"/>'
            '<rect x="8" y="33" width="104" height="54" rx="9"/></g><circle cx="60" cy="60" r="5" fill="currentColor"/></svg>')


def mark(uid):
    return MARK_SVG.replace("{id}", uid)


def font_faces(prefix):
    weights = [("Inter", 400, "inter-400"), ("Inter", 600, "inter-600"), ("Inter", 700, "inter-700"), ("Inter", 800, "inter-800"),
               ("Inter Display", 600, "inter-display-600"), ("Inter Display", 700, "inter-display-700")]
    return "\n".join(f'@font-face{{font-family:"{fam}";font-style:normal;font-weight:{w};font-display:swap;src:url("{prefix}fonts/{f}.v1.woff") format("woff")}}'
                     for fam, w, f in weights)


def site_head(prefix, title, desc, path, extra=""):
    canonical = f'<link rel="canonical" href="{SITE_URL}/{path}">\n<meta property="og:url" content="{SITE_URL}/{path}">\n' if SITE_URL else ""
    return f"""<meta charset="utf-8">
{SECURITY_META}<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>{esc(title)}</title>
<meta name="description" content="{esc(desc)}">
<meta name="theme-color" content="{THEME}">
<meta name="color-scheme" content="dark">
<meta name="format-detection" content="telephone=no">
{canonical}<meta property="og:type" content="website">
<meta property="og:locale" content="es_ES">
<meta property="og:site_name" content="DebtOut">
<meta property="og:title" content="{esc(title)}">
<meta property="og:description" content="{esc(desc)}">
<meta property="og:image" content="{absolute("img/og.png")}">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta property="og:image:alt" content="DebtOut: tu plan para salir de deudas, en el móvil">
<meta name="twitter:card" content="summary_large_image">
<link rel="icon" href="{prefix}icons/favicon.svg" type="image/svg+xml">
<link rel="icon" href="{prefix}icons/favicon-32.png" sizes="32x32" type="image/png">
<link rel="apple-touch-icon" href="{prefix}icons/apple-touch-icon.png">
<link rel="preload" href="{prefix}fonts/inter-400.v1.woff" as="font" type="font/woff" crossorigin>
<link rel="preload" href="{prefix}fonts/inter-display-700.v1.woff" as="font" type="font/woff" crossorigin>
{extra}"""


FOOTER_LEGAL = "".join(f'<li><a href="{{P}}{slug}/">{LEGAL_TITLES[key]}</a></li>' for key, slug in LEGAL_PAGES)

# site.js: fills the owner's details in the legal pages and the contact e-mail in the footer.
write("site.js", """/* DebtOut website: owner details from datos-titular.js (legal pages and footer). No tracking, no cookies. */
(function () {
  "use strict";
  var T = window.DEBTOUT_TITULAR && typeof window.DEBTOUT_TITULAR === "object" ? window.DEBTOUT_TITULAR : {};
  function has(k) { return String(T[k] || "").trim() !== ""; }
  var email = String(T.email || "").trim();
  if (!/^[^\\s@<>"]+@[^\\s@<>"]+\\.[^\\s@<>"]{2,}$/.test(email)) email = "";
  function mailLink() { var a = document.createElement("a"); a.href = "mailto:" + email; a.textContent = email; return a; }
  if (has("nombre") && !has("registro")) document.querySelectorAll('li[data-opt="registro"]').forEach(function (e) { e.remove(); });
  document.querySelectorAll("mark.ph[data-k]").forEach(function (m) {
    var k = m.getAttribute("data-k");
    if (k === "email") { if (email) m.replaceWith(mailLink()); return; }
    if (has(k)) m.replaceWith(document.createTextNode(String(T[k]).trim()));
  });
  document.querySelectorAll("[data-contact]").forEach(function (el) {
    if (!email) return;
    el.hidden = false;
    var slot = el.querySelector("[data-contact-link]");
    if (slot) slot.replaceWith(mailLink());
  });
})();
""")

SITE_CSS = """
:root{color-scheme:dark;--page:#030504;--bg:#070b08;--surface:#0d130f;--surface-2:#131b15;--raise:#1a241c;--line:#1f2b22;--line-2:#2c3b2f;
  --text:#ecf4e8;--muted:#8c9e8f;--faint:#5f7062;--green:#8cc63f;--green-hi:#b6ea6e;--green-ink:#0a1206;--cyan:#5ccfe6;--coral:#ff7a6b;--amber:#f0bd4f;
  --display:"Inter Display","Inter",system-ui,-apple-system,"Segoe UI",Roboto,sans-serif;--body:"Inter",system-ui,-apple-system,"Segoe UI",Roboto,sans-serif}
*,*::before,*::after{box-sizing:border-box}
html{-webkit-text-size-adjust:100%;scroll-behavior:smooth}
body{margin:0;background:var(--page);color:var(--text);font:16px/1.6 var(--body);-webkit-font-smoothing:antialiased}
a{color:var(--green)}
a:hover{color:var(--green-hi)}
:focus-visible{outline:2px solid var(--green-hi);outline-offset:3px;border-radius:6px}
.wrap{width:min(1120px,100% - 32px);margin-inline:auto}
.top{position:sticky;top:0;z-index:20;background:rgba(3,5,4,.82);-webkit-backdrop-filter:blur(14px);backdrop-filter:blur(14px);border-bottom:1px solid var(--line)}
.top .wrap{display:flex;align-items:center;justify-content:space-between;gap:16px;min-height:64px}
.brand{display:inline-flex;align-items:center;gap:10px;color:var(--text);text-decoration:none;font-family:var(--display);font-weight:700;font-size:18px;letter-spacing:-.01em}
.brand:hover{color:var(--text)}
.brand .mark{width:30px;height:30px;color:var(--green)}
.nav{display:flex;gap:4px;margin-left:auto}
.nav a{color:var(--muted);text-decoration:none;font-size:14.5px;font-weight:600;padding:8px 12px;border-radius:10px}
.nav a:hover{color:var(--text);background:var(--surface-2)}
@media (max-width:900px){.nav{display:none}}
.beta{display:inline-block;padding:2px 7px;border-radius:99px;background:rgba(140,198,63,.16);box-shadow:inset 0 0 0 1px rgba(140,198,63,.45);color:var(--green-hi);font-size:10px;letter-spacing:.14em;font-family:var(--body);font-weight:700}
.btn{display:inline-flex;align-items:center;justify-content:center;gap:8px;min-height:48px;padding:0 22px;border-radius:14px;font-weight:700;font-size:15px;text-decoration:none;border:0;cursor:pointer;transition:background-color .2s,color .2s,box-shadow .2s,transform .15s}
.btn:active{transform:scale(.98)}
.btn-primary{background:var(--green);color:var(--green-ink);box-shadow:inset 0 0 0 1px rgba(182,234,110,.45),0 14px 34px -16px rgba(140,198,63,.85)}
.btn-primary:hover{background:var(--green-hi);color:var(--green-ink)}
.btn-ghost{background:transparent;color:var(--text);box-shadow:inset 0 0 0 1px var(--line-2)}
.btn-ghost:hover{background:var(--surface-2);color:var(--text)}
.btn-sm{min-height:40px;padding:0 16px;font-size:14px;border-radius:12px}
.ic{width:20px;height:20px;flex:none}
.foot{border-top:1px solid var(--line);padding:44px 0 calc(32px + env(safe-area-inset-bottom,0px));color:var(--muted);font-size:14px}
.foot-grid{display:grid;grid-template-columns:1.4fr 1fr 1fr;gap:28px}
.foot h2{font-size:13px;letter-spacing:.08em;text-transform:uppercase;color:var(--faint);margin:0 0 12px;font-weight:700}
.foot ul{list-style:none;margin:0;padding:0;display:flex;flex-direction:column;gap:8px}
.foot a{color:var(--muted);text-decoration:none}
.foot a:hover{color:var(--text)}
.foot .brand,.foot .brand:hover{color:var(--text)}
.foot p{margin:10px 0 0;max-width:42ch}
.foot .fine{margin-top:32px;padding-top:20px;border-top:1px solid var(--line);font-size:12.5px;color:var(--faint);max-width:none}
@media (max-width:720px){.foot-grid{grid-template-columns:1fr 1fr}.foot-grid>div:first-child{grid-column:1/-1}}
@media (prefers-reduced-motion:reduce){html{scroll-behavior:auto}*,*::before,*::after{animation-duration:.01ms!important;animation-iteration-count:1!important;transition-duration:.01ms!important}}
"""


def site_footer(prefix):
    return f"""<footer class="foot">
  <div class="wrap">
    <div class="foot-grid">
      <div>
        <a class="brand" href="{prefix or './'}">{mark("ft")}DebtOut</a>
        <p>Tu plan para salir de deudas: reparte tu sueldo, ordena tus pagos y mira cuándo terminas. Sin conectar tu banco.</p>
        <p data-contact hidden>Escríbenos: <span data-contact-link></span></p>
      </div>
      <div>
        <h2>DebtOut</h2>
        <ul>
          <li><a href="{prefix}app/">Abrir la app</a></li>
          <li><a href="{prefix or './'}#como-funciona">Cómo funciona</a></li>
          <li><a href="{prefix or './'}#precio">Precio</a></li>
          <li><a href="{prefix or './'}#preguntas">Preguntas frecuentes</a></li>
        </ul>
      </div>
      <div>
        <h2>Legal</h2>
        <ul>{FOOTER_LEGAL.replace("{P}", prefix)}</ul>
      </div>
    </div>
    <p class="fine">© 2026 DebtOut · Versión beta {VERSION}. DebtOut no es una entidad financiera, no conecta con tu banco, no mueve dinero y no presta asesoramiento financiero. Los cálculos son orientativos.</p>
  </div>
</footer>"""


def site_header(prefix):
    home = prefix or "./"
    nav = "".join(f'<a href="{home}#{a}">{t}</a>' for a, t in
                  [("como-funciona", "Cómo funciona"), ("calculadora", "Calculadora"), ("privacidad", "Privacidad"), ("precio", "Precio"), ("preguntas", "Preguntas")])
    return f"""<header class="top">
  <div class="wrap">
    <a class="brand" href="{home}" aria-label="DebtOut, inicio">{mark("hd")}DebtOut <span class="beta">BETA</span></a>
    <nav class="nav" aria-label="Secciones">{nav}</nav>
    <a class="btn btn-primary btn-sm" href="{prefix}app/" data-cta>Abrir la app</a>
  </div>
</header>"""


# ---------- website home page ----------
def store_badge(url, label, icon):
    if url:
        return f'<a class="store" href="{esc(url)}" rel="noopener">{icon}<span><small>Descárgala para</small>{label}</span></a>'
    return f'<span class="store soon">{icon}<span><small>Próximamente</small>{label}</span></span>'


landing = read("landing.html")
PHONE_IC = ('<svg class="ic" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">'
            '<rect x="6.5" y="2" width="11" height="20" rx="2.5"/><path d="M11 18.5h2"/></svg>')
stores_live = bool(APP_STORE_URL or PLAY_STORE_URL)
tokens = {
    "HEAD": site_head("", SITE_TITLE, SITE_DESC, "", '<link rel="manifest" href="manifest.webmanifest">\n'),
    "FONTS": font_faces(""),
    "SITE_CSS": SITE_CSS,
    "HEADER": site_header(""),
    "FOOTER": site_footer(""),
    "MARK_HERO": mark("hero"),
    "STORES": store_badge(APP_STORE_URL, "iPhone", PHONE_IC) + store_badge(PLAY_STORE_URL, "Android", PHONE_IC),
    "STORES_NOTE": ("Descárgala gratis o úsala en el navegador." if stores_live
                    else "Muy pronto en App Store y Google Play. Mientras tanto, úsala gratis en el navegador del móvil o del ordenador e instálala desde allí."),
    "JSONLD": json.dumps({
        "@context": "https://schema.org", "@type": "SoftwareApplication", "name": "DebtOut",
        "applicationCategory": "FinanceApplication", "operatingSystem": "Web",
        "description": SITE_DESC, "inLanguage": "es", "softwareVersion": VERSION,
        "offers": {"@type": "Offer", "price": "0", "priceCurrency": "EUR"},
        **({"url": SITE_URL + "/"} if SITE_URL else {}),
    }, ensure_ascii=False).replace("</", "<\\/"),
}
for k, v in tokens.items():
    landing = swap(landing, "{{" + k + "}}", v, count=landing.count("{{" + k + "}}") or 1)
assert "{{" not in landing, re.findall(r"\{\{\w+\}\}", landing)
write("index.html", landing)

# ---------- legal pages of the website ----------
LEGAL_CSS = """
.doc{padding:40px 0 64px}
.doc .wrap{max-width:760px}
.crumbs{font-size:14px;color:var(--muted);margin:0 0 18px}
.crumbs a{color:var(--muted)}
.doc h1{font-family:var(--display);font-weight:700;font-size:clamp(30px,5vw,42px);line-height:1.1;letter-spacing:-.02em;margin:0 0 20px}
.legal{color:var(--muted);font-size:15.5px;line-height:1.65}
.legal h3{color:var(--text);font-size:18px;margin:30px 0 8px;font-family:var(--display);font-weight:600}
.legal p{margin:0 0 12px}
.legal ul{margin:0 0 12px;padding-left:20px;display:flex;flex-direction:column;gap:6px}
.legal .upd{font-size:13px;color:var(--faint)}
.legal .tbl{overflow-x:auto;border-radius:12px;box-shadow:inset 0 0 0 1px var(--line-2);margin:0 0 14px}
.legal table{width:100%;min-width:560px;border-collapse:collapse;font-size:13.5px}
.legal th,.legal td{border-bottom:1px solid var(--line-2);padding:10px 12px;text-align:left;vertical-align:top}
.legal tr:last-child td{border-bottom:0}
.legal th{color:var(--text);background:var(--surface)}
.legal .form-model{padding:14px 16px;border-radius:12px;background:var(--surface);box-shadow:inset 0 0 0 1px var(--line-2)}
.legal mark.ph{background:rgba(240,189,79,.18);color:var(--amber);padding:0 4px;border-radius:4px}
.others{margin-top:40px;padding-top:24px;border-top:1px solid var(--line);display:flex;flex-wrap:wrap;gap:10px}
"""
for key, slug in LEGAL_PAGES:
    d = docs[key]
    title = LEGAL_TITLES[key]
    others = "".join(f'<a class="btn btn-ghost btn-sm" href="../{s}/">{LEGAL_TITLES[k]}</a>' for k, s in LEGAL_PAGES if k != key)
    page = f"""<!doctype html>
<html lang="es" dir="ltr">
<head>
{site_head("../", title + " · DebtOut", "DebtOut: " + title.lower() + ". Tu plan se guarda solo en tu dispositivo.", slug + "/")}<script src="../datos-titular.js"></script>
<style>
{font_faces("../")}
{SITE_CSS}
{LEGAL_CSS}
</style>
</head>
<body>
{site_header("../")}
<main class="doc">
  <div class="wrap">
    <p class="crumbs"><a href="../">DebtOut</a> / Legal</p>
    <h1>{title}</h1>
    <div class="legal">
{d["h"]}
    </div>
    <nav class="others" aria-label="Otros textos legales">{others}</nav>
  </div>
</main>
{site_footer("../")}
<script src="../site.js"></script>
</body>
</html>
"""
    write(f"{slug}/index.html", page)

# ---------- web app manifest (same id as before: installed copies keep working and now open app/) ----------
manifest = {
    "id": "./",
    "name": "DebtOut: tu plan para salir de deudas",
    "short_name": "DebtOut",
    "description": DESC,
    "lang": "es",
    "dir": "ltr",
    "start_url": "app/",
    "scope": "./",
    "display": "standalone",
    "background_color": THEME,
    "theme_color": THEME,
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

# Old Netlify settings file, if a previous build left one.
if os.path.exists(os.path.join(OUT, "_headers")):
    os.remove(os.path.join(OUT, "_headers"))

# ---------- robots + sitemap ----------
write("robots.txt", "User-agent: *\nAllow: /\n" + (f"\nSitemap: {SITE_URL}/sitemap.xml\n" if SITE_URL else ""))
sitemap = os.path.join(OUT, "sitemap.xml")
if SITE_URL:
    urls = [""] + [slug + "/" for _, slug in LEGAL_PAGES]
    write("sitemap.xml", '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
          + "".join(f"  <url><loc>{SITE_URL}/{u}</loc></url>\n" for u in urls) + "</urlset>\n")
elif os.path.exists(sitemap):
    os.remove(sitemap)

# ---------- 404 ----------
write("404.html", f"""<!doctype html>
<html lang="es">
<head>
<meta charset="utf-8">
{SECURITY_META}<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Página no encontrada · DebtOut</title>
<meta name="robots" content="noindex">
<meta name="theme-color" content="{THEME}">
<link rel="icon" href="/icons/favicon.svg" type="image/svg+xml">
<style>
@font-face{{font-family:"Inter";font-weight:400;font-display:swap;src:url("/fonts/inter-400.v1.woff") format("woff")}}
@font-face{{font-family:"Inter";font-weight:700;font-display:swap;src:url("/fonts/inter-700.v1.woff") format("woff")}}
:root{{color-scheme:dark}}
*{{box-sizing:border-box}}
body{{margin:0;min-height:100vh;min-height:100svh;display:grid;place-items:center;padding:24px;background:#030504;color:#ecf4e8;font:16px/1.5 "Inter",system-ui,sans-serif;text-align:center}}
main{{max-width:340px;display:flex;flex-direction:column;align-items:center;gap:10px}}
.mark{{width:72px;height:72px;color:#8cc63f}}
h1{{font-size:24px;line-height:1.2;margin:10px 0 0}}
p{{color:#8c9e8f;margin:0 0 14px}}
a{{display:inline-flex;align-items:center;justify-content:center;min-height:52px;width:100%;padding:0 24px;border-radius:16px;background:#8cc63f;color:#0a1206;font-weight:700;text-decoration:none}}
a:hover{{background:#b6ea6e}}
a.ghost{{background:transparent;color:#ecf4e8;box-shadow:inset 0 0 0 1px #2c3b2f}}
a.ghost:hover{{background:#131b15}}
a:focus-visible{{outline:2px solid #b6ea6e;outline-offset:3px}}
</style>
</head>
<body>
<main>
{mark("nf")}
<h1>Esta página no existe</h1>
<p>Puede que el enlace esté mal escrito o que la página ya no esté disponible.</p>
<a href="/app/">Abrir DebtOut</a>
<a class="ghost" href="/">Ir a la web de DebtOut</a>
</main>
</body>
</html>
""")

# ---------- service worker (site root: covers the app, the home page and installs made before app/ existed) ----------
CORE = ["./", "app/", "manifest.webmanifest", "datos-titular.js"] + ["fonts/" + f for f in FONTS] + \
       ["icons/favicon.svg", "icons/favicon-32.png", "icons/apple-touch-icon.png", "icons/icon-192.png"]
for rel in CORE[2:]:
    if rel != "datos-titular.js":
        assert os.path.exists(os.path.join(OUT, rel)), "missing " + rel

h = hashlib.sha256()
for rel in ["index.html", "app/index.html"] + CORE[2:]:
    with open(os.path.join(OUT, rel), "rb") as f:
        h.update(rel.encode() + b"\0" + f.read())
build = VERSION + "-" + h.hexdigest()[:10]

sw = """/* DebtOut service worker.
   Keeps a copy of the app's own files (code, font, icons) and of the home page so they open fast and work offline.
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
    var key = url.origin + url.pathname.replace(/index\\.html$/, "");
    var inApp = url.pathname.indexOf(app.pathname) === 0;
    event.respondWith(networkFirst(req, key, inApp ? app.href : scope.href));
    return;
  }
  if (/\\/(fonts|icons)\\//.test(url.pathname)) { event.respondWith(cacheFirst(req)); return; }
  url.search = "";
  event.respondWith(networkFirst(req, url.href));
});
"""
sw = sw.replace("__BUILD__", build).replace("__CORE__", json.dumps(CORE))
write("sw.js", sw)

# ---------- the app for iPhone and Android (Capacitor) ----------
if os.path.isdir(MOBILE):
    keep_native = os.path.join(WWW, "native.js")
    old_native = open(keep_native, "rb").read() if os.path.exists(keep_native) else None
    shutil.rmtree(WWW, ignore_errors=True)
    os.makedirs(os.path.join(WWW, "fonts"))
    write("index.html", build_app("", native=True), base=WWW)
    for f in FONTS + ["OFL.txt"]:
        shutil.copyfile(os.path.join(OUT, "fonts", f), os.path.join(WWW, "fonts", f))
    shutil.copyfile(os.path.join(OUT, "datos-titular.js"), os.path.join(WWW, "datos-titular.js"))
    esbuild = os.path.join(MOBILE, "node_modules", ".bin", "esbuild")
    if os.path.exists(esbuild):
        subprocess.run([esbuild, "native/bridge.js", "--bundle", "--minify", "--format=iife", "--target=es2019",
                        "--legal-comments=none", "--log-level=warning", "--outfile=www/native.js"], cwd=MOBILE, check=True)
    elif old_native:
        with open(keep_native, "wb") as f:
            f.write(old_native)
    else:
        print("  aviso: falta mobile/node_modules; ejecuta `npm install` en mobile/ para generar www/native.js")

print("build", build)
for rel in ["index.html", "app/index.html", "sw.js", "manifest.webmanifest", "404.html", "site.js", "datos-titular.js"]:
    print(f"  web/{rel:24s} {os.path.getsize(os.path.join(OUT, rel)):>8,d} B")
if os.path.isdir(WWW):
    for rel in ["index.html", "native.js"]:
        p = os.path.join(WWW, rel)
        if os.path.exists(p):
            print(f"  mobile/www/{rel:17s} {os.path.getsize(p):>8,d} B")
