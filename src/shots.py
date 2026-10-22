"""Quick visual pass: walk the beta flow and screenshot key screens (mobile and desktop)."""
import json, os, tempfile, sys
from playwright.sync_api import sync_playwright

BASE = "http://127.0.0.1:8765/"
OUT = os.environ.get("SHOTS_DIR", os.path.join(tempfile.gettempdir(), "debtout-shots"))
os.makedirs(OUT, exist_ok=True)
which = sys.argv[1] if len(sys.argv) > 1 else "mobile"
VP = {"mobile": dict(viewport={"width": 390, "height": 844}, device_scale_factor=2, is_mobile=True, has_touch=True),
      "small": dict(viewport={"width": 320, "height": 640}, device_scale_factor=2, is_mobile=True, has_touch=True),
      "desktop": dict(viewport={"width": 1280, "height": 800}, device_scale_factor=1)}[which]

errs = []
with sync_playwright() as p:
    b = p.chromium.launch()
    ctx = b.new_context(**VP, locale="es-ES", timezone_id="Europe/Madrid")
    pg = ctx.new_page()
    pg.on("pageerror", lambda e: errs.append("pageerror " + str(e)))
    pg.on("console", lambda m: errs.append("console " + m.type + " " + m.text) if m.type in ("error", "warning") else None)

    def shot(name):
        pg.wait_for_timeout(700)
        pg.screenshot(path=f"{OUT}/{which}_{name}.png")

    def act(a, val=None):
        sel = (".sheet-panel " if a == "closeSheet" else "") + f'[data-act="{a}"]' + (f'[data-val="{val}"]' if val else "")
        pg.locator(sel).first.click()
        pg.wait_for_timeout(900)

    pg.goto(BASE)
    pg.wait_for_timeout(1500)
    shot("01_welcome")
    act("start")
    shot("02_start")
    pg.fill("#st-name", "Ana")
    act("toggleTerms")
    act("accept")
    shot("03_salary")
    act("next")
    act("next")
    shot("04_debts")
    act("next")
    pg.wait_for_timeout(300)
    shot("05_split")
    act("calc")
    pg.wait_for_timeout(1200)
    shot("06_result")
    act("finish")
    pg.wait_for_timeout(1200)
    shot("07_home")
    pg.locator(".view").evaluate("v => v.scrollTop = v.scrollHeight")
    shot("08_home_bottom")
    act("tab", "pay")
    shot("09_pay")
    act("tab", "settings")
    shot("10_settings")
    act("toPremium")
    shot("11_premium")
    act("back")
    act("legal", "aviso")
    shot("12_aviso")
    act("closeSheet")
    act("exportData")
    shot("13_export")
    act("closeSheet")
    act("importOpen")
    shot("14_import")
    print(json.dumps(errs, indent=1))
    b.close()
