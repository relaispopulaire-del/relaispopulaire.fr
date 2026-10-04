#!/usr/bin/env python3
"""Récupère les derniers Shorts et vidéos longues de la chaîne YouTube.

Lit les flux publics de la chaîne (aucune clé d'API nécessaire) :
- Shorts uniquement : playlist UUSH…
- Vidéos longues uniquement : playlist UULF…

Met à jour src/data/latest.json seulement si quelque chose a changé.
En cas de souci réseau, les données précédentes sont conservées : le site
se construit toujours.
"""
import json
import os
import sys
import time
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SITE = json.loads((ROOT / "src" / "data" / "site.json").read_text(encoding="utf-8"))
OUT = ROOT / "src" / "data" / "latest.json"

FEED = "https://www.youtube.com/feeds/videos.xml?playlist_id={}"
NS = {
    "atom": "http://www.w3.org/2005/Atom",
    "yt": "http://www.youtube.com/xml/schemas/2015",
}
KEEP = {"shorts": 30, "long": 15}


def fetch(playlist_id: str):
    """Renvoie la liste des vidéos du flux, ou None si le flux est indisponible."""
    url = FEED.format(playlist_id)
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (relaispopulaire.fr)"})
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=20) as resp:
                root = ET.fromstring(resp.read())
            items = []
            for entry in root.findall("atom:entry", NS):
                vid = entry.findtext("yt:videoId", default="", namespaces=NS).strip()
                title = entry.findtext("atom:title", default="", namespaces=NS).strip()
                published = entry.findtext("atom:published", default="", namespaces=NS).strip()
                if vid and title and published:
                    items.append({"id": vid, "title": title, "published": published})
            return items
        except Exception as exc:  # réseau, XML invalide…
            print(f"::warning::Flux {playlist_id} indisponible (essai {attempt + 1}) : {exc}")
            time.sleep(4 * (attempt + 1))
    return None


def merge(fresh, previous, keep):
    """Le flux ne donne que les 15 dernières vidéos : on garde aussi les plus
    anciennes déjà connues, sans réintroduire celles retirées de la chaîne."""
    if not fresh:
        return previous
    ids = {v["id"] for v in fresh}
    oldest = min(v["published"] for v in fresh)
    older = [v for v in previous if v["id"] not in ids and v["published"] < oldest]
    items = sorted(fresh + older, key=lambda v: v["published"], reverse=True)
    return items[:keep]


def main():
    previous = json.loads(OUT.read_text(encoding="utf-8")) if OUT.exists() else {}
    suffix = SITE["youtube_channel_id"][2:]
    data = {
        "shorts": merge(fetch("UUSH" + suffix), previous.get("shorts", []), KEEP["shorts"]),
        "long": merge(fetch("UULF" + suffix), previous.get("long", []), KEEP["long"]),
    }
    changed = any(data[k] != previous.get(k) for k in data)
    if changed:
        data = {"updated": datetime.now(timezone.utc).replace(microsecond=0).isoformat(), **data}
        OUT.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"Nouvelles données : {len(data['shorts'])} Shorts, {len(data['long'])} vidéos longues.")
    else:
        print("Aucune nouvelle vidéo.")
    if os.environ.get("GITHUB_OUTPUT"):
        with open(os.environ["GITHUB_OUTPUT"], "a", encoding="utf-8") as fh:
            fh.write(f"changed={'true' if changed else 'false'}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
