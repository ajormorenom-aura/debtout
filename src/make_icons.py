"""Render DebtOut app icons (PNG + SVG) with Playwright/Chromium."""
import os, sys
from playwright.sync_api import sync_playwright

OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "web", "icons")

# The DebtOut mark (viewBox 0 0 120 120): a cross of two bars with a bill outline cut into it.
MARK_SHAPE = (
    '<rect x="43" y="8" width="34" height="104" rx="9"/>'
    '<rect x="8" y="33" width="104" height="54" rx="9"/>'
)


def mark_group(uid, scale, cx, cy, glow=True):
    """Mark centred on (cx, cy); the cut and the hole are real see-through cuts (SVG mask)."""
    tx, ty = cx - 60 * scale, cy - 60 * scale
    g = f'<g transform="translate({tx:.2f} {ty:.2f}) scale({scale})">'
    if glow:
        g += f'<g mask="url(#cut{uid})"><g filter="url(#blur{uid})" opacity=".55" fill="#8cc63f">{MARK_SHAPE}</g></g>'
    g += (f'<g mask="url(#cut{uid})" fill="url(#fill{uid})">{MARK_SHAPE}</g>'
          f'<circle cx="60" cy="60" r="5" fill="url(#fill{uid})"/>'
          '</g>')
    return g


def defs(uid, size, scale):
    blur = 7 / scale * (size / 512)  # blur radius in mark units
    return (
        '<defs>'
        f'<linearGradient id="bg{uid}" x1="0" y1="0" x2=".55" y2="1">'
        '<stop offset="0" stop-color="#142017"/><stop offset=".6" stop-color="#090e0a"/><stop offset="1" stop-color="#050806"/></linearGradient>'
        f'<radialGradient id="glow{uid}" cx=".5" cy=".5" r=".5">'
        '<stop offset="0" stop-color="#8cc63f" stop-opacity=".34"/><stop offset=".55" stop-color="#8cc63f" stop-opacity=".08"/>'
        '<stop offset="1" stop-color="#8cc63f" stop-opacity="0"/></radialGradient>'
        f'<linearGradient id="fill{uid}" x1="0" y1="0" x2="1" y2="1">'
        '<stop offset="0" stop-color="#cdf58a"/><stop offset=".5" stop-color="#a6dc58"/><stop offset="1" stop-color="#7fbb35"/></linearGradient>'
        f'<linearGradient id="fade{uid}" x1="0" y1="0" x2="0" y2="1">'
        '<stop offset="0" stop-color="#fff" stop-opacity="1"/><stop offset=".7" stop-color="#fff" stop-opacity="0"/></linearGradient>'
        f'<mask id="gridMask{uid}"><rect width="{size}" height="{size}" fill="url(#fade{uid})"/></mask>'
        f'<mask id="cut{uid}" maskUnits="userSpaceOnUse" x="0" y="0" width="120" height="120">'
        '<rect width="120" height="120" fill="#fff"/>'
        '<rect x="19" y="44" width="82" height="32" rx="5" fill="none" stroke="#000" stroke-width="4.5"/>'
        '<circle cx="60" cy="60" r="10" fill="#000"/></mask>'
        f'<filter id="blur{uid}" x="-50%" y="-50%" width="200%" height="200%"><feGaussianBlur stdDeviation="{blur:.2f}"/></filter>'
        '</defs>'
    )


def grid(uid, size, step):
    lines = []
    n = int(size / step) + 1
    for i in range(1, n):
        p = i * step
        lines.append(f'<path d="M{p} 0V{size}M0 {p}H{size}"/>')
    return (f'<g mask="url(#gridMask{uid})" stroke="#8cc63f" stroke-opacity=".07" stroke-width="{max(1, size/512*1.4):.2f}">'
            + "".join(lines) + "</g>")


def icon_svg(size, kind):
    """kind: any (rounded square, transparent corners), maskable / apple (full bleed), favicon (small, simple)."""
    uid = kind
    if kind == "favicon":
        scale = size / 120 * 0.86
        r = size * 0.22
        return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" viewBox="0 0 {size} {size}">'
                + defs(uid, size, scale)
                + f'<rect width="{size}" height="{size}" rx="{r:.2f}" fill="#0a110c"/>'
                + mark_group(uid, scale, size / 2, size / 2, glow=False) + "</svg>")
    scale = size / 512 * 3.0
    body = (f'<rect width="{size}" height="{size}" fill="url(#bg{uid})"/>'
            + grid(uid, size, size / 16)
            + f'<circle cx="{size/2}" cy="{size/2}" r="{size*0.46:.2f}" fill="url(#glow{uid})"/>'
            + mark_group(uid, scale, size / 2, size / 2))
    if kind == "any":
        r = size * 0.225
        clip = f'<clipPath id="round{uid}"><rect width="{size}" height="{size}" rx="{r:.2f}"/></clipPath>'
        body = (f'<defs>{clip}</defs><g clip-path="url(#round{uid})">' + body
                + f'<rect x=".75" y=".75" width="{size-1.5}" height="{size-1.5}" rx="{r-0.75:.2f}" fill="none" stroke="#b6ea6e" stroke-opacity=".16" stroke-width="{max(1, size/256):.2f}"/></g>')
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" viewBox="0 0 {size} {size}">'
            + defs(uid, size, scale) + body + "</svg>")


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    JOBS = [
        ("icon-192.png", 192, "any"),
        ("icon-512.png", 512, "any"),
        ("icon-maskable-192.png", 192, "maskable"),
        ("icon-maskable-512.png", 512, "maskable"),
        ("apple-touch-icon.png", 180, "apple"),
        ("favicon-32.png", 32, "favicon"),
    ]

    with sync_playwright() as p:
        b = p.chromium.launch()
        for name, size, kind in JOBS:
            pg = b.new_page(viewport={"width": size, "height": size}, device_scale_factor=1)
            svg = icon_svg(size, kind)
            pg.set_content(f'<html><body style="margin:0;background:transparent">{svg}</body></html>')
            pg.screenshot(path=os.path.join(OUT, name), omit_background=(kind in ("any", "favicon")),
                          clip={"x": 0, "y": 0, "width": size, "height": size})
            pg.close()
            print(name, os.path.getsize(os.path.join(OUT, name)))
        b.close()

    # Scalable favicon for modern browsers.
    open(os.path.join(OUT, "favicon.svg"), "w").write(icon_svg(64, "favicon"))
    print("favicon.svg", os.path.getsize(os.path.join(OUT, "favicon.svg")))
