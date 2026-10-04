#!/usr/bin/env python3
"""Version « à plat » du site pour GitHub Pages (tous les fichiers à la racine).

- déplace assets/*/* à la racine et réécrit les chemins
- ajoute CNAME (domaine), .nojekyll, et une politique CSP en <meta>
- retire les fichiers propres à Apache/Netlify
"""
import re
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DIST = ROOT / "dist"
OUT = Path(sys.argv[1])
if OUT.exists():
    shutil.rmtree(OUT)
OUT.mkdir(parents=True)

for f in DIST.iterdir():
    if f.is_file() and f.name not in (".htaccess", "_headers", "_redirects"):
        shutil.copy2(f, OUT / f.name)
for f in (DIST / "assets").rglob("*"):
    if f.is_file():
        assert not (OUT / f.name).exists(), f.name
        shutil.copy2(f, OUT / f.name)

ht = (DIST / ".htaccess").read_text(encoding="utf-8")
csp = re.search(r'Content-Security-Policy "([^"]+)"', ht).group(1)
csp = csp.replace("; frame-ancestors 'self'", "")  # non supporté en <meta>
meta = (f'<meta http-equiv="Content-Security-Policy" content="{csp}">\n'
        '<meta name="referrer" content="strict-origin-when-cross-origin">\n')

for p in OUT.glob("*.html"):
    s = p.read_text(encoding="utf-8")
    s = re.sub(r'(/?)assets/(?:css|js|fonts|img)/', r'\1', s)
    s = s.replace('<meta charset="utf-8">\n', '<meta charset="utf-8">\n' + meta, 1)
    p.write_text(s, encoding="utf-8")

css = OUT / "style.css"
css.write_text(css.read_text(encoding="utf-8").replace("../fonts/", ""), encoding="utf-8")
man = OUT / "site.webmanifest"
man.write_text(man.read_text(encoding="utf-8").replace("/assets/img/", "/"), encoding="utf-8")

(OUT / "CNAME").write_text("relaispopulaire.fr\n", encoding="utf-8")
(OUT / ".nojekyll").write_text("", encoding="utf-8")
left = [str(p.name) for p in OUT.iterdir() if "assets/" in p.read_text(errors="ignore")] if False else []
print("files:", len(list(OUT.iterdir())), sorted(x.name for x in OUT.iterdir()))
