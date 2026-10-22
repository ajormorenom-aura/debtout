"""iPhone-like checks in Chromium: install instructions path (iOS user agent) and notch / home-bar insets."""
import json, os, tempfile
from playwright.sync_api import sync_playwright

BASE = "http://127.0.0.1:8765/"
OUT = os.environ.get("SHOTS_DIR", os.path.join(tempfile.gettempdir(), "debtout-shots"))
UA = ("Mozilla/5.0 (iPhone; CPU iPhone OS 18_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) "
      "Version/18.6 Mobile/15E148 Safari/604.1")
ok = []

with sync_playwright() as p:
    b = p.chromium.launch()
    ctx = b.new_context(viewport={"width": 393, "height": 852}, device_scale_factor=2, is_mobile=True, has_touch=True,
                        user_agent=UA, locale="es-ES", timezone_id="Europe/Madrid", service_workers="block")
    pg = ctx.new_page()
    errs = []
    pg.on("pageerror", lambda e: errs.append(str(e)))
    cdp = ctx.new_cdp_session(pg)
    try:
        cdp.send("Emulation.setSafeAreaInsetsOverride", {"insets": {"top": 59, "topMax": 59, "bottom": 34, "bottomMax": 34, "left": 0, "leftMax": 0, "right": 0, "rightMax": 0}})
        insets = True
    except Exception as e:
        insets = False
        print("safe-area emulation unavailable:", str(e)[:160])
    pg.add_init_script("""localStorage.setItem('debtout.app.v3', JSON.stringify({ v: 3, stage: 'app', name: 'Ana', salary: 1850, freq: 'mensual',
      expenses: [{ id: 'e1', icon: 'home', name: 'Alquiler', amount: 650, day: 1 }],
      debts: [{ id: 'd1', type: 'card', name: 'Tarjeta de crédito', balance: 3200, original: 3200, apr: 19.9, min: 95, day: 5 }],
      goals: [{ id: 'g1', name: 'Fondo de emergencia', target: 3000, saved: 840 }], debtPct: 18, savePct: 10,
      accepted: { at: '2026-10-22T10:00:00Z', v: '2026-10-22' } }))""")
    pg.goto(BASE)
    pg.wait_for_timeout(1500)
    if insets:
        pad = pg.evaluate("getComputedStyle(document.getElementById('phone')).paddingTop")
        tab = pg.evaluate("getComputedStyle(document.getElementById('tabbar')).paddingBottom")
        print("phone padding-top", pad, "tabbar padding-bottom", tab)
        ok.append(("notch padding", pad == "59px"))
        ok.append(("home bar padding", tab == "44px"))
        pg.screenshot(path=f"{OUT}/ios_home_insets.png")
    ok.append(("install card on iPhone", pg.locator(".inst").count() == 1))
    pg.locator('.inst [data-act="install"]').click()
    pg.wait_for_timeout(800)
    sheet = pg.locator(".sheet-panel").inner_text() if pg.locator(".sheet-panel").count() else ""
    ok.append(("iPhone install instructions", "Añadir a pantalla de inicio" in sheet and "Compartir" in sheet))
    pg.screenshot(path=f"{OUT}/ios_install_sheet.png")
    pg.locator('.sheet-panel [data-act="closeSheet"]').first.click()
    pg.wait_for_timeout(500)
    pg.locator('[data-act="tab"][data-val="settings"]').click()
    pg.wait_for_timeout(900)
    ok.append(("install row in settings on iPhone", pg.locator('[data-act="install"]').count() == 1))
    # standalone (installed) mode hides install prompts
    pg.add_init_script("Object.defineProperty(navigator, 'standalone', { get: () => true })")
    pg.reload()
    pg.wait_for_timeout(1500)
    ok.append(("no install card once installed", pg.locator(".inst").count() == 0))
    ok.append(("no page errors", not errs))
    b.close()

for name, good in ok:
    print(("PASS " if good else "FAIL ") + name)
print(json.dumps(errs))
