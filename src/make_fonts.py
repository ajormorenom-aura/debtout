"""Subset Inter (SIL Open Font License 1.1) to the characters DebtOut uses and save it as WOFF in web/fonts.

Needs fontTools (pip install fonttools) and the static Inter OTF files (https://github.com/rsms/inter).
Usage: python3 src/make_fonts.py /path/to/inter/otf/folder
If you change the subset, bump the ".v1" in the file names here, in app.html and in build.py (CORE list),
because the service worker keeps fonts by file name and never asks for them again.
"""
import os, subprocess, sys

SRC = sys.argv[1] if len(sys.argv) > 1 else "/usr/share/fonts/opentype/inter"
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "web", "fonts")
os.makedirs(OUT, exist_ok=True)

# Latin, Latin-1, Latin Extended-A, general punctuation, euro, arrows, minus sign.
UNICODES = "U+0020-007E,U+00A0-017F,U+0192,U+02C6,U+02DA,U+02DC,U+2000-206F,U+20AC,U+2122,U+2190-2193,U+2212,U+2215,U+FEFF,U+FFFD"
JOBS = [("Inter-Regular.otf", "inter-400.v1.woff"), ("Inter-SemiBold.otf", "inter-600.v1.woff"),
        ("Inter-Bold.otf", "inter-700.v1.woff"), ("Inter-ExtraBold.otf", "inter-800.v1.woff"),
        ("InterDisplay-SemiBold.otf", "inter-display-600.v1.woff"), ("InterDisplay-Bold.otf", "inter-display-700.v1.woff")]

for src, out in JOBS:
    subprocess.run(["pyftsubset", os.path.join(SRC, src), "--unicodes=" + UNICODES, "--flavor=woff",
                    "--output-file=" + os.path.join(OUT, out),
                    "--layout-features=kern,liga,calt,ccmp,locl,mark,mkmk,tnum,case,frac,numr,dnom",
                    "--name-IDs=*", "--name-legacy", "--name-languages=*", "--desubroutinize", "--no-hinting"], check=True)
    print(out, os.path.getsize(os.path.join(OUT, out)), "bytes")
