"""Screenshots of the real app with sample data, for the install dialog, the website and link previews.

Needs the local server running (python3 src/serve.py) and a fresh build (python3 src/build.py).
Outputs:
  web/screenshots/inicio.png, pagos.png, escritorio.png   web app manifest (Chrome/Android install dialog)
  web/img/app-inicio.webp, app-plan.webp, app-pagos.webp, app-deudas.webp   website
  web/img/og.png                                          link previews (1200 x 630)
Usage: python3 src/make_screens.py
"""
import base64, io, os
from playwright.sync_api import sync_playwright
from PIL import Image

BASE = "http://127.0.0.1:8765/"
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "web")
SHOTS = os.path.join(ROOT, "screenshots")
IMG = os.path.join(ROOT, "img")
os.makedirs(SHOTS, exist_ok=True)
os.makedirs(IMG, exist_ok=True)

PLAN = """{
  v: 3, stage: '%s', name: 'Ana', salary: 1850, freq: 'mensual',
  expenses: [
    { id: 'e1', icon: 'home', name: 'Alquiler', amount: 650, day: 1 },
    { id: 'e2', icon: 'cart', name: 'Comida', amount: 260, day: null },
    { id: 'e3', icon: 'zap', name: 'Luz e internet', amount: 95, day: 12 },
    { id: 'e4', icon: 'bus', name: 'Transporte', amount: 60, day: 3 }
  ],
  debts: [
    { id: 'd1', type: 'card', name: 'Tarjeta de crédito', balance: %s, original: 3200, apr: 19.9, min: 95, day: 5 },
    { id: 'd2', type: 'car', name: 'Préstamo del coche', balance: %s, original: 5200, apr: 7.5, min: 140, day: 20 }
  ],
  debtPct: 24, savePct: 8,
  goals: [{ id: 'g1', name: 'Fondo de emergencia', target: 3000, saved: 1140 }, { id: 'g2', name: 'Viaje a Lisboa', target: 900, saved: 0 }],
  premium: false, reminders: true, paid: { 'e:e1': true, 'e:e4': true, 'd:d1': true }, month: 4, startMonth: '%s', paidTotal: 2090, savedTotal: 590,
  accepted: { at: '2026-10-22T10:00:00Z', v: '2026-10-22' }, installHidden: true,
  remindDay: (function () { var d = new Date(); return d.getFullYear() + '-' + String(d.getMonth() + 1).padStart(2, '0') + '-' + String(d.getDate()).padStart(2, '0'); })()
}"""


def seed(stage, start):
    bal = ("2310", "4100") if stage == "app" else ("3200", "5200")
    return "localStorage.setItem('debtout.app.v3', JSON.stringify(" + PLAN % (stage, bal[0], bal[1], start) + "))"


def webp(png_bytes, path, quality=82):
    Image.open(io.BytesIO(png_bytes)).convert("RGB").save(path, "WEBP", quality=quality, method=6)
    print(os.path.relpath(path, ROOT), os.path.getsize(path))


def png(png_bytes, path):
    Image.open(io.BytesIO(png_bytes)).convert("RGB").save(path, optimize=True)
    print(os.path.relpath(path, ROOT), os.path.getsize(path))


PHONE = dict(viewport={"width": 390, "height": 844}, device_scale_factor=2, is_mobile=True, has_touch=True,
             locale="es-ES", timezone_id="Europe/Madrid", reduced_motion="reduce", service_workers="block")

with sync_playwright() as p:
    b = p.chromium.launch()
    # The plan started 4 months ago and is up to date: the home screen shows this month.
    start = b.new_page().evaluate("() => { const d = new Date(); d.setMonth(d.getMonth() - 4); return d.getFullYear() + '-' + String(d.getMonth() + 1).padStart(2, '0'); }")

    phone = b.new_context(**PHONE)
    phone.add_init_script(seed("app", start))
    pg = phone.new_page()
    pg.goto(BASE + "app/")
    pg.wait_for_timeout(1400)
    shots = {"inicio": pg.screenshot()}
    for tab in ["pay", "debts"]:
        pg.locator(f'[data-act="tab"][data-val="{tab}"]').click()
        pg.wait_for_timeout(700)
        shots[tab] = pg.screenshot()
    phone.close()

    # The result screen comes at the end of the set-up, so walk the last step of it.
    phone = b.new_context(**PHONE)
    phone.add_init_script("if (!sessionStorage.getItem('seeded')) { sessionStorage.setItem('seeded', '1'); " + seed("onboarding", start) + "; }")
    pg = phone.new_page()
    pg.goto(BASE + "app/")
    pg.wait_for_timeout(1400)
    pg.locator('[data-act="start"]').click()
    pg.wait_for_timeout(500)
    pg.locator('[data-act="toggleTerms"]').click()
    pg.locator('[data-act="accept"]').click()
    pg.wait_for_timeout(600)
    for _ in range(3):
        pg.locator('[data-act="next"]').first.click()
        pg.wait_for_timeout(600)
    pg.locator('[data-act="calc"]').click()
    pg.wait_for_timeout(1500)
    shots["plan"] = pg.screenshot()
    phone.close()

    desk = b.new_context(viewport={"width": 1280, "height": 800}, device_scale_factor=1, locale="es-ES",
                         timezone_id="Europe/Madrid", reduced_motion="reduce", service_workers="block")
    desk.add_init_script(seed("app", start))
    pg = desk.new_page()
    pg.goto(BASE + "app/")
    pg.wait_for_timeout(1400)
    png(pg.screenshot(), os.path.join(SHOTS, "escritorio.png"))
    desk.close()

    png(shots["inicio"], os.path.join(SHOTS, "inicio.png"))
    png(shots["pay"], os.path.join(SHOTS, "pagos.png"))
    webp(shots["inicio"], os.path.join(IMG, "app-inicio.webp"))
    webp(shots["pay"], os.path.join(IMG, "app-pagos.webp"))
    webp(shots["debts"], os.path.join(IMG, "app-deudas.webp"))
    webp(shots["plan"], os.path.join(IMG, "app-plan.webp"))

    # ---- link preview image ----
    def data(path, mime):
        return f"data:{mime};base64," + base64.b64encode(open(path, "rb").read()).decode()
    fonts = os.path.join(ROOT, "fonts")
    shot = "data:image/png;base64," + base64.b64encode(shots["inicio"]).decode()
    og = f"""<html><head><style>
@font-face{{font-family:"ID";font-weight:700;src:url("{data(os.path.join(fonts, 'inter-display-700.v1.woff'), 'font/woff')}")}}
@font-face{{font-family:"I";font-weight:600;src:url("{data(os.path.join(fonts, 'inter-600.v1.woff'), 'font/woff')}")}}
*{{box-sizing:border-box}}
body{{margin:0;width:1200px;height:630px;overflow:hidden;background:#030504;color:#ecf4e8;font-family:"I";position:relative}}
.bg{{position:absolute;inset:0;background:radial-gradient(620px 480px at 10% 0%,rgba(140,198,63,.22),transparent 70%),radial-gradient(600px 500px at 100% 100%,rgba(92,207,230,.14),transparent 70%)}}
.grid{{position:absolute;inset:0;background-image:linear-gradient(rgba(140,198,63,.06) 1px,transparent 1px),linear-gradient(90deg,rgba(140,198,63,.06) 1px,transparent 1px);background-size:40px 40px;-webkit-mask-image:linear-gradient(to bottom,#000,transparent 85%)}}
.txt{{position:absolute;left:84px;top:96px;width:620px}}
.brand{{display:flex;align-items:center;gap:14px;font-family:"ID";font-size:30px;letter-spacing:-.01em}}
.brand svg{{width:48px;height:48px;color:#8cc63f}}
.beta{{font-family:"I";font-size:13px;letter-spacing:.16em;color:#b6ea6e;background:rgba(140,198,63,.16);box-shadow:inset 0 0 0 1.5px rgba(140,198,63,.45);padding:4px 10px;border-radius:99px}}
h1{{font-family:"ID";font-size:66px;line-height:1.02;letter-spacing:-.03em;margin:38px 0 22px}}
h1 em{{font-style:normal;color:#b6ea6e}}
p{{font-size:25px;color:#8c9e8f;margin:0;line-height:1.4}}
.phone{{position:absolute;right:92px;top:58px;width:330px;height:714px;border-radius:48px;padding:10px;background:#0a0f0b;box-shadow:0 0 0 1.5px #24322a,0 0 0 4px #1c271f,0 40px 100px rgba(0,0,0,.8),0 0 120px rgba(140,198,63,.18)}}
.phone img{{width:100%;height:100%;object-fit:cover;object-position:top;border-radius:39px;display:block}}
</style></head><body><div class="bg"></div><div class="grid"></div>
<div class="txt"><div class="brand"><svg viewBox="0 0 120 120"><defs><mask id="m" maskUnits="userSpaceOnUse" x="0" y="0" width="120" height="120"><rect width="120" height="120" fill="#fff"/><rect x="19" y="44" width="82" height="32" rx="5" fill="none" stroke="#000" stroke-width="4.5"/><circle cx="60" cy="60" r="10" fill="#000"/></mask></defs><g mask="url(#m)" fill="currentColor"><rect x="43" y="8" width="34" height="104" rx="9"/><rect x="8" y="33" width="104" height="54" rx="9"/></g><circle cx="60" cy="60" r="5" fill="currentColor"/></svg>DebtOut <span class="beta">BETA</span></div>
<h1>Sal de deudas con un plan <em>para cada mes</em></h1>
<p>Reparte tu sueldo y mira en qué mes terminas de pagar. Sin conectar tu banco. Gratis en la beta.</p></div>
<div class="phone"><img src="{shot}"></div></body></html>"""
    pg = b.new_page(viewport={"width": 1200, "height": 630}, device_scale_factor=1)
    pg.set_content(og)
    pg.wait_for_timeout(500)
    png(pg.screenshot(), os.path.join(IMG, "og.png"))
    b.close()
