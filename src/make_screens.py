"""Store-style screenshots for the web app manifest (shown by Chrome/Android in the install dialog)."""
import os, sys
from playwright.sync_api import sync_playwright

BASE = "http://127.0.0.1:8765/"
OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "web", "screenshots")
os.makedirs(OUT, exist_ok=True)

SEED = """localStorage.setItem('debtout.app.v3', JSON.stringify({
  v: 3, stage: 'app', name: 'Ana', salary: 1850, freq: 'mensual',
  expenses: [
    { id: 'e1', icon: 'home', name: 'Alquiler', amount: 650, day: 1 },
    { id: 'e2', icon: 'cart', name: 'Comida', amount: 260, day: null },
    { id: 'e3', icon: 'zap', name: 'Luz e internet', amount: 95, day: 12 },
    { id: 'e4', icon: 'bus', name: 'Transporte', amount: 60, day: 3 }
  ],
  debts: [
    { id: 'd1', type: 'card', name: 'Tarjeta de crédito', balance: 2310, original: 3200, apr: 19.9, min: 95, day: 5 },
    { id: 'd2', type: 'car', name: 'Préstamo del coche', balance: 4100, original: 5200, apr: 7.5, min: 140, day: 20 }
  ],
  debtPct: 24, savePct: 8,
  goals: [{ id: 'g1', name: 'Fondo de emergencia', target: 3000, saved: 1140 }],
  premium: false, reminders: false, paid: { 'e:e1': true, 'e:e4': true, 'd:d1': true }, month: 4, paidTotal: 2090, savedTotal: 590,
  accepted: { at: '2026-10-22T10:00:00Z', v: '2026-10-22' }, installHidden: true
}))"""

with sync_playwright() as p:
    b = p.chromium.launch()
    phone = b.new_context(viewport={"width": 390, "height": 844}, device_scale_factor=2, is_mobile=True, has_touch=True,
                          locale="es-ES", timezone_id="Europe/Madrid", reduced_motion="reduce", service_workers="block")
    phone.add_init_script(SEED)
    pg = phone.new_page()
    pg.goto(BASE)
    pg.wait_for_timeout(1400)
    pg.screenshot(path=os.path.join(OUT, "inicio.png"))
    pg.locator('[data-act="tab"][data-val="pay"]').click()
    pg.wait_for_timeout(1200)
    pg.screenshot(path=os.path.join(OUT, "pagos.png"))
    phone.close()

    desk = b.new_context(viewport={"width": 1280, "height": 800}, device_scale_factor=1, locale="es-ES",
                         timezone_id="Europe/Madrid", reduced_motion="reduce", service_workers="block")
    desk.add_init_script(SEED)
    pg = desk.new_page()
    pg.goto(BASE)
    pg.wait_for_timeout(1400)
    pg.screenshot(path=os.path.join(OUT, "escritorio.png"))
    desk.close()
    b.close()

from PIL import Image
for n in ["inicio.png", "pagos.png", "escritorio.png"]:
    path = os.path.join(OUT, n)
    im = Image.open(path)
    im.convert("RGB").save(path, optimize=True)
    print(n, im.size, os.path.getsize(path))
