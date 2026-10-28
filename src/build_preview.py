"""Build a phone-friendly preview of the beta for the claude.ai artifact viewer.

Same app as the website build, adapted to the viewer's frame: fonts inlined as data URIs, no service worker,
no install prompts, no file download (the viewer blocks downloads; copying the text still works),
and the notch / home-bar insets left to the viewer's own page padding.
"""
import base64, json, os, re

SRC = os.path.dirname(os.path.abspath(__file__))
FONTS = os.path.join(SRC, "..", "web", "fonts")
OUT = os.path.join(SRC, "preview", "debtout-beta.html")
VERSION = "0.10.0"

app = open(os.path.join(SRC, "app.html"), encoding="utf-8").read()

# legal texts, same source as the website build
legal_src = open(os.path.join(SRC, "legal_beta.html"), encoding="utf-8").read()
parts = re.split(r"<!--doc:(\w+)\|([^>]+)-->", legal_src)
docs = {}
for i in range(1, len(parts), 3):
    html = parts[i + 2].strip().replace("<table>", '<div class="tbl"><table>').replace("</table>", "</table></div>")
    docs[parts[i]] = {"t": parts[i + 1], "h": html}
legal_json = json.dumps(docs, ensure_ascii=False).replace("</", "<\\/")


def swap(s, old, new, count=1):
    assert s.count(old) == count, (old[:80], s.count(old))
    return s.replace(old, new)


app = swap(app, "/*LEGAL_START*/{}/*LEGAL_END*/", "/*LEGAL_START*/" + legal_json + "/*LEGAL_END*/")
app = swap(app, '"__VERSION__"', json.dumps(VERSION + " · vista previa"))
app = swap(app, "__SW_URL__", "sw.js")

# fonts as data URIs
for name in sorted(os.listdir(FONTS)):
    if name.endswith(".woff"):
        data = base64.b64encode(open(os.path.join(FONTS, name), "rb").read()).decode()
        app = swap(app, f'url("fonts/{name}")', f'url("data:font/woff;base64,{data}")')

# the viewer pads the page for the notch and the home bar itself
app = app.replace("env(safe-area-inset-top,0px)", "0px").replace("env(safe-area-inset-bottom,0px)", "0px")

# no service worker or install prompts inside the viewer
app = swap(app, "function canInstall() { return !NATIVE && !standalone() && (!!installEvt || isIOS()); }", "function canInstall() { return false; }")
app = swap(app, 'if (!NATIVE && "serviceWorker" in navigator && (location.protocol === "https:"', 'if (false && "serviceWorker" in navigator && (location.protocol === "https:"')

# downloads are blocked in the viewer: offer the copy button only
app = swap(app, """'<p class="muted sm">Guarda una copia de tu plan en tu móvil, en tu ordenador o en tu nube. Para recuperarla, usa Restaurar una copia en este o en otro dispositivo.</p>' +
      '<button class="btn btn-primary" data-act="exportFile">' + ic(NATIVE ? "share" : "download") + (NATIVE ? "Guardar o enviar la copia" : "Descargar copia") + "</button>" +""",
           """'<p class="muted sm">Copia el texto y guárdalo en una nota o envíatelo. Para recuperarlo, usa Restaurar una copia y pega el texto.</p>' +""")
app = swap(app, """'<button class="btn btn-ghost" data-act="copyExport">' + ic("copy") + "Copiar el texto</button>";""",
           """'<button class="btn btn-primary" data-act="copyExport">' + ic("copy") + "Copiar el texto</button>";""")

page = '<title>DebtOut</title>\n<meta name="claude:viewport-fit-sides" content="cover">\n' + app
os.makedirs(os.path.dirname(OUT), exist_ok=True)
open(OUT, "w", encoding="utf-8").write(page)
print(OUT, len(page.encode()), "bytes")
