#!/usr/bin/env python3
"""Build news/<cc>.json for the VUE news ticker (headline + source) from Google News RSS.
Runs on GitHub Actions every 30 minutes. The TV only reads these small JSON files.
Each item: t = headline, s = source, p = publish time (unix seconds), b = 1 for breaking news
(headline marked "عاجل"); the TV shows breaking items in a red "عاجل" box while they are fresh."""
import json, re, sys, time, urllib.parse, urllib.request, xml.etree.ElementTree as ET, datetime, email.utils

COUNTRIES = {  # code: (Arabic name, Google News edition)
    "sa": ("السعودية", "SA"), "kw": ("الكويت", "KW"), "ae": ("الإمارات", "AE"), "qa": ("قطر", "QA"),
    "bh": ("البحرين", "BH"), "om": ("عُمان", "OM"), "eg": ("مصر", "EG"), "jo": ("الأردن", "JO"),
}
BREAKING = re.compile(r"^\s*[\(\[«]?\s*عاجل\s*[\)\]»]?\s*[:|\-–—.،]*\s*")
UA = {"User-Agent": "Mozilla/5.0 (VUE news ticker; https://vue-tv.github.io)"}
SKIP = re.compile(r"مباشر|فيديو:|صور:|إعلان|برعاية", re.I)

# Preferred official / major sources per country (fetched first, then the general edition).
PREFERRED = {"sa": "site:spa.gov.sa OR site:alarabiya.net OR site:sabq.org"}

def fetch(edition, query=None):
    if query:
        url = "https://news.google.com/rss/search?" + urllib.parse.urlencode({"q": query + " when:1d", "hl": "ar", "gl": edition, "ceid": edition + ":ar"})
    else:
        url = f"https://news.google.com/rss?hl=ar&gl={edition}&ceid={edition}:ar"
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=30) as r:
        root = ET.fromstring(r.read())
    out, seen = [], set()
    for it in root.iter("item"):
        title = (it.findtext("title") or "").strip()
        src_el = it.find("source"); source = (src_el.text if src_el is not None else "") or ""
        if source and title.endswith(" - " + source): title = title[: -len(source) - 3]
        title = re.sub(r"\s+", " ", title).strip()
        if not title or len(title) < 12 or SKIP.search(title): continue
        brk = bool(BREAKING.match(title)) or "| عاجل" in title or "عاجل |" in title
        if brk: title = BREAKING.sub("", title).replace("| عاجل", "").replace("عاجل |", "").strip(" |-–—:")
        if len(title) < 12: continue
        key = title[:40]
        if key in seen: continue
        item = {"t": title[:140], "s": source.strip()[:40]}
        try: item["p"] = int(email.utils.parsedate_to_datetime(it.findtext("pubDate")).timestamp())
        except Exception: pass
        if brk: item["b"] = 1
        seen.add(key); out.append(item)
        if len(out) >= 25: break
    return out

def main():
    index = []
    for code, (name, edition) in COUNTRIES.items():
        items = []
        for q in ["عاجل " + name] + ([PREFERRED[code]] if code in PREFERRED else []) + [None]:
            try:
                got = fetch(edition, q)
            except Exception as e:
                print(code, "failed:", e, file=sys.stderr); got = []
            have = {x["t"][:40] for x in items}
            items += [x for x in got if x["t"][:40] not in have]
        now = time.time()
        # breaking only while fresh (3 h); keep at most 5 of them, newest first, ahead of the rest
        brk = sorted([x for x in items if x.get("b") and now - x.get("p", 0) < 3 * 3600], key=lambda x: -x.get("p", 0))[:5]
        for x in items:
            if x.get("b") and x not in brk: x.pop("b", None)
        items = brk + [x for x in items if x not in brk]
        items = items[:30]
        if items:
            with open(f"news/{code}.json", "w", encoding="utf-8") as f:
                json.dump({"country": code, "name": name, "updated": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="minutes"), "items": items}, f, ensure_ascii=False, separators=(",", ":"))
        index.append({"code": code, "name": name})
        print(code, len(items), file=sys.stderr); time.sleep(2)
    with open("news/countries.json", "w", encoding="utf-8") as f:
        json.dump(index, f, ensure_ascii=False)

if __name__ == "__main__":
    main()
