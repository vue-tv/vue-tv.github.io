#!/usr/bin/env python3
"""Build kids/videos.json for VUE Kids from a fixed allow-list of kids channels.

Runs daily on GitHub Actions. Uses only public YouTube feeds (no API key):
latest uploads + popular uploads per channel, drops Shorts, live/podcast items and
any video whose owner disabled embedding, then picks up to MAX per category with a
date-based shuffle so the list changes every day."""
import concurrent.futures, datetime, json, random, re, sys, urllib.request, xml.etree.ElementTree as ET

MAX = 40
CATEGORIES = [
    {"id": "spacetoon", "name": "سبيستون", "art": "rocket", "color": "#ff7a3d",
     "channels": ["UCuQKih3Ac3NABADQKQdeV6A", "UCwCLmo14vG4luqGsYcYxKrQ"]},
    {"id": "toyor", "name": "طيور الجنة", "art": "chick", "color": "#7c5cff",
     "channels": ["UCozAuGJZ5MPoijz8IE_1Gtw", "UC79iC-tMACVyRjfzu_DYrVg"]},
    {"id": "songs", "name": "أناشيد وأغاني", "art": "bunny", "color": "#ff5c9a",
     "channels": ["UCGAWwx_VrdiBawxxaQMBPug", "UC2mcPN2YDX31oaLnfZScx_g", "UCpcZREaNdYfSzpbQmo3IiZA",
                  "UCHnhz7XCP6Zx6l22npF-yWA", "UCHIa4JmqvnCc7rQ5NADhqDA", "UCoNd526tmPb5Yw9CzkcdnTw"]},
    {"id": "learn", "name": "تعلّم وقصص", "art": "bear", "color": "#22b8a8",
     "channels": ["UCvr9YT7AwMTxKDqou3e_OUQ", "UCoCDD5hipO8RhDkOkvwhe1Q", "UCtlcIZVBdFPSAtCoNZsTusg",
                  "UC4ctOayFRE8EIazA4-FUMLw", "UCBqfiWktGq5Gy-B5fIaUdzw", "UChC2qD1bMrhAXzwvf4A6k1Q"]},
]
SKIP = re.compile(r"#shorts|shorts|بث مباشر|مباشر|live|بودكاست|podcast|trailer|إعلان|كواليس"
                  # not for young kids — extend on the parent's request
                  r"|gundam|غاندام|جاندام|attack on titan|horror|رعب", re.I)
NS = {"a": "http://www.w3.org/2005/Atom", "yt": "http://www.youtube.com/xml/schemas/2015"}
UA = {"User-Agent": "Mozilla/5.0 (VUE kids feed)"}

def get(url, timeout=20):
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=timeout) as r:
        return r.status, r.read()

def feed(kind, value):
    try:
        status, body = get(f"https://www.youtube.com/feeds/videos.xml?{kind}={value}")
        root = ET.fromstring(body)
    except Exception as e:
        print("feed failed", kind, value, e, file=sys.stderr); return []
    out = []
    for entry in root.findall("a:entry", NS):
        vid = entry.findtext("yt:videoId", namespaces=NS)
        title = (entry.findtext("a:title", namespaces=NS) or "").strip()
        link = entry.find("a:link", NS)
        href = link.get("href", "") if link is not None else ""
        if not vid or "/shorts/" in href or SKIP.search(title):
            continue
        out.append({"id": vid, "t": title[:90]})
    return out

def embeddable(vid):
    """True if the video plays when embedded on the VUE site.
    1) oEmbed must succeed (owner allows embedding at all);
    2) the embed page, requested as from vue-tv.github.io, must not say UNPLAYABLE
       (some channels block playback outside YouTube). If YouTube answers with
       anything else (e.g. a bot check on the build machine) we trust oEmbed."""
    try:
        status, _ = get(f"https://www.youtube.com/oembed?url=https://www.youtube.com/watch?v={vid}&format=json", 15)
        if status != 200:
            return False
    except Exception:
        return False
    try:
        req = urllib.request.Request(f"https://www.youtube.com/embed/{vid}", headers={**UA, "Referer": "https://vue-tv.github.io/"})
        with urllib.request.urlopen(req, timeout=15) as r:
            page = r.read().decode("utf-8", "ignore")
        m = re.search(r'previewPlayabilityStatus\\?":\{\\?"status\\?":\\?"([A-Z_]+)', page)
        return not (m and m.group(1) == "UNPLAYABLE")
    except Exception:
        return True

def main(path):
    today = datetime.date.today().isoformat()
    rng = random.Random(today)
    result = {"product": "VUE", "schemaVersion": 1, "updated": today, "categories": []}
    for cat in CATEGORIES:
        pool, seen = [], set()
        for ch in cat["channels"]:
            items = feed("channel_id", ch) + feed("playlist_id", "UULP" + ch[2:])
            for it in items:
                if it["id"] not in seen:
                    seen.add(it["id"]); pool.append(it)
        rng.shuffle(pool)
        with concurrent.futures.ThreadPoolExecutor(8) as ex:
            ok = list(ex.map(embeddable, [p["id"] for p in pool[:MAX * 2]]))
        videos = [p for p, good in zip(pool[:MAX * 2], ok) if good][:MAX]
        print(f"{cat['name']}: {len(pool)} found, {len(videos)} kept", file=sys.stderr)
        result["categories"].append({k: cat[k] for k in ("id", "name", "art", "color")} | {"videos": videos})
    if sum(len(c["videos"]) for c in result["categories"]) < 20:
        sys.exit("too few videos — keeping the previous file")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, separators=(",", ":"))

if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "kids/videos.json")
