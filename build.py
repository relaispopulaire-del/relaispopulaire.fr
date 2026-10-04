#!/usr/bin/env python3
"""Génère le site statique Relais Populaire dans dist/.

Usage : python3 build.py
- Lit les données dans src/data/*.json
- Rend les gabarits Jinja2 de src/templates/
- Copie les fichiers statiques et produit sitemap, robots, manifest, .htaccess
"""
import base64
import hashlib
import json
import re
import shutil
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape
from markupsafe import Markup

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
DIST = ROOT / "dist"
BRAND = SRC / "brand"

site = json.loads((SRC / "data" / "site.json").read_text(encoding="utf-8"))
vdata = json.loads((SRC / "data" / "videos.json").read_text(encoding="utf-8"))
latest = json.loads((SRC / "data" / "latest.json").read_text(encoding="utf-8"))

MQ = timezone(timedelta(hours=-4))  # heure de la Martinique (UTC−4 toute l'année)
NOW = datetime.now(MQ)
MONTHS = ["janv.", "févr.", "mars", "avr.", "mai", "juin", "juil.", "août", "sept.", "oct.", "nov.", "déc."]


def date_label(iso):
    d = datetime.fromisoformat(iso).astimezone(MQ)
    return f"{d.day} {MONTHS[d.month - 1]}" + ("" if d.year == NOW.year else f" {d.year}")


# Titres YouTube → titres lisibles sur le site (émojis, hashtags, majuscule…)
EMOJI = re.compile(
    "[\U0001F000-\U0001FAFF⌀-⏿☀-➿⬀-⯿️‍⃣\U000E0020-\U000E007F]+"
)


def clean_title(t):
    t = re.sub(r"#[^\s#]+", " ", t)                       # hashtags
    t = re.sub(rf"(?<=\w)\s*{EMOJI.pattern}\s*(?=\w)", " — ", t)  # émoji entre deux mots
    t = EMOJI.sub(" ", t)
    t = re.sub(r"\.{3,}", "…", t)
    t = re.sub(r"\s+", " ", t).strip(" -–—|")
    t = re.sub(r"\s+([,.…])", r"\1", t)
    t = re.sub(r"(?<![.…])\.$", "", t)                      # point final isolé
    t = re.sub(r"(?i)\brelais populaire\b", "Relais Populaire", t)
    if t[:1].islower():
        t = t[0].upper() + t[1:]
    return t


CATS = {c["id"]: c["label"] for c in vdata["categories"]}
VIDEOS = {v["id"]: v for v in vdata["videos"]}
# Titres retravaillés à la main : ils l'emportent sur ceux de YouTube
TITLES = {v["id"]: v["title"] for v in vdata["videos"] + vdata["shorts"]}
TITLES.update(vdata.get("titles", {}))
LANGS = {s["id"]: s["lang"] for s in vdata["shorts"] if s.get("lang")}


def video_thumbs(vid, kind="max"):
    hq = f"https://i.ytimg.com/vi/{vid}/hqdefault.jpg"
    sd = f"https://i.ytimg.com/vi/{vid}/sddefault.jpg"
    mx = f"https://i.ytimg.com/vi_webp/{vid}/maxresdefault.webp"
    t = {"thumb_hq": hq, "thumb_sd": sd}
    if kind == "max":
        t.update(thumb_large=mx, srcset=f"{hq} 480w, {sd} 640w, {mx} 1280w")
    else:
        t.update(thumb_large=sd, srcset=f"{hq} 480w, {sd} 640w")
    return t


for v in vdata["videos"]:
    v["cat_label"] = CATS[v["cat"]]
    v.update(video_thumbs(v["id"], v.get("thumb", "max")))
    v["url"] = f"https://www.youtube.com/watch?v={v['id']}"


def short_item(s):
    """Short vertical : les miniatures YouTube classiques (4:3) contiennent l'image
    verticale au centre, recadrée en 9:16 par le CSS ; oar2 est la version verticale HD.
    Les largeurs du srcset sont celles de la partie utile de chaque image."""
    vid = s["id"]
    base = f"https://i.ytimg.com/vi/{vid}"
    item = {
        "id": vid,
        "title": TITLES.get(vid) or clean_title(s["title"]),
        "url": f"https://www.youtube.com/shorts/{vid}",
        "thumb_hq": f"{base}/hqdefault.jpg",
        "thumb_sd": f"{base}/sddefault.jpg",
        "srcset": f"{base}/hqdefault.jpg 202w, {base}/sddefault.jpg 270w, {base}/oar2.jpg 720w",
        "srcset_small": f"{base}/hqdefault.jpg 202w, {base}/sddefault.jpg 270w",
        "lang": LANGS.get(vid),
        "published": s.get("published"),
        "date_label": date_label(s["published"]) if s.get("published") else None,
    }
    return item


def long_item(v):
    vid = v["id"]
    cur = VIDEOS.get(vid, {})
    item = video_thumbs(vid, cur.get("thumb", "max"))
    item.update(
        id=vid,
        title=TITLES.get(vid) or clean_title(v["title"]),
        url=f"https://www.youtube.com/watch?v={vid}",
        cat_label=CATS.get(cur.get("cat"), "Vidéo"),
        blurb=cur.get("blurb"),
        published=v["published"],
        date_label=date_label(v["published"]),
    )
    return item


SHORTS = [short_item(s) for s in latest["shorts"]]
LONG = [long_item(v) for v in latest["long"][:3]]
REEL_SHORTS = list(SHORTS[12:])
REEL_SHORTS += [short_item(s) for s in vdata["shorts"] if s["id"] not in {x["id"] for x in SHORTS}]
REEL_SHORTS = REEL_SHORTS[:18]


def pick(ids):
    return [VIDEOS[i] for i in ids]


# Chiffres des réseaux (site.json → "audience")
def compact(n):
    """70300 → « 70,3 k », 4800000 → « 4,8 M », 9078 → « 9 078 »."""
    if n >= 1_000_000:
        s = f"{n / 1_000_000:.1f}".replace(".", ",").replace(",0", "")
        return f"{s} M"
    if n >= 10_000:
        s = f"{n / 1000:.1f}".replace(".", ",").replace(",0", "")
        return f"{s} k"
    return f"{n:,}".replace(",", " ")


AUD = site["audience"]
FOLLOWERS_TOTAL = sum(p["followers"] for p in AUD if p.get("followers"))
VIEWS_TOTAL = sum(p["views"] for p in AUD if p.get("views"))
STATS = {
    "followers_total": FOLLOWERS_TOTAL,
    "followers_floor": FOLLOWERS_TOTAL // 1000 * 1000,
    "views_total": VIEWS_TOTAL,
    "views_m": round(VIEWS_TOTAL / 1_000_000, 1),
    "followers_label": f"{FOLLOWERS_TOTAL // 1000 * 1000:,}".replace(",", " "),
    "views_label": f"{VIEWS_TOTAL / 1_000_000:.1f}".replace(".", ","),
    "followers": [(p["name"], compact(p["followers"]))
                  for p in sorted(AUD, key=lambda p: -p.get("followers", 0)) if p.get("followers")],
    "views": [(p["name"], compact(p["views"]))
              for p in sorted(AUD, key=lambda p: -p.get("views", 0)) if p.get("views")],
}


# ---------------------------------------------------------------- inline head script (+ hash CSP)
HEAD_SCRIPT = (
    "(function(d){d.classList.add('js');var m=null;try{m=localStorage.getItem('rpm-motion')}catch(e){}"
    "var r=window.matchMedia&&window.matchMedia('(prefers-reduced-motion: reduce)').matches;"
    "d.setAttribute('data-motion',m?m:(r?'off':'on'))})(document.documentElement);"
)
HEAD_SCRIPT_HASH = "sha256-" + base64.b64encode(hashlib.sha256(HEAD_SCRIPT.encode()).digest()).decode()


def file_hash(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()[:10]


def svg_inline(name: str, id_prefix: str) -> Markup:
    """Logo SVG en ligne, identifiants de dégradés rendus uniques."""
    svg = (BRAND / name).read_text(encoding="utf-8")
    svg = re.sub(r"\b(rpm[smh])-", lambda m: f"{id_prefix}-", svg)
    svg = svg.replace("<svg ", '<svg aria-hidden="true" focusable="false" ', 1)
    svg = svg.replace(' role="img" aria-label="Relais Populaire"', "")
    return Markup(svg)


NAV = [
    {"slug": "videos", "href": "videos.html", "label": "Vidéos"},
    {"slug": "le-media", "href": "le-media.html", "label": "Le média"},
    {"slug": "collaborer", "href": "collaborer.html", "label": "Collaborer"},
    {"slug": "contact", "href": "contact.html", "label": "Contact"},
]

PAGES = [
    {
        "tpl": "index.html", "out": "index.html", "slug": "accueil", "path": "/",
        "title": "Relais Populaire — le média qui raconte la Martinique",
        "description": "L’actu de la Martinique filmée sur le terrain : formats courts chaque jour, enquêtes et portraits. Relais Populaire donne la parole aux habitants de la Martinique, de la Caraïbe et de la diaspora.",
        "priority": "1.0",
    },
    {
        "tpl": "videos.html", "out": "videos.html", "slug": "videos", "path": "/videos.html",
        "title": "Vidéos et enquêtes — Relais Populaire",
        "description": "Les derniers Shorts qui font l’actu en Martinique, nos enquêtes et nos reportages : jeunesse, quartiers, mémoire, montagne Pelée, sport.",
        "priority": "0.9",
    },
    {
        "tpl": "le-media.html", "out": "le-media.html", "slug": "le-media", "path": "/le-media.html",
        "title": "Le média, notre démarche et notre charte — Relais Populaire",
        "description": "Relais Populaire Média, média indépendant martiniquais : qui nous sommes, notre démarche de terrain et notre charte éditoriale.",
        "priority": "0.8",
    },
    {
        "tpl": "collaborer.html", "out": "collaborer.html", "slug": "collaborer", "path": "/collaborer.html",
        "title": "Collaborer : reportage, film, captation — Relais Populaire",
        "description": "Reportages, portraits, captation d’événements, formats réseaux, images aériennes : Relais Populaire met son regard et ses moyens au service de vos projets.",
        "priority": "0.8",
    },
    {
        "tpl": "contact.html", "out": "contact.html", "slug": "contact", "path": "/contact.html",
        "title": "Contact — Relais Populaire",
        "description": "Proposer un sujet, témoigner, lancer un projet ou exercer un droit de réponse : écrivez à la rédaction de Relais Populaire.",
        "priority": "0.7",
    },
    {
        "tpl": "mentions-legales.html", "out": "mentions-legales.html", "slug": "mentions", "path": "/mentions-legales.html",
        "title": "Mentions légales — Relais Populaire",
        "description": "Mentions légales de relaispopulaire.fr : éditeur, directeur de la publication, hébergeur, propriété intellectuelle et droit de réponse.",
        "priority": "0.3",
    },
    {
        "tpl": "confidentialite.html", "out": "confidentialite.html", "slug": "confidentialite", "path": "/confidentialite.html",
        "title": "Confidentialité — Relais Populaire",
        "description": "Politique de confidentialité de relaispopulaire.fr : aucun cookie, aucun traceur, vidéos YouTube chargées uniquement au clic.",
        "priority": "0.3",
    },
    {
        "tpl": "404.html", "out": "404.html", "slug": "404", "path": "/404.html",
        "title": "Page introuvable — Relais Populaire",
        "description": "Cette page n’existe pas ou a été déplacée.",
        "robots": "noindex, follow", "root": "/", "sitemap": False,
    },
]


def jsonld(page):
    url = site["url"]
    graph = [
        {
            "@type": "NewsMediaOrganization",
            "@id": f"{url}/#organisation",
            "name": site["org"],
            "alternateName": [site["name"], site["short"]],
            "url": f"{url}/",
            "logo": {"@type": "ImageObject", "url": f"{url}/assets/img/logo-512.png", "width": 512, "height": 512},
            "image": f"{url}/assets/img/og-image.jpg",
            "slogan": site["slogan"],
            "description": site["description"],
            "email": site["email"],
            "areaServed": ["Martinique", "Caraïbe", "France"],
            "knowsLanguage": ["fr", "gcf"],
            "sameAs": [site["youtube"]] + [s["url"] for s in site.get("socials", [])],
            "publishingPrinciples": f"{url}/le-media.html#charte",
            "correctionsPolicy": f"{url}/le-media.html#charte",
        },
        {
            "@type": "WebSite",
            "@id": f"{url}/#site",
            "url": f"{url}/",
            "name": site["name"],
            "inLanguage": "fr-FR",
            "publisher": {"@id": f"{url}/#organisation"},
        },
        {
            "@type": "WebPage",
            "@id": f"{url}{page['path']}#page",
            "url": f"{url}{page['path']}",
            "name": page["title"],
            "description": page["description"],
            "inLanguage": "fr-FR",
            "isPartOf": {"@id": f"{url}/#site"},
            "about": {"@id": f"{url}/#organisation"},
        },
    ]
    data = {"@context": "https://schema.org", "@graph": graph}
    return Markup(json.dumps(data, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/"))


def wa_link(text, url):
    from urllib.parse import quote
    return "https://wa.me/?text=" + quote(f"{text}\n{url}")


def french_spacing(html: str) -> str:
    """Espaces fines insécables avant : ; ! ? » et après « (hors scripts)."""
    parts = re.split(r"(<script\b.*?</script>)", html, flags=re.S)
    for i, part in enumerate(parts):
        if part.startswith("<script"):
            continue
        part = re.sub(r"(?<=\S) ([:;!?»])", "\u202f\\1", part)
        part = re.sub(r"« ", "«\u202f", part)
        parts[i] = part
    return "".join(parts)


def build():
    if DIST.exists():
        shutil.rmtree(DIST)
    (DIST / "assets").mkdir(parents=True)
    # fichiers statiques
    for sub in ("css", "js", "fonts", "img"):
        src = SRC / "static" / sub
        if src.exists():
            shutil.copytree(src, DIST / "assets" / sub)

    # minification (sources lisibles dans src/, fichiers compacts dans dist/)
    bin_dir = ROOT / "node_modules" / ".bin"
    if not (bin_dir / "esbuild").exists():
        bin_dir = ROOT / "work" / "node_modules" / ".bin"
    css = DIST / "assets/css/style.css"
    js = DIST / "assets/js/main.js"
    subprocess.run([str(bin_dir / "lightningcss"), "--minify", "--targets", ">= 0.25%, not dead",
                    str(css), "-o", str(css)], check=True)
    subprocess.run([str(bin_dir / "esbuild"), str(js), "--minify", "--target=es2018",
                    f"--outfile={js}", "--allow-overwrite", "--log-level=warning"], check=True)

    v_css = file_hash(DIST / "assets/css/style.css")
    v_js = file_hash(DIST / "assets/js/main.js")

    env = Environment(
        loader=FileSystemLoader(SRC / "templates"),
        autoescape=select_autoescape(["html"]),
        trim_blocks=True,
        lstrip_blocks=True,
    )
    env.globals.update(
        site=site,
        nav=NAV,
        cats=vdata["categories"],
        videos=vdata["videos"],
        shorts=SHORTS,
        ring=SHORTS[:12],
        reel_shorts=REEL_SHORTS,
        long_latest=LONG,
        stats=STATS,
        collab_refs=pick(vdata["collab_refs"]),
        V=VIDEOS,
        v_css=v_css,
        v_js=v_js,
        head_script=Markup(HEAD_SCRIPT),
        wa_link=wa_link,
        logo_horiz_markup=svg_inline("horiz_current.svg", "lh"),
        logo_stacked_markup=svg_inline("stacked_current.svg", "ls"),
    )

    for page in PAGES:
        tpl = env.get_template(page["tpl"])
        ctx = dict(page=page, root=page.get("root", ""), jsonld=jsonld(page))
        html = tpl.render(**ctx)
        html = re.sub(r"\n\s*\n+", "\n", html)
        html = french_spacing(html)
        (DIST / page["out"]).write_text(html, encoding="utf-8")

    # sitemap
    urls = []
    fresh = max(site["updated"], latest.get("updated", "")[:10])
    for p in PAGES:
        if p.get("sitemap", True):
            lastmod = fresh if p["slug"] in ("accueil", "videos") else site["updated"]
            urls.append(
                f"  <url><loc>{site['url']}{p['path']}</loc><lastmod>{lastmod}</lastmod>"
                f"<priority>{p['priority']}</priority></url>"
            )
    (DIST / "sitemap.xml").write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' + "\n".join(urls) + "\n</urlset>\n",
        encoding="utf-8",
    )
    (DIST / "robots.txt").write_text(f"User-agent: *\nAllow: /\n\nSitemap: {site['url']}/sitemap.xml\n", encoding="utf-8")

    manifest = {
        "name": "Relais Populaire",
        "short_name": "Relais Populaire",
        "description": "Le média indépendant qui raconte la Martinique.",
        "lang": "fr",
        "start_url": "/",
        "scope": "/",
        "display": "standalone",
        "background_color": "#050605",
        "theme_color": "#050605",
        "icons": [
            {"src": "/assets/img/icon-192.png", "sizes": "192x192", "type": "image/png"},
            {"src": "/assets/img/icon-512.png", "sizes": "512x512", "type": "image/png"},
            {"src": "/assets/img/icon-maskable-512.png", "sizes": "512x512", "type": "image/png", "purpose": "maskable"},
        ],
    }
    (DIST / "site.webmanifest").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    if (DIST / "assets/img/favicon.ico").exists():
        shutil.move(str(DIST / "assets/img/favicon.ico"), DIST / "favicon.ico")

    htaccess = (SRC / "htaccess.tpl").read_text(encoding="utf-8").replace("{{HEAD_SCRIPT_HASH}}", HEAD_SCRIPT_HASH)
    (DIST / ".htaccess").write_text(htaccess, encoding="utf-8")

    # Équivalents pour un hébergement Netlify (ignorés par Apache)
    csp = re.search(r'Content-Security-Policy "([^"]+)"', htaccess).group(1)
    (DIST / "_headers").write_text(
        "/*\n"
        "  X-Content-Type-Options: nosniff\n"
        "  Referrer-Policy: strict-origin-when-cross-origin\n"
        "  X-Frame-Options: SAMEORIGIN\n"
        "  Permissions-Policy: camera=(), microphone=(), geolocation=(), payment=(), usb=()\n"
        "  Cross-Origin-Opener-Policy: same-origin\n"
        f"  Content-Security-Policy: {csp}\n"
        "  Strict-Transport-Security: max-age=31536000\n"
        "/assets/css/*\n  Cache-Control: public, max-age=31536000, immutable\n"
        "/assets/js/*\n  Cache-Control: public, max-age=31536000, immutable\n"
        "/assets/fonts/*\n  Cache-Control: public, max-age=31536000, immutable\n"
        "/assets/img/*\n  Cache-Control: public, max-age=2592000\n",
        encoding="utf-8",
    )
    (DIST / "_redirects").write_text(
        "https://www.relaispopulaire.fr/* https://relaispopulaire.fr/:splat 301!\n"
        "http://www.relaispopulaire.fr/* https://relaispopulaire.fr/:splat 301!\n",
        encoding="utf-8",
    )
    print("OK — pages:", ", ".join(p["out"] for p in PAGES))
    print("CSP hash:", HEAD_SCRIPT_HASH)


if __name__ == "__main__":
    build()
