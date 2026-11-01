"""Icons and splash screens for the iPhone and Android apps (mobile/ios, mobile/android), drawn like the web icons.

Android: launcher icons (classic, round and adaptive with a monochrome layer for themed icons), notification icon,
splash screens. iPhone: the 1024 px app icon (no transparency, as Apple requires) and the launch image.
Run it after `npx cap add` or whenever the logo changes: python3 src/make_native_assets.py
"""
import os
from playwright.sync_api import sync_playwright
from make_icons import MARK_SHAPE, defs, grid, icon_svg, mark_group

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "mobile")
RES = os.path.join(ROOT, "android", "app", "src", "main", "res")
IOS = os.path.join(ROOT, "ios", "App", "App", "Assets.xcassets")
BG = "#070b08"
DENSITY = {"mdpi": 1, "hdpi": 1.5, "xhdpi": 2, "xxhdpi": 3, "xxxhdpi": 4}


def svg(w, h, body, uid="n", scale=1.0):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">'
            + defs(uid, max(w, h), scale) + body + "</svg>")


def silhouette(size, mark_px):
    """White mark with its cut-outs, on transparent: notification and themed (monochrome) icons."""
    s = mark_px / 104  # the cross is 104 units wide inside its 120-unit box
    tx = ty = size / 2 - 60 * s
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" viewBox="0 0 {size} {size}">'
            '<defs><mask id="c" maskUnits="userSpaceOnUse" x="0" y="0" width="120" height="120"><rect width="120" height="120" fill="#fff"/>'
            '<rect x="19" y="44" width="82" height="32" rx="5" fill="none" stroke="#000" stroke-width="5"/><circle cx="60" cy="60" r="10.5" fill="#000"/></mask></defs>'
            f'<g transform="translate({tx:.2f} {ty:.2f}) scale({s:.4f})"><g mask="url(#c)" fill="#fff">{MARK_SHAPE}</g>'
            '<circle cx="60" cy="60" r="5" fill="#fff"/></g></svg>')


def adaptive_background(size):
    """Gradient, grid and glow of the web icon, without the mark (the system adds its own mask)."""
    return svg(size, size, f'<rect width="{size}" height="{size}" fill="url(#bgn)"/>' + grid("n", size, size / 12)
               + f'<circle cx="{size/2}" cy="{size/2}" r="{size*0.42:.2f}" fill="url(#glown)"/>', "n", size / 512 * 3.0)


def adaptive_foreground(size):
    # 108 dp canvas; the mark stays inside the 66 dp safe circle.
    scale = size * 0.52 / 104
    return svg(size, size, mark_group("n", scale, size / 2, size / 2), "n", scale)


def round_icon(size):
    return svg(size, size, f'<clipPath id="rc"><circle cx="{size/2}" cy="{size/2}" r="{size/2}"/></clipPath><g clip-path="url(#rc)">'
               f'<rect width="{size}" height="{size}" fill="url(#bgn)"/>' + grid("n", size, size / 12)
               + f'<circle cx="{size/2}" cy="{size/2}" r="{size*0.46:.2f}" fill="url(#glown)"/>'
               + mark_group("n", size * 0.56 / 104, size / 2, size / 2) + "</g>", "n", size * 0.56 / 104)


def splash(w, h, frac=0.26):
    """frac: mark width as a share of the shorter side (the iPhone image is a square cropped to the screen)."""
    m = min(w, h) * frac
    scale = m / 104
    r = min(w, h) * 0.5
    return svg(w, h, f'<rect width="{w}" height="{h}" fill="{BG}"/>'
               + f'<circle cx="{w/2}" cy="{h/2}" r="{r:.1f}" fill="url(#glown)"/>'
               + mark_group("n", scale, w / 2, h / 2), "n", scale)


def render(page, markup, path, w, h, transparent=False):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    page.set_viewport_size({"width": int(w), "height": int(h)})
    page.set_content(f'<html><body style="margin:0;background:transparent">{markup}</body></html>')
    page.screenshot(path=path, omit_background=transparent, clip={"x": 0, "y": 0, "width": int(w), "height": int(h)})


with sync_playwright() as p:
    b = p.chromium.launch()
    pg = b.new_page(device_scale_factor=1)
    n = 0
    for d, k in DENSITY.items():
        legacy, fg = round(48 * k), round(108 * k)
        render(pg, icon_svg(legacy, "any"), f"{RES}/mipmap-{d}/ic_launcher.png", legacy, legacy, True)
        render(pg, round_icon(legacy), f"{RES}/mipmap-{d}/ic_launcher_round.png", legacy, legacy, True)
        render(pg, adaptive_foreground(fg), f"{RES}/mipmap-{d}/ic_launcher_foreground.png", fg, fg, True)
        render(pg, adaptive_background(fg), f"{RES}/mipmap-{d}/ic_launcher_background.png", fg, fg)
        render(pg, silhouette(fg, fg * 0.5), f"{RES}/mipmap-{d}/ic_launcher_monochrome.png", fg, fg, True)
        st = round(24 * k)
        render(pg, silhouette(st, st * 0.92), f"{RES}/drawable-{d}/ic_stat_debtout.png", st, st, True)
        n += 6
    for folder in os.listdir(RES):
        if folder.startswith("drawable") and os.path.exists(f"{RES}/{folder}/splash.png"):
            from PIL import Image
            w, h = Image.open(f"{RES}/{folder}/splash.png").size
            render(pg, splash(w, h), f"{RES}/{folder}/splash.png", w, h)
            n += 1
    render(pg, icon_svg(1024, "maskable"), f"{IOS}/AppIcon.appiconset/AppIcon-512@2x.png", 1024, 1024)
    for name in ["splash-2732x2732.png", "splash-2732x2732-1.png", "splash-2732x2732-2.png"]:
        render(pg, splash(2732, 2732, 0.15), f"{IOS}/Splash.imageset/{name}", 2732, 2732)
    n += 4
    b.close()

# Apple rejects app icons with an alpha channel.
from PIL import Image
icon = f"{IOS}/AppIcon.appiconset/AppIcon-512@2x.png"
Image.open(icon).convert("RGB").save(icon, optimize=True)
for name in ["splash-2732x2732.png", "splash-2732x2732-1.png", "splash-2732x2732-2.png"]:
    path = f"{IOS}/Splash.imageset/{name}"
    Image.open(path).convert("RGB").save(path, optimize=True)
print(n, "images written")
