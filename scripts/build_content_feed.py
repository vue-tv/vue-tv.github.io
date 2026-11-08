#!/usr/bin/env python3
"""Build content-feed.json + content.js for VUE backgrounds.

Every 5 days a different set is chosen automatically from the pools below, so
the TVs get fresh backgrounds without any app update. Add an image by dropping a
JPG into assets/content/backgrounds/ and listing it in a pool."""
import datetime, hashlib, json, os, random

GENERAL = ["riyadh-kingdom-centre.jpg", "jeddah-albalad.jpg", "alula-elephant-rock.jpg", "abha-asir.jpg", "diriyah-turaif.jpg",
           "saudi-riyadh-skyline.jpg", "saudi-riyadh-kafd.jpg", "saudi-jeddah-corniche-2.jpg"]
SPORT = ["stadium-king-fahd-gulf-cup.jpg", "stadium-king-fahd.jpg", "stadium-night-match.jpg"]
PERIOD_DAYS, PICK = 5, 6
BASE = "/assets/content/backgrounds/"

def pick(pool, period, salt):
    pool = [p for p in pool if os.path.exists("assets/content/backgrounds/" + p)]
    rng = random.Random(f"{salt}-{period}"); order = pool[:]; rng.shuffle(order)
    return [BASE + p for p in order[:min(PICK, len(order))]]

def main():
    today = datetime.date.today()
    period = today.toordinal() // PERIOD_DAYS
    gen, sport = pick(GENERAL, period, "general"), pick(SPORT, period, "sport")
    tag = hashlib.sha1(json.dumps([gen, sport]).encode()).hexdigest()[:8]  # new revision whenever the images change
    feed = {"product": "VUE", "schemaVersion": 1, "revision": f"p{period}-{tag}",
            "updatedAt": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
            "backgrounds": gen, "sportBackgrounds": sport}
    with open("content-feed.json", "w", encoding="utf-8") as f:
        json.dump(feed, f, ensure_ascii=False, indent=2); f.write("\n")
    body = json.dumps(feed, ensure_ascii=False, separators=(",", ":"))
    with open("content.js", "w", encoding="utf-8") as f:
        # Calls the app's fixed receiver directly (location.search would be the TV page's URL, not this script's).
        f.write("(function(){var cb=window.__VUE_CONTENT_RECEIVE__;if(typeof cb==='function')cb(" + body + ");})();\n")
    print("revision", feed["revision"], len(feed["backgrounds"]), "general,", len(feed["sportBackgrounds"]), "sport")

if __name__ == "__main__":
    main()
