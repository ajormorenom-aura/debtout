"""Crea venta/debtout-proyecto-venta.zip: el proyecto entero, limpio, para entregarlo al comprador.

Uso (desde cualquier carpeta):  python3 venta/crear_zip.py

Deja fuera lo que se puede regenerar o no debe salir de tu ordenador:
dependencias (node_modules), historial de git, compilaciones (dist, build, www…),
cachés, claves de firma y secretos (.dev.vars, *.keystore, *.jks) y los ZIP anteriores.
Si ya rellenaste tus datos en web/datos-titular.js, dentro del ZIP van en blanco.
Solo usa la biblioteca estándar de Python 3, así que funciona igual en Windows, macOS y Linux.
"""
import fnmatch
import os
import re
import subprocess
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "venta" / "debtout-proyecto-venta.zip"
PREFIX = "debtout"  # carpeta raíz dentro del ZIP

# Carpetas que se saltan estén donde estén.
SKIP_DIRS = {
    "node_modules", ".git", "dist", "build", ".wrangler", "__pycache__",
    ".gradle", ".kotlin", ".idea", ".vscode", "DerivedData", "Pods", "xcuserdata",
}
# Carpetas generadas por build.py o por Capacitor (se recrean con npm run sync).
SKIP_PATHS = {
    "src/preview",
    "mobile/www",
    "mobile/android/app/src/main/assets/public",
    "mobile/android/capacitor-cordova-android-plugins",
    "mobile/ios/App/App/public",
    "mobile/ios/capacitor-cordova-ios-plugins",
}
# Archivos sueltos: basura del sistema, secretos, claves de firma y binarios compilados.
SKIP_FILES = [
    ".DS_Store", "Thumbs.db", "*.pyc", "*.log",
    ".env", ".env.*", ".dev.vars", "local.properties",
    "*.keystore", "*.jks", "*.p12", "*.p8", "*.mobileprovision", "google-services.json",
    "GoogleService-Info.plist", "*.zip", "*.apk", "*.aab", "*.ipa",
]

OWNER_FILE = "web/datos-titular.js"
OWNER_FIELD = re.compile(r'^(\s*(?:nombre|nif|domicilio|email|registro):\s*)"[^"\n]*"', re.M)


def skipped(rel):
    parts = rel.split("/")
    if any(p in SKIP_DIRS for p in parts[:-1]):
        return True
    if any(rel == p or rel.startswith(p + "/") for p in SKIP_PATHS):
        return True
    return any(fnmatch.fnmatch(parts[-1], pat) for pat in SKIP_FILES)


def project_files():
    """Archivos del proyecto: los que git conoce (respetando .gitignore) o, sin git, todo lo de la carpeta."""
    try:
        out = subprocess.run(
            ["git", "-C", str(ROOT), "ls-files", "--cached", "--others", "--exclude-standard", "-z"],
            check=True, capture_output=True,
        ).stdout.decode("utf-8")
        files = [f for f in out.split("\0") if f]
    except (OSError, subprocess.CalledProcessError):
        files = []
        for dirpath, dirnames, filenames in os.walk(ROOT):
            rel_dir = Path(dirpath).relative_to(ROOT).as_posix()
            rel_dir = "" if rel_dir == "." else rel_dir + "/"
            dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS and (rel_dir + d) not in SKIP_PATHS]
            files += [rel_dir + f for f in filenames]
    return sorted(f for f in set(files) if (ROOT / f).is_file() and not skipped(f))


def main():
    files = project_files()
    blanked = False
    OUT.unlink(missing_ok=True)
    with zipfile.ZipFile(OUT, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for rel in files:
            src = ROOT / rel
            arc = f"{PREFIX}/{rel}"
            if rel == OWNER_FILE:
                text = src.read_text(encoding="utf-8")
                clean = OWNER_FIELD.sub(r'\1""', text)
                blanked = clean != text
                z.writestr(zipfile.ZipInfo.from_file(src, arc), clean, zipfile.ZIP_DEFLATED)
            else:
                z.write(src, arc)

    size = OUT.stat().st_size / 1024 / 1024
    print(f"Listo: {OUT.relative_to(ROOT)} ({len(files)} archivos, {size:.1f} MB)")
    if blanked:
        print(f"Tus datos de {OWNER_FILE} van en blanco dentro del ZIP (tu archivo no se ha tocado).")
    missing = [d for d in ("src", "web", "mobile", "server", "venta") if not any(f.startswith(d + "/") for f in files)]
    if missing:
        print("Ojo: faltan carpetas en el ZIP: " + ", ".join(missing), file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
