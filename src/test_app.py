"""End-to-end checks for DebtOut, served as a static site (see serve.py).

Covers the web app (/app/), the website (/ and the legal pages) and the build for the phone apps (mobile/www),
which runs here with a pretend phone (window.DebtOutNative) because a browser has no Capacitor.
Needs the server running: python3 src/serve.py (and, for mobile/www, python3 src/serve.py mobile/www 8766).
"""
import datetime, json, math, os, subprocess, sys, tempfile, time, traceback
from zoneinfo import ZoneInfo
from playwright.sync_api import sync_playwright

SITE = "http://127.0.0.1:8765/"
BASE = SITE + "app/"
NATIVE_BASE = "http://127.0.0.1:8766/"
VERSION = "0.10.0"
TMP = tempfile.mkdtemp(prefix="debtout-test-")
MOBILE = dict(viewport={"width": 390, "height": 844}, device_scale_factor=2, is_mobile=True, has_touch=True,
              locale="es-ES", timezone_id="Europe/Madrid")
DESKTOP = dict(viewport={"width": 1280, "height": 800}, device_scale_factor=1, locale="es-ES", timezone_id="Europe/Madrid")
INIT = """
window.__csp = [];
document.addEventListener('securitypolicyviolation', function (e) { window.__csp.push(e.violatedDirective + ' ' + e.blockedURI); });
"""

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
MONTHS = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"]
SEED = {"v": 3, "stage": "app", "name": "Ana", "salary": 1850, "freq": "mensual",
        "expenses": [{"id": "e1", "icon": "home", "name": "Alquiler", "amount": 650, "day": 1},
                     {"id": "e3", "icon": "zap", "name": "Luz e internet", "amount": 95, "day": 12}],
        "debts": [{"id": "d1", "type": "card", "name": "Tarjeta de crédito", "balance": 3200, "original": 3200, "apr": 19.9, "min": 95, "day": 5}],
        "goals": [{"id": "g1", "name": "Fondo de emergencia", "target": 3000, "saved": 840}], "debtPct": 18, "savePct": 10,
        "paid": {"d:d1": True}, "month": 0, "accepted": {"at": "2026-10-22T10:00:00Z", "v": "2026-10-22"}, "installHidden": True}

# A pretend phone: what mobile/native/bridge.js gives the app inside Capacitor, recording every call.
FAKE_PHONE = """
window.__nat = { calls: [], store: {}, perm: 'prompt', last: null, back: null, sub: __SUB__, offer: __OFFER__ };
(function (plan) { if (plan) window.__nat.store['debtout.app.v3'] = plan; })(__PLAN__);
/* build.py leaves the assistant address empty until the server is published; the tests point it at a fake one. */
(function () { var v = {}; Object.defineProperty(window, 'DEBTOUT_CONFIG', { configurable: true, get: function () { return v; },
  set: function (n) { v = Object.assign({}, n, { aiUrl: 'https://asistente.test' }); } }); })();
window.DebtOutNative = {
  platform: 'android',
  storage: {
    get: function (k) { return Promise.resolve(k in window.__nat.store ? window.__nat.store[k] : null); },
    set: function (k, v) { window.__nat.store[k] = v; window.__nat.calls.push(['set', k]); return Promise.resolve(); },
    remove: function (k) { delete window.__nat.store[k]; window.__nat.calls.push(['remove', k]); return Promise.resolve(); }
  },
  shareFile: function (name, text) { window.__nat.calls.push(['share', name, text.length]); return Promise.resolve('shared'); },
  haptic: function (k) { window.__nat.calls.push(['haptic', k]); },
  notifications: {
    permission: function () { return Promise.resolve(window.__nat.perm); },
    request: function () { window.__nat.calls.push(['request']); window.__nat.perm = 'granted'; return Promise.resolve(true); },
    replace: function (list) { window.__nat.last = list.map(function (n) { return { title: n.title, at: +n.at }; }); window.__nat.calls.push(['replace', list.length]); return Promise.resolve(); },
    clear: function () { window.__nat.calls.push(['clear']); return Promise.resolve(); }
  },
  purchases: {
    available: true,
    status: function () { return Promise.resolve(window.__nat.sub); },
    offer: function () { return Promise.resolve(window.__nat.offer); },
    buy: function () {
      window.__nat.calls.push(['buy']);
      window.__nat.sub = { active: true, trial: !!(window.__nat.offer && window.__nat.offer.trial), until: new Date(Date.now() + 30 * 864e5).toISOString(), willRenew: true, manageUrl: null };
      return Promise.resolve(window.__nat.sub);
    },
    restore: function () { window.__nat.calls.push(['restore']); return Promise.resolve(window.__nat.sub); },
    userId: function () { return Promise.resolve('$RCAnonymousID:0123456789abcdef0123456789abcdef'); },
    manage: function (u) { window.__nat.calls.push(['manage', u]); },
    onChange: function (cb) { window.__nat.subChange = cb; }
  },
  onBack: function (h) { window.__nat.back = h; },
  onResume: function (h) { window.__nat.resume = h; },
  ready: function () { window.__nat.calls.push(['ready']); }
};
"""


PREMIUM = {"active": True, "trial": False, "until": "2027-01-01T00:00:00Z", "willRenew": True, "manageUrl": None}
FREE = {"active": False, "trial": False, "until": None, "willRenew": False, "manageUrl": None}
PRICE = "2,99 €"  # PREMIUM_PRICE in src/build.py (and the price set in the stores)
OFFER = {"price": PRICE, "trial": True, "trialPeriod": "P1M"}


def fake_phone(plan, sub=PREMIUM, offer=OFFER):
    """plan: the plan already in native storage (dict) or None."""
    return (FAKE_PHONE.replace("__PLAN__", json.dumps(json.dumps(plan)) if plan else "null")
            .replace("__SUB__", json.dumps(sub)).replace("__OFFER__", json.dumps(offer)))


def html_route(body):
    """Route handler that answers with this HTML (one parameter: Playwright passes the request too if asked)."""
    return lambda route: route.fulfill(status=200, content_type="text/html; charset=utf-8", body=body)


def payoff(bal, apr, pay):
    """Same maths as the app and the website calculator."""
    r, m, interest = apr / 1200, 0, 0.0
    if pay <= bal * r + 0.001:
        return None
    while bal > 0.005 and m < 600:
        i = bal * r
        interest += i
        bal = bal + i - pay
        m += 1
    return (m, interest) if bal <= 0.005 else None


def eur(n):
    n = int(math.floor(n + 0.5))
    return f"{n:,}".replace(",", ".") + " €"


def dur(m):
    y, r = divmod(m, 12)
    if not y:
        return f"{m} {'mes' if m == 1 else 'meses'}"
    return f"{y} {'año' if y == 1 else 'años'}" + (f" y {r} {'mes' if r == 1 else 'meses'}" if r else "")


# The phone build is served on its own port, as Capacitor serves www/ at the root of its own origin.
mobile_server = subprocess.Popen([sys.executable, os.path.join(ROOT, "src", "serve.py"), os.path.join(ROOT, "mobile", "www"), "8766"],
                                 stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
time.sleep(0.6)

results = []


def check(name, cond, detail=""):
    results.append((bool(cond), name, detail))
    print(("PASS " if cond else "FAIL ") + name + ("" if cond else "  -> " + str(detail)))


def new_page(b, opts, errs, reqs):
    ctx = b.new_context(**opts)
    ctx.add_init_script(INIT)
    pg = ctx.new_page()
    pg.on("pageerror", lambda e: errs.append("pageerror " + str(e)))
    pg.on("console", lambda m: errs.append("console " + m.type + ": " + m.text) if m.type == "error" else None)
    ctx.on("request", lambda r: reqs.append(r.url))
    return ctx, pg


def act(pg, a, val=None, wait=900, scope=""):
    sel = scope + f'[data-act="{a}"]' + (f'[data-val="{val}"]' if val else "")
    pg.locator(sel).first.click()
    pg.wait_for_timeout(wait)


def close_sheet(pg):
    act(pg, "closeSheet", scope=".sheet-panel ", wait=500)


def state(pg):
    return pg.evaluate("JSON.parse(localStorage.getItem('debtout.app.v3') || 'null')")


def screen_h1(pg):
    loc = pg.locator(".view h1")
    return loc.first.inner_text() if loc.count() else ""


def no_overflow(pg):
    return pg.evaluate("""() => {
      const v = document.querySelector('.view');
      return document.documentElement.scrollWidth <= innerWidth + 1 && (!v || v.scrollWidth <= v.clientWidth + 1);
    }""")


with sync_playwright() as p:
    b = p.chromium.launch()
    errs, reqs = [], []
    try:
        ctx, pg = new_page(b, MOBILE, errs, reqs)
        cdp = ctx.new_cdp_session(pg)
        pg.goto(BASE)
        pg.wait_for_timeout(1600)

        # ---- welcome ----
        check("title", "DebtOut" in pg.title(), pg.title())
        check("manifest link", pg.locator('link[rel="manifest"]').count() == 1)
        check("security policy inside the app page", "object-src 'none'" in (pg.locator('meta[http-equiv="Content-Security-Policy"]').get_attribute("content") or ""))
        check("beta tag on welcome", pg.locator(".wordmark .beta-tag").inner_text().strip() == "BETA")
        body = pg.locator(".view").inner_text()
        check("no fake login on welcome", "Ya tengo cuenta" not in body and "contraseña" not in body.lower(), body)
        check("welcome buttons", pg.locator('[data-act="start"]').count() == 1 and pg.locator('[data-act="importOpen"]').count() == 1)
        pg.evaluate("document.fonts.ready")
        pg.wait_for_timeout(300)
        fonts = pg.evaluate("""() => [document.fonts.check("16px Inter"), document.fonts.check("700 25px 'Inter Display'"),
                               getComputedStyle(document.querySelector('.view h1')).fontFamily]""")
        check("Inter fonts load from the site", fonts[0] and fonts[1] and "Inter Display" in fonts[2], fonts)
        check("no horizontal overflow (welcome)", no_overflow(pg))

        # ---- start (terms + optional name) ----
        act(pg, "start")
        check("start screen", screen_h1(pg) == "Antes de empezar", screen_h1(pg))
        act(pg, "accept", wait=300)
        check("terms required", "Marca la casilla" in pg.locator("#err").inner_text(), pg.locator("#err").inner_text())
        pg.fill("#st-name", "  Ana   López ")
        act(pg, "toggleTerms", wait=200)
        act(pg, "accept")
        s = state(pg)
        check("salary after accepting", screen_h1(pg) == "¿Cuánto cobras?", screen_h1(pg))
        check("acceptance stored", s and s["accepted"] and s["accepted"]["v"] == "2026-10-28" and s["name"] == "Ana López", s and (s.get("accepted"), s.get("name")))
        act(pg, "back")
        check("back from salary goes to start", screen_h1(pg) == "Antes de empezar")
        act(pg, "accept")
        check("terms remembered on the way back", screen_h1(pg) == "¿Cuánto cobras?")

        # ---- onboarding with a second debt (no Premium gate in the beta) ----
        act(pg, "next")
        act(pg, "next")
        check("debts step", screen_h1(pg) == "Tus deudas", screen_h1(pg))
        tz = ZoneInfo("Europe/Madrid")
        tomorrow = (datetime.datetime.now(tz) + datetime.timedelta(days=1)).day
        act(pg, "debtAdd", wait=700)
        check("second debt opens the form, not a gate", pg.locator("#df-bal").count() == 1 and pg.locator('[data-act="gateYes"]').count() == 0)
        pg.fill("#df-name", "Préstamo coche")
        pg.fill("#df-bal", "1.200")
        pg.fill("#df-apr", "7,5")
        pg.fill("#df-min", "60")
        pg.fill("#df-day", str(tomorrow))
        act(pg, "debtSave", scope=".sheet-panel ")
        check("two debts", pg.locator(".dcard").count() == 2, pg.locator(".dcard").count())
        act(pg, "next")
        check("split step", screen_h1(pg) == "Reparte tu sueldo", screen_h1(pg))
        if pg.locator('[data-act="calc"][disabled]').count():
            act(pg, "recommend", wait=500)
        act(pg, "calc", wait=1800)
        check("result screen", pg.locator(".bignum").count() == 1, screen_h1(pg))
        act(pg, "finish", wait=1500)
        check("home greets by first name", "Hola, Ana" in pg.locator(".hello-name").inner_text(), pg.locator(".hello-name").inner_text())
        check("beta card on home", "Beta abierta" in pg.locator(".view").inner_text())
        check("no install card without an install prompt", pg.locator(".inst").count() == 0)

        # ---- goals: second goal is free in the beta ----
        act(pg, "tab", "goals")
        act(pg, "goalAdd", wait=700)
        check("second goal opens the form", pg.locator("#gf-name").count() == 1)
        pg.fill("#gf-name", "Viaje")
        pg.fill("#gf-target", "900")
        act(pg, "goalSave", scope=".sheet-panel ")
        check("two goals", pg.locator(".gcard").count() == 2)

        # ---- reminders ----
        act(pg, "tab", "pay")
        act(pg, "remToggle", wait=500)
        check("reminders switch on (no gate)", pg.locator(".switch.on").count() == 1 and state(pg)["reminders"] is True)
        act(pg, "tab", "home")
        rem = pg.locator(".status.rem")
        check("home shows what is due soon", rem.count() == 1 and "Préstamo coche" in rem.inner_text(), rem.inner_text() if rem.count() else "none")
        pg.reload()
        pg.wait_for_timeout(1500)
        t = pg.locator(".toast.bell")
        check("reminder toast on open", t.count() == 1 and "Préstamo coche" in t.inner_text(), t.inner_text() if t.count() else "none")
        pg.reload()
        pg.wait_for_timeout(1500)
        check("reminder toast only once a day", pg.locator(".toast.bell.show").count() == 0)

        # ---- settings ----
        act(pg, "tab", "settings")
        txt = pg.locator(".view").inner_text()
        check("settings rows", all(x in txt for x in ["Nombre", "Ana", "Beta, todo incluido", "Exportar mis datos", "Restaurar una copia", "Borrar mis datos", "DebtOut beta " + VERSION]), txt)
        check("no fake account rows", "Cerrar sesión" not in txt and "Borrar cuenta" not in txt and "email" not in txt.lower(), txt)
        check("no feedback row without a contact email", pg.locator('[data-act="feedback"]').count() == 0)
        check("no install row on a browser that cannot install", pg.locator('[data-act="install"]').count() == 0)
        act(pg, "editName", wait=600)
        pg.fill("#nm-name", "Ana")
        act(pg, "nameSave", scope=".sheet-panel ")
        check("name edit", state(pg)["name"] == "Ana")

        # simulated install prompt (Chrome / Android)
        pg.evaluate("""() => {
          const e = new Event('beforeinstallprompt', { cancelable: true });
          e.prompt = () => { window.__prompted = true; };
          e.userChoice = Promise.resolve({ outcome: 'accepted' });
          window.dispatchEvent(e);
        }""")
        pg.wait_for_timeout(400)
        check("install row appears with an install prompt", pg.locator('[data-act="install"]').count() == 1)
        act(pg, "tab", "home")
        check("install card on home", pg.locator(".inst").count() == 1)
        act(pg, "install", scope=".inst ", wait=700)
        check("install prompt shown and card hidden", pg.evaluate("window.__prompted === true") and state(pg)["installHidden"] is True and pg.locator(".inst").count() == 0)

        # ---- premium screen ----
        act(pg, "toPremium")
        txt = pg.locator(".view").inner_text()
        check("premium screen is beta info, no purchase", "Beta abierta" in txt and "Contratar" not in txt and "prototipo" not in txt.lower(), txt)
        act(pg, "back")

        # ---- legal ----
        act(pg, "tab", "settings")
        for doc, must, mustnot in [("aviso", ["Versión beta", "Inter"], ["Unbounded", "Manrope"]),
                                   ("privacidad", ["Netlify, Inc.", "Marco de Privacidad", "Anthropic", "Usar mi plan", "Nunca tu nombre", "no las usa para entrenar"], ["Google Fonts", "contraseña (guardada", "Stripe", "Invita"]),
                                   ("cookies", ["debtout.app.v3", "debtout-app-"], ["Google Fonts"]),
                                   ("terminos", ["Beta gratuita", "DebtOut Premium en la app", "1 mes gratis", "una sola vez por cuenta", "24 horas antes", "Asistente de IA", PRICE + " al mes (IVA incluido)"], ["Invita a un amigo", "Es el precio final", "2 meses", "0,99"])]:
            act(pg, "legal", doc, wait=600)
            lt = pg.locator(".sheet .legal").inner_text()
            check(f"legal {doc} content", all(m in lt for m in must) and not any(m in lt for m in mustnot), [m for m in must if m not in lt] + [m for m in mustnot if m in lt])
            if doc == "aviso":
                check("owner placeholders highlighted while empty", pg.locator(".sheet mark.ph").count() >= 4)
            close_sheet(pg)

        # ---- export (download) ----
        act(pg, "exportData", wait=600)
        with pg.expect_download() as dl:
            act(pg, "exportFile", scope=".sheet-panel ", wait=600)
        path = os.path.join(TMP, "copia.json")
        dl.value.save_as(path)
        data = json.load(open(path, encoding="utf-8"))
        check("export file", data.get("app") == "DebtOut" and data["plan"]["name"] == "Ana" and len(data["plan"]["debts"]) == 2 and dl.value.suggested_filename.startswith("debtout-copia-"), dl.value.suggested_filename)
        check("last export remembered", bool(state(pg)["lastExport"]))
        close_sheet(pg)

        # ---- delete ----
        act(pg, "deleteAsk", wait=600)
        act(pg, "deleteYes", wait=1500)
        check("delete wipes storage and returns to welcome", pg.locator('[data-act="start"]').count() == 1 and pg.evaluate("localStorage.getItem('debtout.app.v3')") in (None, "null") or state(pg)["stage"] == "onboarding")
        pg.wait_for_timeout(400)
        s = state(pg)
        check("no personal data left after delete", s is None or (s["name"] == "" and s["accepted"] is None), s and (s.get("name"), s.get("accepted")))

        # ---- import from file on the welcome screen ----
        act(pg, "importOpen", wait=600)
        pg.set_input_files("#imp-file", path)
        pg.wait_for_timeout(1600)
        check("import restores the plan", "Hola, Ana" in pg.locator(".view").inner_text() and len(state(pg)["debts"]) == 2)

        # ---- hostile backup file ----
        evil = {"app": "DebtOut", "plan": {"v": 3, "stage": "app", "name": "<img src=x onerror=\"window.__xss=1\">",
                "salary": "abc", "freq": "<b>", "expenses": [{"id": "e\"><img src=x onerror=window.__xss=2>", "icon": "javascript:alert(1)", "name": "<script>window.__xss=3</script>", "amount": "50", "day": "<b>7</b>"}],
                "debts": [{"id": "d1", "type": "<svg onload=window.__xss=4>", "name": "<img src=x onerror=window.__xss=5>", "balance": 500, "original": 500, "apr": 300, "min": 20, "day": "<i>5</i>"}],
                "goals": [], "debtPct": 999, "savePct": -5, "paid": {"<img>": True, "d:d1": True}, "accepted": {"at": "x", "v": "2026-10-22"}}}
        act(pg, "tab", "settings")
        act(pg, "importOpen", wait=600)
        pg.fill("#imp-json", json.dumps(evil))
        act(pg, "importDo", scope=".sheet-panel ", wait=1600)
        for tab in ["home", "debts", "pay", "settings"]:
            act(pg, "tab", tab, wait=900)
        s = state(pg)
        check("hostile backup cannot run code", pg.evaluate("window.__xss === undefined") and pg.locator('.view img[src="x"]').count() == 0)
        check("hostile backup values are coerced", s["salary"] == 0 and s["freq"] == "mensual" and s["debts"][0]["apr"] == 100 and s["debts"][0]["day"] == 1
              and s["debts"][0]["type"] == "other" and s["expenses"][0]["icon"] == "tag" and s["expenses"][0]["day"] is None and s["debtPct"] == 80 and s["savePct"] == 0
              and list(s["paid"].keys()) == ["d:d1"] and '"' not in s["expenses"][0]["id"], s)
        act(pg, "importOpen", wait=600)
        pg.fill("#imp-json", "esto no es una copia")
        act(pg, "importDo", scope=".sheet-panel ", wait=500)
        check("invalid backup shows an error", "No parece una copia" in pg.locator("#serr").inner_text())
        close_sheet(pg)
        # restore the good copy for the rest of the run
        act(pg, "importOpen", wait=600)
        pg.set_input_files("#imp-file", path)
        pg.wait_for_timeout(1600)

        # ---- service worker + offline ----
        sw = pg.evaluate("""async () => {
          const reg = await navigator.serviceWorker.ready;
          const keys = await caches.keys();
          const c = await caches.open(keys.find(k => k.startsWith('debtout-app-')));
          const urls = (await c.keys()).map(r => new URL(r.url).pathname);
          return { active: !!reg.active, scope: reg.scope, keys, urls };
        }""")
        check("service worker active with app cache", sw["active"] and any(k.startswith("debtout-app-" + VERSION + "-") for k in sw["keys"]), sw)
        check("app shell, fonts and owner file cached", all(u in sw["urls"] for u in ["/", "/app/", "/fonts/inter-400.v1.woff", "/fonts/inter-display-700.v1.woff", "/datos-titular.js", "/manifest.webmanifest"]), sw["urls"])
        pg.reload()
        pg.wait_for_timeout(1500)
        check("page controlled by the service worker", pg.evaluate("!!navigator.serviceWorker.controller"))
        ctx.set_offline(True)
        pg.reload()
        pg.wait_for_timeout(1800)
        off = pg.evaluate("""() => ({ hello: (document.querySelector('.hello-name') || {}).textContent, titular: typeof window.DEBTOUT_TITULAR,
                                     font: document.fonts.check('16px Inter') })""")
        check("works offline", off["hello"] == "Hola, Ana" and off["titular"] == "object" and off["font"], off)
        act(pg, "tab", "settings")
        act(pg, "legal", "privacidad", wait=600)
        check("legal texts offline", "Netlify" in pg.locator(".sheet .legal").inner_text())
        close_sheet(pg)
        ctx.set_offline(False)

        # ---- installability (Chrome's own checks) ----
        man = cdp.send("Page.getAppManifest")
        check("manifest parses without errors", not man.get("errors"), man.get("errors"))
        inst = cdp.send("Page.getInstallabilityErrors")
        errs_i = [e["errorId"] for e in inst.get("installabilityErrors", []) if e["errorId"] not in ("in-incognito",)]
        check("Chrome sees the app as installable", not errs_i, inst)

        # ---- small phone layout ----
        pg.set_viewport_size({"width": 320, "height": 640})
        for tab in ["home", "debts", "pay", "goals", "settings"]:
            act(pg, "tab", tab, wait=900)
            check(f"no horizontal overflow at 320px ({tab})", no_overflow(pg))

        csp = pg.evaluate("window.__csp")
        check("no CSP violations (mobile run)", not csp, csp)
        ctx.close()

        # ---- owner details filled in ----
        ctx2, pg2 = new_page(b, dict(MOBILE, service_workers="block"), errs, reqs)  # page.route cannot see requests a service worker makes
        filled = 'window.DEBTOUT_TITULAR = { nombre: "Lucía Prueba Ejemplo", nif: "00000000T", domicilio: "Calle Mayor 1, 50001 Zaragoza", email: "hola@debtout.example", registro: "" };'
        pg2.route("**/datos-titular.js", lambda r: r.fulfill(status=200, content_type="text/javascript", body=filled))
        pg2.goto(BASE)
        pg2.wait_for_timeout(1500)
        act(pg2, "legal", "cookies", wait=600)
        close_sheet(pg2)
        pg2.evaluate("""() => {
          const s = { v: 3, stage: 'app', name: 'Leo', salary: 1500, freq: 'mensual', expenses: [], debts: [], goals: [], debtPct: 0, savePct: 10,
                      accepted: { at: new Date().toISOString(), v: '2026-10-22' } };
          localStorage.setItem('debtout.app.v3', JSON.stringify(s));
        }""")
        pg2.reload()
        pg2.wait_for_timeout(1500)
        act(pg2, "tab", "settings")
        act(pg2, "legal", "aviso", wait=600)
        lt = pg2.locator(".sheet .legal").inner_text()
        check("owner details fill the legal notice", "Lucía Prueba Ejemplo" in lt and "00000000T" in lt and "Calle Mayor 1" in lt and pg2.locator(".sheet mark.ph").count() == 0, lt[:400])
        check("company registry line hidden for individuals", "Datos registrales" not in lt)
        check("contact email is a mailto link", pg2.locator('.sheet a[href="mailto:hola@debtout.example"]').count() >= 1)
        close_sheet(pg2)
        check("feedback row with a contact email", pg2.locator('[data-act="feedback"]').count() == 1)
        ctx2.close()

        # ---- desktop + reduced motion smoke ----
        ctx3, pg3 = new_page(b, dict(DESKTOP, reduced_motion="reduce"), errs, reqs)
        pg3.goto(BASE)
        pg3.wait_for_timeout(1000)
        check("desktop shows the phone frame", pg3.locator(".statusbar").is_visible() and pg3.locator('[data-act="start"]').count() == 1)
        check("no CSP violations (desktop run)", not pg3.evaluate("window.__csp"))
        ctx3.close()

        # ---- 404 ----
        ctx4, pg4 = new_page(b, MOBILE, errs, reqs)
        r = pg4.goto(BASE + "no-existe")
        check("404 page", r.status == 404 and "Esta página no existe" in pg4.content() and pg4.locator('a[href="/app/"]').count() == 1)
        ctx4.close()

        # ---- website: home page ----
        ctx5, pg5 = new_page(b, MOBILE, errs, reqs)
        pg5.goto(SITE)
        pg5.wait_for_timeout(900)
        check("website title and hero", "DebtOut" in pg5.title() and "Adiós a las deudas" in pg5.locator("h1").inner_text(), pg5.title())
        check("website links to the app", pg5.locator('a[href="app/"]').count() >= 4)
        check("security policy inside the website page", pg5.locator('meta[http-equiv="Content-Security-Policy"]').count() == 1
              and not os.path.exists(os.path.join(ROOT, "web", "_headers")) and not os.path.exists(os.path.join(ROOT, "netlify.toml")))
        check("website images load", pg5.evaluate("[...document.querySelectorAll('.hero img')].every(i => i.complete && i.naturalWidth > 0)"))
        price_txt = pg5.locator("#precio").inner_text()
        check("website shows the Premium price", "1 mes gratis" in price_txt and "y después " + PRICE + " al mes" in price_txt, price_txt)
        stale = [os.path.relpath(os.path.join(d, f), ROOT) for top in ["web", os.path.join("mobile", "www")] for d, _, fs in os.walk(os.path.join(ROOT, top))
                 for f in fs if f.endswith((".html", ".js")) and "0,99" in open(os.path.join(d, f), encoding="utf-8").read()]
        check("no old price left in the published files", not stale, stale)
        check("website has no fake reviews or ratings", not any(w in pg5.locator("body").inner_text().lower() for w in ["opiniones de usuarios", "valoración", "★", "descargas"]))
        lo, hi = payoff(3200, 19.9, 95), payoff(3200, 19.9, 195)
        out = pg5.evaluate("['r-min-t','r-min-i','r-plan-t','r-plan-i','r-win-t'].map(id => document.getElementById(id).textContent)")
        check("calculator: minimum payment only", out[0] == dur(lo[0]) and out[1] == "Intereses: " + eur(lo[1]), (out, dur(lo[0]), eur(lo[1])))
        check("calculator: with 100 € extra", out[2] == dur(hi[0]) and out[3] == "Intereses: " + eur(hi[1]), (out, dur(hi[0]), eur(hi[1])))
        check("calculator: savings line", out[4] == f"Te ahorras {eur(lo[1] - hi[1])} en intereses y terminas {dur(lo[0] - hi[0])} antes.", out[4])
        pg5.fill("#c-min", "40")
        pg5.locator("#c-extra").fill("0")
        pg5.wait_for_timeout(200)
        check("calculator: payment below the interest", "no baja nunca" in pg5.locator("#r-win-t").inner_text() and pg5.locator("#r-win.bad").count() == 1, pg5.locator("#r-win-t").inner_text())
        pg5.fill("#c-bal", "")
        check("calculator: asks for missing data", "Escribe lo que debes" in pg5.locator("#r-win-t").inner_text())
        pg5.set_viewport_size({"width": 320, "height": 640})
        check("no horizontal overflow at 320px (website)", pg5.evaluate("document.documentElement.scrollWidth <= innerWidth + 1"))
        for slug, title in [("aviso-legal", "Aviso legal"), ("privacidad", "Política de privacidad"), ("cookies", "Política de cookies"), ("terminos", "Términos y condiciones")]:
            r = pg5.goto(SITE + slug + "/")
            pg5.wait_for_timeout(300)
            ok = r.status == 200 and pg5.locator("h1").inner_text() == title and pg5.locator(".legal h3").count() >= 2
            check(f"legal page /{slug}/", ok and pg5.evaluate("document.documentElement.scrollWidth <= innerWidth + 1"), (r.status, pg5.locator("h1").inner_text()))
        check("legal pages highlight missing owner details", pg5.goto(SITE + "aviso-legal/") and pg5.locator("mark.ph").count() >= 4)
        check("footer links to every legal page", all(pg5.locator(f'.foot a[href="../{s}/"]').count() == 1 for s in ["aviso-legal", "privacidad", "cookies", "terminos"]))
        check("no CSP violations (website)", not pg5.evaluate("window.__csp"), pg5.evaluate("window.__csp"))
        robots = pg5.goto(SITE + "robots.txt")
        check("robots.txt", robots.status == 200 and "User-agent: *" in robots.text())
        ctx5.close()

        # someone with a plan comes back to the website; an old install (home screen at /) goes straight to the app
        ctx5, pg5 = new_page(b, dict(MOBILE, service_workers="block"), errs, reqs)
        pg5.add_init_script("localStorage.setItem('debtout.app.v3', JSON.stringify({ v: 3, stage: 'app', expenses: [], debts: [], goals: [] }))")
        pg5.goto(SITE)
        pg5.wait_for_timeout(500)
        check("website offers to open the saved plan", "Abrir mi plan" in pg5.locator(".hero .btn-primary").inner_text(), pg5.locator(".hero .btn-primary").inner_text())
        ctx5.close()
        ctx5, pg5 = new_page(b, dict(MOBILE, service_workers="block"), errs, reqs)
        pg5.add_init_script("Object.defineProperty(navigator, 'standalone', { get: () => true })")
        pg5.goto(SITE)
        pg5.wait_for_timeout(1200)
        check("installed app opened at / goes to the app", pg5.url == BASE, pg5.url)
        ctx5.close()

        # ---- back button / gesture on the web ----
        ctx6, pg6 = new_page(b, dict(MOBILE, service_workers="block"), errs, reqs)
        pg6.add_init_script("if (!localStorage.getItem('debtout.app.v3')) localStorage.setItem('debtout.app.v3', JSON.stringify(" + json.dumps(SEED) + "))")
        pg6.goto(SITE)
        pg6.goto(BASE)
        pg6.wait_for_timeout(1300)
        act(pg6, "tab", "debts", wait=500)
        pg6.evaluate("history.back()")
        pg6.wait_for_timeout(700)
        check("back from a tab goes to Inicio", pg6.locator(".hello-name").count() == 1 and pg6.url == BASE, pg6.url)
        act(pg6, "bell", wait=500)
        pg6.evaluate("history.back()")
        pg6.wait_for_timeout(600)
        check("back closes a sheet and stays in the app", pg6.locator("#sheet").is_hidden() and pg6.url == BASE, pg6.url)
        act(pg6, "editPlan", wait=500)
        pg6.evaluate("history.back()")
        pg6.wait_for_timeout(700)
        check("back from an edit screen returns to it", pg6.locator(".hello-name").count() == 1)
        pg6.evaluate("history.back()")
        pg6.wait_for_timeout(700)
        check("back from Inicio leaves the app", pg6.url == SITE, pg6.url)

        # ---- the month shown is the plan's month (it used to drift one month ahead for every month that went by) ----
        now = datetime.datetime.now(ZoneInfo("Europe/Madrid"))
        def ym(off):
            m = now.year * 12 + now.month - 1 + off
            return m // 12, m % 12
        y, m = ym(-3)
        plan = dict(SEED, month=1, startMonth=f"{y}-{m + 1:02d}")
        pg6.evaluate("p => localStorage.setItem('debtout.app.v3', JSON.stringify(p))", plan)
        pg6.goto(BASE)
        pg6.wait_for_timeout(1300)
        y, m = ym(-2)
        label = pg6.evaluate("window.__debtout.monthLabel(0)")
        check("month = start month + months closed", label == f"{MONTHS[m]} de {y}", (label, MONTHS[m], y))
        check("home says the plan is behind", "Tu plan sigue en" in pg6.locator(".view").inner_text())
        old = dict(SEED, month=4)
        old.pop("startMonth", None)
        pg6.evaluate("p => localStorage.setItem('debtout.app.v3', JSON.stringify(p))", old)
        pg6.goto(BASE)
        pg6.wait_for_timeout(1300)
        label = pg6.evaluate("window.__debtout.monthLabel(0)")
        check("plans from before the fix show the current month", label == f"{MONTHS[now.month - 1]} de {now.year}" and "Tu plan sigue en" not in pg6.locator(".view").inner_text(), label)
        ctx6.close()

        # ---- tablet: full screen with a centred column, no phone frame ----
        ctx7, pg7 = new_page(b, dict(viewport={"width": 820, "height": 1180}, device_scale_factor=2, is_mobile=True, has_touch=True,
                                     locale="es-ES", timezone_id="Europe/Madrid", service_workers="block"), errs, reqs)
        pg7.add_init_script("localStorage.setItem('debtout.app.v3', JSON.stringify(" + json.dumps(SEED) + "))")
        pg7.goto(BASE)
        pg7.wait_for_timeout(1300)
        lay = pg7.evaluate("""() => ({ fs: document.documentElement.classList.contains('fs'), bar: getComputedStyle(document.querySelector('.statusbar')).display,
                                      phone: document.getElementById('phone').getBoundingClientRect().width, col: document.querySelector('.scr').getBoundingClientRect().width })""")
        check("tablet uses the whole screen", lay["fs"] and lay["bar"] == "none" and lay["phone"] == 820 and lay["col"] <= 620, lay)
        ctx7.close()

        # ---- the phone app build (mobile/www) with a pretend phone ----
        www = os.path.join(ROOT, "mobile", "www")
        idx = open(os.path.join(www, "index.html"), encoding="utf-8").read()
        check("phone build: native bridge, no manifest", '<script src="native.js"></script>' in idx and "manifest" not in idx and os.path.getsize(os.path.join(www, "native.js")) > 5000)
        ctx8, pg8 = new_page(b, dict(MOBILE, service_workers="allow"), errs, reqs)
        pg8.add_init_script(fake_phone(dict(SEED, name="Nativa")))
        pg8.goto(NATIVE_BASE)
        pg8.wait_for_timeout(1000)
        nat = lambda: pg8.evaluate("window.__nat.calls")
        check("phone: plan read from native storage", "Hola, Nativa" in pg8.locator(".view").inner_text() and json.loads(pg8.evaluate("localStorage.getItem('debtout.app.v3')"))["name"] == "Nativa")
        check("phone: splash hidden once the app is drawn", ["ready"] in nat())
        check("phone: no service worker and no install prompts", pg8.evaluate("navigator.serviceWorker.getRegistrations().then(r => r.length)") == 0
              and pg8.locator(".inst").count() == 0)
        act(pg8, "tab", "pay", wait=500)
        check("phone: reminders text mentions notifications", "notificación" in pg8.locator(".rem").inner_text())
        act(pg8, "remToggle", wait=1200)
        rem = pg8.evaluate("""() => ({ asked: window.__nat.calls.some(c => c[0] === 'request'), list: window.__nat.last || [],
                                     nine: (window.__nat.last || []).every(n => new Date(n.at).getHours() === 9 && new Date(n.at).getMinutes() === 0),
                                     future: (window.__nat.last || []).every(n => n.at > Date.now()),
                                     sorted: (window.__nat.last || []).every((n, i, a) => !i || a[i - 1].at <= n.at) })""")
        check("phone: turning reminders on asks permission and schedules notifications", rem["asked"] and 0 < len(rem["list"]) <= 60 and rem["nine"] and rem["future"] and rem["sorted"]
              and all(n["title"].startswith("Hoy pagas ") for n in rem["list"]), rem)
        paid_first = pg8.evaluate("""() => { const l = window.__debtout.reminderList(); const card = l.filter(n => n.title.indexOf('Tarjeta') > -1);
                                            const now = new Date(); return card.length > 0 && card.every(n => n.at.getMonth() !== now.getMonth() || n.at.getFullYear() !== now.getFullYear()); }""")
        check("phone: a payment already marked as done is reminded next month", paid_first)
        act(pg8, "payToggle", wait=400, scope=".prow:not(.done) ")
        check("phone: haptic tap when marking a payment", ["haptic", "tap"] in nat())
        act(pg8, "tab", "home", wait=500)
        act(pg8, "bell", wait=500)
        closed = pg8.evaluate("window.__nat.back()")
        pg8.wait_for_timeout(400)
        check("phone: back button closes a sheet", closed is True and pg8.locator("#sheet").is_hidden())
        act(pg8, "tab", "settings", wait=500)
        pg8.evaluate("window.__nat.back()")
        pg8.wait_for_timeout(600)
        check("phone: back button goes to Inicio", pg8.locator(".hello-name").count() == 1)
        check("phone: back button at Inicio leaves the app", pg8.evaluate("window.__nat.back()") is False)
        act(pg8, "tab", "settings", wait=500)
        act(pg8, "exportData", wait=500)
        act(pg8, "exportFile", scope=".sheet-panel ", wait=600)
        shared = [c for c in nat() if c[0] == "share"]
        check("phone: backup goes through the share sheet", shared and shared[0][1].startswith("debtout-copia-") and shared[0][2] > 200 and bool(state(pg8)["lastExport"]), shared)
        close_sheet(pg8)
        act(pg8, "importOpen", wait=500)
        check("phone: any file can be picked to restore", pg8.locator("#imp-file").get_attribute("accept") is None)
        close_sheet(pg8)
        act(pg8, "deleteAsk", wait=500)
        act(pg8, "deleteYes", wait=600)
        check("phone: deleting wipes native storage and notifications", ["remove", "debtout.app.v3"] in nat() and ["clear"] in nat())
        ctx8.close()
        # a plan made before the native copy existed is copied into native storage
        ctx8, pg8 = new_page(b, MOBILE, errs, reqs)
        pg8.add_init_script(fake_phone(None) + ";localStorage.setItem('debtout.app.v3', JSON.stringify(" + json.dumps(SEED) + "))")
        pg8.goto(NATIVE_BASE)
        pg8.wait_for_timeout(1000)
        check("phone: existing plan copied to native storage", pg8.evaluate("JSON.parse(window.__nat.store['debtout.app.v3'] || '{}').name") == "Ana")
        ctx8.close()

        # ---- phone without Premium: free plan, locks and the free month ----
        ctx9, pg9 = new_page(b, MOBILE, errs, reqs)
        pg9.add_init_script(fake_phone(SEED, sub=FREE))
        pg9.goto(NATIVE_BASE)
        pg9.wait_for_timeout(1000)
        nat9 = lambda: pg9.evaluate("window.__nat.calls")
        check("free phone: Inicio offers Premium", "Hazte Premium" in pg9.locator(".promo").inner_text() and "Beta" not in pg9.locator(".view").inner_text())
        act(pg9, "toAssistant", wait=500)
        check("free phone: the assistant is locked", "El asistente es Premium" in pg9.locator(".sheet-panel").inner_text())
        close_sheet(pg9)
        act(pg9, "tab", "pay", wait=500)
        act(pg9, "remToggle", wait=500)
        check("free phone: reminders are locked", pg9.locator('[data-act="gateYes"]').count() == 1 and state(pg9).get("reminders") is not True)
        close_sheet(pg9)
        act(pg9, "tab", "debts", wait=500)
        act(pg9, "debtAdd", wait=500)
        check("free phone: a second debt is locked", "Más de una deuda es Premium" in pg9.locator(".sheet-panel").inner_text())
        act(pg9, "gateYes", scope=".sheet-panel ", wait=1000)
        prem = pg9.locator(".view").inner_text()
        check("free phone: Premium screen shows the free month and the price", "1 mes gratis de Premium" in prem and "Después, " + PRICE + " al mes" in prem
              and "Empezar mi mes gratis" in prem and "solo para quien no lo ha disfrutado antes" in prem and "se renueva cada mes por " + PRICE in prem and "24 horas" in prem, prem)
        act(pg9, "subBuy", wait=1200)
        check("free phone: starting the free month unlocks Premium", ["buy"] in nat9() and pg9.locator(".toast").inner_text().startswith("¡Listo! Tu mes gratis")
              and screen_h1(pg9) != "1 mes gratis de Premium", pg9.locator(".toast").inner_text())
        act(pg9, "tab", "settings", wait=500)
        txt = pg9.locator(".view").inner_text()
        check("free phone: settings show the free month", "Mes gratis" in txt and "mes gratis hasta el" in txt and "DebtOut " + VERSION in txt and "beta " + VERSION not in txt, txt)
        act(pg9, "toPremium", wait=700)
        act(pg9, "subManage", wait=300)
        check("free phone: manage subscription opens the store", any(c[0] == "manage" for c in nat9()))
        ctx9.close()

        # someone who already used the free month: the store offers no trial and nothing to restore
        ctx9, pg9 = new_page(b, MOBILE, errs, reqs)
        pg9.add_init_script(fake_phone(SEED, sub=FREE, offer=dict(OFFER, trial=False)))
        pg9.goto(NATIVE_BASE)
        pg9.wait_for_timeout(1000)
        act(pg9, "tab", "settings", wait=500)
        act(pg9, "toPremium", wait=900)
        prem = pg9.locator(".view").inner_text()
        check("no second free month: the price is shown without a trial", "Suscribirme por " + PRICE + " al mes" in prem and "gratis de Premium" not in prem and "solo para quien" not in prem, prem)
        act(pg9, "subRestore", wait=600)
        check("restoring without a subscription says so", "No hay ninguna suscripción activa" in pg9.locator(".toast").inner_text())
        ctx9.close()

        # ---- phone with Premium: the assistant ----
        errs_ai = []  # this scenario fails requests on purpose (limit, no connection)
        ctx10, pg10 = new_page(b, MOBILE, errs_ai, reqs)
        pg10.add_init_script(fake_phone(dict(SEED, name="Nativa")))
        sent, replies = [], []
        def fake_ai(route):
            sent.append(json.loads(route.request.post_data))
            status, body = replies.pop(0) if replies else (200, {"respuesta": "Vale.", "quedan": 20, "limite": 30})
            if status == "abort":
                return route.abort()
            route.fulfill(status=status, content_type="application/json", body=json.dumps(body),
                          headers={"Access-Control-Allow-Origin": "*"})
        pg10.route("https://asistente.test/**", fake_ai)
        pg10.goto(NATIVE_BASE)
        pg10.wait_for_timeout(1000)
        check("assistant: Inicio invites Premium users to ask", "Pregunta a tu asistente" in pg10.locator(".promo").inner_text())
        act(pg10, "toAssistant", wait=700)
        check("assistant: screen with suggestions and the AI notice", screen_h1(pg10) == "Pregúntame lo que quieras" and pg10.locator('[data-act="aiSuggest"]').count() >= 6
              and "generadas por IA" in pg10.locator("#ai-left").inner_text())
        replies.append((200, {"respuesta": "**Primero** la tarjeta:\n- Paga el mínimo de todas\n- El resto, a la de mayor TAE\n<img src=x onerror=window.__xss=1>", "quedan": 29, "limite": 30}))
        act(pg10, "aiSuggest", "¿Qué deuda pago primero?", wait=900)
        req = sent[-1] if sent else {}
        check("assistant: sends the question with the purchase id and no plan", req.get("usuario", "").startswith("$RCAnonymousID:") and req.get("mensajes") == [{"rol": "usuario", "texto": "¿Qué deuda pago primero?"}]
              and "plan" not in req, req)
        bubble = pg10.locator(".msg.ai").last
        check("assistant: answer shown with bold and a list, safely", bubble.locator("b").count() == 1 and bubble.locator("li").count() == 2
              and pg10.evaluate("window.__xss === undefined") and bubble.locator("img").count() == 0 and "<img" in bubble.inner_text())
        check("assistant: questions left this month", "Te quedan 29 preguntas" in pg10.locator("#ai-left").inner_text())
        act(pg10, "aiPlanToggle", wait=500)
        check("assistant: sharing the plan asks first", "¿Usar tu plan?" in pg10.locator(".sheet-panel").inner_text() and "Tu nombre no se envía" in pg10.locator(".sheet-panel").inner_text())
        act(pg10, "aiPlanYes", scope=".sheet-panel ", wait=600)
        pg10.fill("#ai-q", "¿Cuándo termino?")
        act(pg10, "aiSend", wait=900)
        req = sent[-1]
        plan = req.get("plan") or {}
        check("assistant: with consent the plan goes along, without the name", plan.get("deudas") and plan["deudas"][0]["pendiente"] == 3200 and plan.get("sueldo_neto_al_mes") == 1850
              and "Nativa" not in json.dumps(req) and len(req["mensajes"]) == 3 and req["mensajes"][1]["rol"] == "asistente" and state(pg10)["aiPlan"] is True, json.dumps(req)[:300])
        replies.append((429, {"error": "limit", "limite": 30, "renueva": "2026-11-01"}))
        pg10.fill("#ai-q", "Otra")
        act(pg10, "aiSend", wait=800)
        check("assistant: monthly limit explained", "Has usado tus 30 preguntas" in pg10.locator(".msg.err").last.inner_text() and "1 de noviembre" in pg10.locator(".msg.err").last.inner_text())
        pg10.evaluate("window.__debtout.ui.chatLeft = null")
        replies.append(("abort", None))
        pg10.fill("#ai-q", "¿Y si no hay red?")
        act(pg10, "aiSend", wait=800)
        check("assistant: no connection, with a retry button", "No hay conexión" in pg10.locator(".msg.err").last.inner_text() and pg10.locator('[data-act="aiRetry"]').count() == 1)
        act(pg10, "aiRetry", wait=800)
        check("assistant: retry sends the question again", sent[-1]["mensajes"][-1]["texto"] == "¿Y si no hay red?" and pg10.locator(".msg.ai").last.inner_text() == "Vale.")
        pg10.evaluate("window.__nat.back()")
        pg10.wait_for_timeout(600)
        check("assistant: back button returns to Inicio", pg10.locator(".hello-name").count() == 1)
        check("assistant: no script errors", not [e for e in errs_ai if e.startswith("pageerror")], errs_ai)
        ctx10.close()

        # ---- web: the assistant is in the phone app; the beta can end on a date ----
        ctx11, pg11 = new_page(b, dict(MOBILE, service_workers="block"), errs, reqs)
        pg11.add_init_script("localStorage.setItem('debtout.app.v3', JSON.stringify(" + json.dumps(SEED) + "))")
        pg11.goto(BASE)
        pg11.wait_for_timeout(1300)
        act(pg11, "tab", "settings", wait=500)
        act(pg11, "toAssistant", wait=500)
        sheet = pg11.locator(".sheet-panel").inner_text()
        check("web: the assistant points to the phone app", "El asistente es Premium" in sheet and "app para iPhone y Android" in sheet)
        ctx11.close()
        page = open(os.path.join(ROOT, "web", "app", "index.html"), encoding="utf-8").read()
        assert page.count('var BETA_END = "";') == 1
        for when, future in [((now + datetime.timedelta(days=40)).strftime("%Y-%m-%d"), True), ((now - datetime.timedelta(days=1)).strftime("%Y-%m-%d"), False)]:
            ctx11, pg11 = new_page(b, dict(MOBILE, service_workers="block"), errs, reqs)
            pg11.add_init_script("localStorage.setItem('debtout.app.v3', JSON.stringify(" + json.dumps(SEED) + "))")
            body = page.replace('var BETA_END = "";', f'var BETA_END = "{when}";')
            pg11.route(BASE, html_route(body))
            pg11.goto(BASE)
            pg11.wait_for_timeout(1300)
            if future:
                check("web beta with an end date: announced on Inicio", "Todo gratis hasta el" in pg11.locator(".promo").inner_text())
                act(pg11, "toPremium", wait=600)
                check("web beta with an end date: explained on the plan screen", "La beta de la web termina el" in pg11.locator(".view").inner_text())
            else:
                act(pg11, "tab", "debts", wait=500)
                act(pg11, "debtAdd", wait=500)
                check("web after the beta: free plan with 1 debt", "Más de una deuda es Premium" in pg11.locator(".sheet-panel").inner_text())
                act(pg11, "gateYes", scope=".sheet-panel ", wait=800)
                check("web after the beta: Premium is in the app", screen_h1(pg11) == "Plan gratis" and PRICE in pg11.locator(".view").inner_text())
            ctx11.close()
    except Exception:
        traceback.print_exc()
        check("test run finished without exceptions", False)
    b.close()
mobile_server.terminate()

AI_TEST = "https://asistente.test/"  # the phone app's own assistant server (faked in the tests)
external = sorted(set(u for u in reqs if not (u.startswith(SITE) or u.startswith(NATIVE_BASE) or u.startswith(AI_TEST) or u.startswith("data:") or u.startswith("blob:"))))
check("no requests to third parties", not external, external)
check("no page or console errors", not [e for e in errs if "404" not in e and "no-existe" not in e], errs)

failed = [r for r in results if not r[0]]
print(f"\n{len(results) - len(failed)}/{len(results)} checks passed")
sys.exit(1 if failed else 0)
