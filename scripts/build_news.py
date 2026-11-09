#!/usr/bin/env python3
"""Build news/<cc>.json for the VUE news box from Google News RSS (every 30 minutes on GitHub).
The TV only reads these small JSON files.

Each item: t = headline, s = source name (channel / paper / agency), p = publish time (unix s),
b = 1 for breaking news. An item is breaking only when a real outlet marks it "عاجل", it is about
the chosen country, it is fresh (< 3 h) and it is serious (security / disaster / major official news).

Sources are mixed: official agencies and major channels first, then the general edition, and no
single outlet may fill the list (at most MAX_PER_SOURCE items each, interleaved)."""
import json, re, sys, time, urllib.parse, urllib.request, xml.etree.ElementTree as ET, datetime, email.utils

COUNTRIES = {  # code: (Arabic name, Google News edition)
    "sa": ("السعودية", "SA"), "kw": ("الكويت", "KW"), "ae": ("الإمارات", "AE"), "qa": ("قطر", "QA"),
    "bh": ("البحرين", "BH"), "om": ("عُمان", "OM"), "eg": ("مصر", "EG"), "jo": ("الأردن", "JO"),
}
# Official agencies and major outlets per country, asked for first.
PREFERRED = {
    "sa": ["spa.gov.sa", "alarabiya.net", "alekhbariya.net", "okaz.com.sa", "alriyadh.com", "aawsat.com", "sabq.org", "almadina.com", "alwatan.com.sa"],
    "kw": ["kuna.net.kw", "alqabas.com", "alraimedia.com", "aljarida.com", "alanba.com.kw"],
    "ae": ["wam.ae", "alkhaleej.ae", "albayan.ae", "emaratalyoum.com", "skynewsarabia.com"],
    "qa": ["qna.org.qa", "al-sharq.com", "raya.com", "alwatan.com", "aljazeera.net"],
    "bh": ["bna.bh", "alayam.com", "akhbar-alkhaleej.com", "albiladpress.com"],
    "om": ["omannews.gov.om", "omandaily.om", "alwatan.com", "atheer.om"],
    "eg": ["sis.gov.eg", "ahram.org.eg", "youm7.com", "masrawy.com", "almasryalyoum.com", "alwatannews.com"],
    "jo": ["petra.gov.jo", "alghad.com", "alrai.com", "addustour.com", "royanews.tv"],
}
# Words that place a headline in the country (for breaking news).
PLACES = {
    "sa": "السعودية|المملكة|سعودي|الرياض|جدة|مكة|المدينة المنورة|الدمام|الشرقية|القصيم|أبها|عسير|جازان|نجران|تبوك|حائل|الطائف|الخبر|الأحساء|الجوف|ينبع|العلا|الباحة",
    "kw": "الكويت|كويتي", "ae": "الإمارات|إماراتي|أبوظبي|دبي|الشارقة|عجمان|رأس الخيمة|الفجيرة",
    "qa": "قطر|قطري|الدوحة", "bh": "البحرين|بحريني|المنامة", "om": "عمان|عُمان|عماني|مسقط|صلالة",
    "eg": "مصر|مصري|القاهرة|الإسكندرية|الجيزة", "jo": "الأردن|أردني|عمّان|عمان|الزرقاء|إربد|العقبة",
}
SERIOUS = re.compile(r"انفجار|هجوم|استهداف|اعتراض|صاروخ|مسيّر|مسير|إطلاق نار|حريق|زلزال|سيول|أمطار غزيرة|إنذار|تحذير|الدفاع المدني|إخلاء|وفاة|مقتل|قتلى|إصابات|حادث|طوارئ|إغلاق|تعليق الدراسة|الديوان الملكي|أمر ملكي|مرسوم|قرار عاجل|وزارة الداخلية|الأمن العام|عاصفة|غبار")
BLOCKED_SOURCES = re.compile(r"^(صحيفة\s+)?عاجل$|ajel", re.I)   # an outlet literally named "عاجل" (not breaking news)
BREAKING = re.compile(r"^\s*[\(\[«]?\s*عاجل\s*[\)\]»]?\s*[:|\-–—.،/]*\s*")
UA = {"User-Agent": "Mozilla/5.0 (VUE news ticker; https://vue-tv.github.io)"}
SKIP = re.compile(r"مباشر|فيديو:|صور:|إعلان|برعاية", re.I)
MAX_PER_SOURCE = 3
NAMES = {"www.wam.ae": "وام", "wam.ae": "وام", "BBC": "بي بي سي عربي", "CNN Arabic": "سي إن إن بالعربية", "France 24": "فرانس 24",
         "Masrawy": "مصراوي", "Sharjah24": "الشارقة 24", "Investing.com": "إنفستنغ", "RT Arabic": "روسيا اليوم", "Independent Arabia": "إندبندنت عربية", "Qatar news agency": "قنا", "FilGoal": "في الجول"}

def clean_source(s):
    s = re.split(r"\s+[:|\-–—]\s+", s.strip())[0].strip()
    s = NAMES.get(s, s)
    if s.lower().startswith("www."): s = s[4:]
    return s[:32]

def fetch(edition, query=None):
    if query:
        url = "https://news.google.com/rss/search?" + urllib.parse.urlencode({"q": query + " when:1d", "hl": "ar", "gl": edition, "ceid": edition + ":ar"})
    else:
        url = f"https://news.google.com/rss?hl=ar&gl={edition}&ceid={edition}:ar"
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=30) as r:
        root = ET.fromstring(r.read())
    out = []
    for it in root.iter("item"):
        title = (it.findtext("title") or "").strip()
        src_el = it.find("source"); source = ((src_el.text if src_el is not None else "") or "").strip()
        src_url = (src_el.get("url") if src_el is not None else "") or ""
        if BLOCKED_SOURCES.search(source) or BLOCKED_SOURCES.search(src_url): continue
        if source and title.endswith(" - " + source): title = title[: -len(source) - 3]
        title = re.sub(r"\s+", " ", title).strip()
        if not title or SKIP.search(title): continue
        flagged = bool(BREAKING.match(title)) or "| عاجل" in title or "عاجل |" in title
        if flagged: title = BREAKING.sub("", title).replace("| عاجل", "").replace("عاجل |", "").strip(" |-–—:/")
        if len(title) < 12: continue
        item = {"t": title[:140], "s": clean_source(source)}
        try: item["p"] = int(email.utils.parsedate_to_datetime(it.findtext("pubDate")).timestamp())
        except Exception: pass
        if flagged: item["_flag"] = 1
        out.append(item)
        if len(out) >= 40: break
    return out

def mix(items, limit=30):
    """Round-robin over sources so the box shows many outlets; at most MAX_PER_SOURCE each."""
    groups, order = {}, []
    for x in items:
        k = x["s"] or "?"
        if k not in groups: groups[k] = []; order.append(k)
        if len(groups[k]) < MAX_PER_SOURCE: groups[k].append(x)
    out, i = [], 0
    while len(out) < limit and any(groups.values()):
        k = order[i % len(order)]; i += 1
        if groups[k]: out.append(groups[k].pop(0))
    return out

def main():
    index = []
    now = time.time()
    for code, (name, edition) in COUNTRIES.items():
        items, seen = [], set()
        sites = PREFERRED.get(code, [])
        queries = [" OR ".join("site:" + s for s in sites[i:i + 4]) for i in range(0, len(sites), 4)] + [None]
        for q in queries:
            try:
                got = fetch(edition, q)
            except Exception as e:
                print(code, "failed:", e, file=sys.stderr); got = []
            for x in got:
                key = x["t"][:40]
                if key not in seen: seen.add(key); items.append(x)
            time.sleep(1)
        place = re.compile(PLACES[code])
        brk = []
        for x in items:
            if x.pop("_flag", None) and now - x.get("p", 0) < 3 * 3600 and place.search(x["t"]) and SERIOUS.search(x["t"]):
                brk.append(x)
        brk = sorted(brk, key=lambda x: -x.get("p", 0))[:3]
        for x in brk: x["b"] = 1
        rest = mix([x for x in items if x not in brk], 30 - len(brk))
        items = brk + rest
        if items:
            with open(f"news/{code}.json", "w", encoding="utf-8") as f:
                json.dump({"country": code, "name": name, "updated": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="minutes"), "items": items}, f, ensure_ascii=False, separators=(",", ":"))
        index.append({"code": code, "name": name})
        print(code, len(items), "sources:", len({x["s"] for x in items}), "breaking:", len(brk), file=sys.stderr)
    with open("news/countries.json", "w", encoding="utf-8") as f:
        json.dump(index, f, ensure_ascii=False)

if __name__ == "__main__":
    main()
