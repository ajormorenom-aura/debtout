"""Tiny static server that behaves like Netlify for local tests: applies _headers rules and serves 404.html."""
import http.server, os, sys, fnmatch

ROOT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "web")
PORT = int(sys.argv[2]) if len(sys.argv) > 2 else 8765


def parse_headers(path):
    rules, cur = [], None
    if not os.path.exists(path):
        return rules
    for line in open(path, encoding="utf-8"):
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if not line.startswith((" ", "\t")):
            cur = (line.strip(), [])
            rules.append(cur)
        elif cur and ":" in line:
            k, v = line.strip().split(":", 1)
            cur[1].append((k.strip(), v.strip()))
    return rules


RULES = parse_headers(os.path.join(ROOT, "_headers"))
TYPES = {".webmanifest": "application/manifest+json", ".woff": "font/woff", ".svg": "image/svg+xml", ".js": "text/javascript", ".json": "application/json"}


class H(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *a, **k):
        super().__init__(*a, directory=ROOT, **k)

    def log_message(self, *a):
        pass

    def guess_type(self, path):
        ext = os.path.splitext(path)[1].lower()
        return TYPES.get(ext) or super().guess_type(path)

    def end_headers(self):
        p = self.path.split("?")[0]
        seen = {}
        for pat, hs in RULES:
            if fnmatch.fnmatch(p, pat):
                for k, v in hs:
                    seen[k] = v
        for k, v in seen.items():
            self.send_header(k, v)
        super().end_headers()

    def send_error(self, code, message=None, explain=None):
        if code == 404 and os.path.exists(os.path.join(ROOT, "404.html")):
            body = open(os.path.join(ROOT, "404.html"), "rb").read()
            self.send_response(404)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            if self.command != "HEAD":
                self.wfile.write(body)
            return
        super().send_error(code, message, explain)


if __name__ == "__main__":
    http.server.ThreadingHTTPServer(("127.0.0.1", PORT), H).serve_forever()
