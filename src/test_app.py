"""End-to-end checks for the DebtOut beta PWA, served the way Netlify would serve it (see serve.py)."""
import datetime, json, os, sys, tempfile, traceback
from zoneinfo import ZoneInfo
from playwright.sync_api import sync_playwright

BASE = "http://127.0.0.1:8765/"
TMP = tempfile.mkdtemp(prefix="debtout-test-")
MOBILE = dict(viewport={"width": 390, "height": 844}, device_scale_factor=2, is_mobile=True, has_touch=True,
              locale="es-ES", timezone_id="Europe/Madrid")
DESKTOP = dict(viewport={"width": 1280, "height": 800}, device_scale_factor=1, locale="es-ES", timezone_id="Europe/Madrid")
INIT = """
window.__csp = [];
document.addEventListener('securitypolicyviolation', function (e) { window.__csp.push(e.violatedDirective + ' ' + e.blockedURI); });
"""

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
        check("acceptance stored", s and s["accepted"] and s["accepted"]["v"] == "2026-10-22" and s["name"] == "Ana López", s and (s.get("accepted"), s.get("name")))
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
        check("settings rows", all(x in txt for x in ["Nombre", "Ana", "Beta, todo incluido", "Exportar mis datos", "Restaurar una copia", "Borrar mis datos", "DebtOut beta 0.9.0"]), txt)
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
                                   ("privacidad", ["Netlify, Inc.", "Marco de Privacidad"], ["Google Fonts", "contraseña (guardada", "Stripe", "Invita"]),
                                   ("cookies", ["debtout.app.v3", "debtout-app-"], ["Google Fonts"]),
                                   ("terminos", ["Beta gratuita", "Premium en el futuro"], ["Invita a un amigo", "0,99 € al mes, IVA incluido. Es el precio final"])]:
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
        check("service worker active with app cache", sw["active"] and any(k.startswith("debtout-app-0.9.0-") for k in sw["keys"]), sw)
        check("app shell, fonts and owner file cached", all(u in sw["urls"] for u in ["/", "/fonts/inter-400.v1.woff", "/fonts/inter-display-700.v1.woff", "/datos-titular.js", "/manifest.webmanifest"]), sw["urls"])
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
        check("404 page", r.status == 404 and "Esta página no existe" in pg4.content())
        ctx4.close()
    except Exception:
        traceback.print_exc()
        check("test run finished without exceptions", False)
    b.close()

external = sorted(set(u for u in reqs if not (u.startswith(BASE) or u.startswith("data:") or u.startswith("blob:"))))
check("no requests to third parties", not external, external)
check("no page or console errors", not [e for e in errs if "404" not in e and "no-existe" not in e], errs)

failed = [r for r in results if not r[0]]
print(f"\n{len(results) - len(failed)}/{len(results)} checks passed")
sys.exit(1 if failed else 0)
