#!/usr/bin/env python3
"""Build news/league-<id>.json for the VUE Sport page from Arabic Google News (every 30 minutes).

Why: the English ESPN feed covers the Saudi league almost only through Ronaldo / Al Nassr. Here we
ask Arabic outlets about every club of the league (plus the national team for the Saudi league),
tag each headline with the club it is about, and mix clubs round-robin so no club or star can fill
the list (at most MAX_PER_TEAM headlines each).

Item: t = headline, s = source, p = publish time (unix s), k = club (Arabic), l = club logo URL."""
import json, re, sys, time, urllib.parse, urllib.request, xml.etree.ElementTree as ET, datetime, email.utils

LOGO = "https://a.espncdn.com/i/teamlogos/soccer/500/{}.png"
# league id: (query words for the league, [(club Arabic name / alternatives, ESPN id), ...])
LEAGUES = {
    "ksa.1": ("دوري روشن", [("الهلال", 929), ("النصر", 817), ("العميد|الاتحاد(?! (?:الفرنسي|الآسيوي|الدولي|الأوروبي|الوطني|السعودي|الإنجليزي|الإسباني|المصري|العربي|الخليجي|الأفريقي|الأردني|اللبناني|العراقي))", 2276), ("الأهلي السعودي|الأهلي|الاهلي|الراقي", 8346), ("الشباب السعودي|نادي الشباب|فريق الشباب|مدرب الشباب|لاعب الشباب|الليث|الشباب (?:يفوز|يتعادل|يخسر|يواجه|يتغلب|يضم|يعلن)", 793), ("الاتفاق", 8363),
               ("التعاون", 18459), ("الفتح", 13033), ("الفيحاء", 21827), ("الخليج", 21829), ("القادسية", 22022), ("نادي الرياض|فريق الرياض|مدرب الرياض|لاعب الرياض|الرياض (?:يفوز|يتعادل|يخسر|يواجه|يتغلب|يضم|يعلن)", 21965),
               ("الحزم", 21964), ("الخلود", 22028), ("نيوم", 130899), ("الدرعية", 131746), ("أبها|ابها", 21833), ("الفيصلي", 21446),
               ("المنتخب السعودي|الأخضر السعودي", 0)]),
    "esp.1": ("الدوري الإسباني", [("ريال مدريد", 86), ("برشلونة", 83), ("أتلتيكو مدريد|أتليتيكو مدريد", 1068), ("إشبيلية|اشبيلية", 243),
               ("ريال بيتيس", 244), ("ريال سوسيداد", 89), ("فياريال", 102), ("فالنسيا", 94), ("أتلتيك بلباو|أتلتيك بيلباو", 93),
               ("جيرونا|سيلتا فيغو", 85), ("أوساسونا", 97), ("رايو فاييكانو", 101), ("خيتافي", 2922), ("إسبانيول", 88)]),
    "eng.1": ("الدوري الإنجليزي", [("ليفربول", 364), ("مانشستر سيتي", 382), ("مانشستر يونايتد", 360), ("أرسنال|آرسنال", 359), ("تشيلسي", 363),
               ("توتنهام", 367), ("نيوكاسل", 361), ("أستون فيلا", 362), ("وست هام|برايتون", 331), ("إيفرتون", 368), ("نوتنغهام فورست", 393),
               ("كريستال بالاس", 384), ("فولهام", 370), ("برينتفورد", 337), ("بورنموث", 349), ("ليدز", 357), ("سندرلاند", 366)]),
    "ita.1": ("الدوري الإيطالي", [("يوفنتوس", 111), ("إنتر ميلان|الإنتر", 110), ("ميلان", 103), ("نابولي", 114), ("روما", 104), ("لاتسيو", 112),
               ("أتالانتا", 105), ("فيورنتينا", 109), ("بولونيا", 107), ("تورينو", 239), ("كومو", 2572), ("جنوى", 3263), ("أودينيزي", 118)]),
    "ger.1": ("الدوري الألماني", [("بايرن ميونخ", 132), ("بوروسيا دورتموند|دورتموند", 124), ("باير ليفركوزن|ليفركوزن", 131), ("لايبزيغ", 11420),
               ("آينتراخت فرانكفورت|فرانكفورت", 125), ("شتوتغارت", 134), ("فولفسبورغ|فرايبورغ", 126), ("مونشنغلادباخ", 268), ("هوفنهايم", 7911),
               ("فيردر بريمن", 137), ("أونيون برلين", 598), ("هامبورغ", 127), ("شالكه", 133), ("ماينز", 2950)]),
    "fra.1": ("الدوري الفرنسي", [("باريس سان جيرمان", 160), ("مارسيليا", 176), ("موناكو", 174), ("ليون", 167), ("ليل", 166), ("نيس", 2502),
               ("لانس", 175), ("رين", 169), ("ستراسبورغ", 180), ("نانت|بريست", 6997), ("تولوز", 179), ("لوريان", 273)]),
    "uefa.champions": ("دوري أبطال أوروبا", [("ريال مدريد", 86), ("برشلونة", 83), ("بايرن ميونخ", 132), ("مانشستر سيتي", 382), ("ليفربول", 364),
               ("أرسنال|آرسنال", 359), ("باريس سان جيرمان", 160), ("إنتر ميلان|الإنتر", 110), ("دورتموند", 124), ("أتلتيكو مدريد", 1068),
               ("يوفنتوس", 111), ("تشيلسي", 363), ("ميلان", 103), ("ليفركوزن", 131)]),
    "afc.champions": ("دوري أبطال آسيا", [("الهلال", 929), ("النصر", 817), ("العميد|الاتحاد(?! (?:الفرنسي|الآسيوي|الدولي|الأوروبي|الوطني|السعودي|الإنجليزي|الإسباني|المصري|العربي|الخليجي|الأفريقي|الأردني|اللبناني|العراقي))", 2276), ("الأهلي السعودي|الأهلي|الاهلي|الراقي", 8346), ("السد", 0), ("العين", 0),
               ("الدحيل", 0), ("شباب الأهلي", 0), ("الشارقة", 0), ("الوحدة", 0), ("الغرافة", 0), ("القادسية", 22022)]),
}
OTHER = {"rus.1": "الدوري الروسي", "ned.1": "الدوري الهولندي", "por.1": "الدوري البرتغالي", "tur.1": "الدوري التركي", "bel.1": "الدوري البلجيكي",
         "sco.1": "الدوري الاسكتلندي", "gre.1": "الدوري اليوناني", "usa.1": "الدوري الأمريكي", "bra.1": "الدوري البرازيلي", "arg.1": "الدوري الأرجنتيني",
         "mex.1": "الدوري المكسيكي", "jpn.1": "الدوري الياباني", "kor.1": "الدوري الكوري", "fifa.world": "كأس العالم", "fifa.worldq": "تصفيات كأس العالم"}
SPORT = re.compile(r"مباراة|لاعب|مدرب|دوري|هدف|أهداف|فوز|يفوز|خسارة|يخسر|تعادل|صفقة|انتقال|التعاقد|تعاقد|عقد|ملعب|كأس|المنتخب|نادي|النادي|جماهير|جمهور|ركلة|إصابة|مصاب|تشكيلة|الجولة|موسم|بطولة|روشن|كرة|الهداف|حارس|مهاجم|مدافع|ديربي|كلاسيكو|تدريبات|معسكر|الإعارة|الميركاتو|يونايتد|سيتي")
STARS = re.compile(r"رونالدو|كريستيانو|ميسي|بنزيما|نيمار|مبابي")   # a star may not fill the list either
OTHER_SPORTS = re.compile(r"سيدات|كرة اليد|كرة السلة|سلة |السلة|الطائرة|كرة الطاولة|النسائية|للسيدات|السيدات|أولمبياد|ألعاب القوى|المطرقة|السباحة|التنس|الملاكمة|فورمولا|الجولف|الشطرنج|الرياضات الإلكترونية|الهوكي|الكاراتيه|الجودو|التايكوندو|الفروسية|البادل|الدراجات")
FOREIGN_AR = re.compile(r"المصري|المصرية|مصر|اللبناني|لبنان|الأردني|الأردن|التونسي|المغربي|الجزائري|الليبي|العراقي|السوداني|السوري|اليمني|البنك الأهلي|الزمالك|بيراميدز|الإسماعيلي|المقاولون|الوداد|الرجاء|الترجي|طرابلس|بنغازي|القاهرة|الدوري الممتاز المصري|الوحدات|الرمثا|الحسين إربد|الجزيرة الأردني")
SAUDI_SITES = "site:arriyadiyah.com OR site:okaz.com.sa OR site:alriyadh.com OR site:sabq.org OR site:aawsat.com OR site:alyaum.com OR site:al-jazirah.com OR site:almadina.com OR site:alwatan.com.sa OR site:spl.com.sa OR site:alarabiya.net OR site:spa.gov.sa"
BLOCKED_SOURCES = re.compile(r"^(صحيفة\s+)?عاجل$|ajel", re.I)
SKIP = re.compile(r"تذاكر|كيفية الحصول|كيفية شراء|القنوات الناقلة|مباشر|بث مباشر|فيديو:|صور:|إعلان|برعاية|توقعات|نتيجة مباراة .* اليوم الآن", re.I)
UA = {"User-Agent": "Mozilla/5.0 (VUE sport news; https://vue-tv.github.io)"}
MAX_PER_TEAM, MAX_STAR, LIMIT = 2, 2, 25

def fetch(query):
    url = "https://news.google.com/rss/search?" + urllib.parse.urlencode({"q": query + " when:2d", "hl": "ar", "gl": "SA", "ceid": "SA:ar"})
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=30) as r:
        root = ET.fromstring(r.read())
    out = []
    for it in root.iter("item"):
        title = (it.findtext("title") or "").strip()
        src_el = it.find("source"); source = ((src_el.text if src_el is not None else "") or "").strip()
        if BLOCKED_SOURCES.search(source) or BLOCKED_SOURCES.search((src_el.get("url") if src_el is not None else "") or ""): continue
        if source and title.endswith(" - " + source): title = title[: -len(source) - 3]
        title = re.sub(r"^\s*[\(\[«]?\s*عاجل\s*[\)\]»]?\s*[:|\-–—.،/]*\s*", "", re.sub(r"\s+", " ", title)).strip(" |-–—:")
        title = re.sub(r"^(?:أخبار [^|]{2,30} اليوم\s*\|\s*|بالفيديو\s*\.{2,}\s*|بالصور\s*\.{2,}\s*|خاص\s*\|\s*|رسميًا?\s*[:|]\s*)", "", title).strip()
        if len(title) < 15 or SKIP.search(title): continue
        src = re.split(r"\s+[:|\-–—]\s+", source)[0]
        src = re.sub(r"^https?://(www\.)?|/+$", "", src)
        item = {"t": title[:140], "s": src[:32]}
        try: item["p"] = int(email.utils.parsedate_to_datetime(it.findtext("pubDate")).timestamp())
        except Exception: pass
        out.append(item)
    return out

def build(league_id, words, clubs):
    pool, seen = [], set()
    def add(items):
        for x in items:
            k = re.sub(r"\W", "", x["t"])[:36]
            if k not in seen: seen.add(k); pool.append(x)
    saudi = league_id in ("ksa.1", "afc.champions")
    queries = [words]
    if saudi:  # Saudi outlets first: they cover every club, not only the stars
        for i in range(0, len(clubs), 5):
            queries.append("(" + " OR ".join('"' + n.split("|")[0] + '"' for n, _ in clubs[i:i + 5]) + ") (" + SAUDI_SITES + ")")
    for i in range(0, len(clubs), 4):  # clubs in groups of 4, each with a football word so "الهلال"/"الاتحاد" mean the clubs
        names = " OR ".join('"' + n.split("|")[0] + '"' for n, _ in clubs[i:i + 4])
        queries.append("(" + names + ") (كرة OR دوري OR مباراة OR لاعب OR مدرب)")
    for q in queries:
        try: add(fetch(q))
        except Exception as e: print(league_id, "failed:", e, file=sys.stderr)
        time.sleep(1)
    # tag each headline with the first club it names; keep football headlines only
    tagged = []
    for x in pool:
        if OTHER_SPORTS.search(x["t"]): continue
        if saudi and FOREIGN_AR.search(x["t"] + " " + x["s"]): continue
        hits = [(m.start(), n, cid) for n, cid in clubs for m in [re.search(n, x["t"])] if m]
        club = None
        if hits:
            hits.sort(); _, n, cid = hits[0]
            canon = {2276: "الاتحاد", 793: "الشباب", 21965: "الرياض", 8346: "الأهلي"}
            club = (canon.get(cid) or n.split("|")[0], cid)
        if not club and not re.search(words.split()[-1], x["t"]): continue
        if not SPORT.search(x["t"]): continue   # football words required (club names like الاتحاد/الخليج/التعاون are everyday words too)
        if club:
            x["k"] = club[0]
            if club[1]: x["l"] = LOGO.format(club[1])
        tagged.append(x)
    tagged.sort(key=lambda x: -x.get("p", 0))
    # round-robin over clubs (newest first inside each), at most MAX_PER_TEAM per club and MAX_STAR per star
    groups, order = {}, []
    for x in tagged:
        g = x.get("k", "_league")
        if g not in groups: groups[g] = []; order.append(g)
        groups[g].append(x)
    out, used, stars, i = [], {}, 0, 0
    while len(out) < LIMIT and any(groups.values()):
        g = order[i % len(order)]; i += 1
        while groups[g]:
            x = groups[g].pop(0)
            if used.get(g, 0) >= (4 if g == "_league" else MAX_PER_TEAM): groups[g] = []; break
            if STARS.search(x["t"]):
                if stars >= MAX_STAR: continue
                stars += 1
            used[g] = used.get(g, 0) + 1; out.append(x); break
    return out

def main():
    only = sys.argv[1:]
    jobs = [(lid, w, c) for lid, (w, c) in LEAGUES.items()] + [(lid, name, []) for lid, name in OTHER.items()]
    if only: jobs = [j for j in jobs if j[0] in only]
    for lid, words, clubs in jobs:
        items = build(lid, words, clubs)
        if len(items) >= 4:
            with open(f"news/league-{lid}.json", "w", encoding="utf-8") as f:
                json.dump({"league": lid, "updated": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="minutes"), "items": items}, f, ensure_ascii=False, separators=(",", ":"))
        print(lid, len(items), "clubs:", len({x.get("k") for x in items if x.get("k")}), file=sys.stderr)

if __name__ == "__main__":
    main()
