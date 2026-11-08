#!/usr/bin/env python3
"""Build VUE's static, data-only JSONP content feed and copy approved wallpapers."""
from pathlib import Path
import json, re, shutil

ROOT = Path(__file__).resolve().parent
PROJECT = ROOT.parent
SOURCE = PROJECT / "work/android-tv/app/src/main/assets/www/assets/backgrounds"
DIST = ROOT / "dist"
DATA = ROOT / "content-feed.json"
ALLOWED = {"riyadh-kingdom-centre.jpg", "jeddah-albalad.jpg", "alula-elephant-rock.jpg", "abha-asir.jpg", "diriyah-turaif.jpg"}
feed = json.loads(DATA.read_text(encoding="utf-8"))
if feed.get("product") != "VUE" or feed.get("schemaVersion") != 1:
    raise SystemExit("Unsupported VUE content feed schema")
if not re.fullmatch(r"[A-Za-z0-9._-]{1,64}", str(feed.get("revision", ""))):
    raise SystemExit("Invalid content revision")
files = feed.get("backgrounds")
if not isinstance(files, list) or not 1 <= len(files) <= 8 or len(set(files)) != len(files):
    raise SystemExit("Choose 1 to 8 unique wallpapers")
for name in files:
    if name not in ALLOWED:
        raise SystemExit(f"Wallpaper is not on the approved list: {name}")
    if not (SOURCE / name).is_file():
        raise SystemExit(f"Missing wallpaper: {SOURCE / name}")
manifest = {
    "product": "VUE", "schemaVersion": 1, "revision": feed["revision"],
    "updatedAt": str(feed.get("updatedAt", ""))[:40],
    "backgrounds": [f"/assets/content/backgrounds/{name}" for name in files]
}
for target in (ROOT, DIST):
    image_dir = target / "assets/content/backgrounds"
    image_dir.mkdir(parents=True, exist_ok=True)
    for name in files:
        shutil.copy2(SOURCE / name, image_dir / name)
    # Retain only files in the active revision; no old campaign imagery is published by accident.
    for old in image_dir.iterdir():
        if old.is_file() and old.name not in files:
            old.unlink()
    payload = json.dumps(manifest, ensure_ascii=False, separators=(",", ":"))
    (target / "content.js").write_text(
        "(function(){var cb=new URLSearchParams(location.search).get('callback');"
        "if(cb==='__VUE_CONTENT_RECEIVE__'&&typeof window[cb]==='function')"
        f"window[cb]({payload});"
        "})();\n", encoding="utf-8"
    )
print(f"Built revision {manifest['revision']} with {len(files)} wallpapers for website and dist")
