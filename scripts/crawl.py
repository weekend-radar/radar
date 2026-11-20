"""Crawl PUBLIC Telegram channels via their web preview (https://t.me/s/<channel>),
keep posts that look like weekend activities, merge duplicates, save to data/events.json."""
import json, re, time, sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
import requests
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parent.parent
CFG = json.loads((ROOT / "channels.json").read_text(encoding="utf-8"))
OUT = ROOT / "data" / "events.json"
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; WeekendRadar/1.0)"}

CATEGORIES = {
    "Free":       r"\bfree\b|\bfoc\b|free entry|free admission|complimentary|giveaway|freebie|no charge",
    "Exhibition": r"exhibit|exhibition|gallery|museum|art ?(show|fair)|installation|showcase",
    "Festival":   r"festival|fair\b|carnival|bazaar|market|pasar|fest\b",
    "Workshop":   r"workshop|class\b|course|seminar|talk\b|webinar|meetup|masterclass",
    "Outdoor":    r"hike|walk\b|run\b|cycling|park\b|beach|nature|kayak|picnic|outdoor",
    "Music/Show": r"concert|gig\b|live music|performance|theatre|theater|movie|screening|show\b",
    "Family":     r"family|kids|children|parent",
    "Food":       r"food|tasting|buffet|promo|1-for-1|1 for 1|discount|sale\b",
}
CAT_RE = {k: re.compile(v, re.I) for k, v in CATEGORIES.items()}
URL_RE = re.compile(r"https?://[^\s<>\"]+")


def classify(text):
    return [k for k, rx in CAT_RE.items() if rx.search(text)]


def parse_page(html, channel):
    soup = BeautifulSoup(html, "html.parser")
    posts = []
    for msg in soup.select("div.tgme_widget_message[data-post]"):
        post_id = msg["data-post"]
        txt_el = msg.select_one("div.tgme_widget_message_text")
        if not txt_el:
            continue
        for br in txt_el.find_all("br"):
            br.replace_with("\n")
        text = txt_el.get_text().strip()
        time_el = msg.select_one("a.tgme_widget_message_date time")
        date = time_el["datetime"] if time_el and time_el.has_attr("datetime") else None
        img = None
        ph = msg.select_one("a.tgme_widget_message_photo_wrap")
        if ph and ph.has_attr("style"):
            m = re.search(r"url\('([^']+)'\)", ph["style"])
            img = m.group(1) if m else None
        links = [a["href"] for a in txt_el.find_all("a", href=True) if a["href"].startswith("http")]
        posts.append({
            "id": post_id, "channel": channel, "date": date, "text": text, "image": img,
            "link": f"https://t.me/{post_id}",
            "urls": list(dict.fromkeys(links + URL_RE.findall(text)))[:5],
        })
    return posts


def fetch_channel(channel, pages):
    all_posts, before = [], None
    for _ in range(pages):
        url = f"https://t.me/s/{channel}" + (f"?before={before}" if before else "")
        try:
            r = requests.get(url, headers=HEADERS, timeout=30)
            r.raise_for_status()
        except Exception as e:
            print(f"[warn] {channel}: {e}", file=sys.stderr)
            break
        posts = parse_page(r.text, channel)
        if not posts:
            break
        all_posts += posts
        before = min(int(p["id"].split("/")[1]) for p in posts)
        time.sleep(2)  # be polite
    return all_posts


# ---------- De-duplication ----------
STOP = set("the and for with this that are you our your will from at on in of to a an is it be by or as we us all get now new more join here info link click".split())
SIM_THRESHOLD = 0.55   # text similarity (0-1) above which two posts are "the same event"
LINK_SIM_MIN = 0.30    # if they also share the same link, a lower similarity is enough


def tokens(text):
    t = URL_RE.sub(" ", text.lower())
    t = re.sub(r"[^\w\s]", " ", t)          # drop emoji / punctuation
    return {w for w in t.split() if len(w) > 2 and w not in STOP}


def norm_urls(urls):
    out = set()
    for u in urls:
        u = re.sub(r"[?#].*$", "", u.lower()).rstrip("/")
        if u and "t.me/" not in u:
            out.add(u)
    return out


def similarity(a, b):
    if not a or not b:
        return 0.0
    inter = len(a & b)
    # also compare against the smaller set, so a short repost of a long post still matches
    return max(inter / len(a | b), inter / min(len(a), len(b)) * 0.9)


def is_dup(x, y):
    sim = similarity(x["_tok"], y["_tok"])
    if sim >= SIM_THRESHOLD:
        return True
    return sim >= LINK_SIM_MIN and bool(x["_urls"] & y["_urls"])


def dedupe(events):
    """Merge near-identical posts. Keeps the richest post (image, longer text)
    and lists the others in `also_in`."""
    for e in events:
        e["_tok"] = tokens(e["text"])
        e["_urls"] = norm_urls(e.get("urls", []))
    order = sorted(events, key=lambda e: (bool(e.get("image")), len(e["text"])), reverse=True)
    kept = []
    for e in order:
        also = {d["id"]: d for d in e.pop("also_in", [])}
        for k in kept:
            if is_dup(e, k):
                known = {d["id"]: d for d in k.get("also_in", [])}
                known[e["id"]] = {"id": e["id"], "channel": e["channel"], "link": e["link"], "date": e["date"]}
                known.update(also)
                k["also_in"] = list(known.values())
                break
        else:
            e["also_in"] = list(also.values())
            kept.append(e)
    for k in kept:
        k.pop("_tok", None); k.pop("_urls", None)
        k["also_in"] = [d for d in k["also_in"] if d["id"] != k["id"]]
    return kept


def main():
    existing = {}
    if OUT.exists():
        for e in json.loads(OUT.read_text(encoding="utf-8")).get("events", []):
            existing[e["id"]] = e

    for ch in CFG["channels"]:
        for p in fetch_channel(ch, CFG.get("pages_per_channel", 3)):
            cats = classify(p["text"])
            if cats:
                p["categories"] = cats
                old = existing.get(p["id"])
                if old and old.get("also_in"):
                    p["also_in"] = old["also_in"]
                existing[p["id"]] = p

    cutoff = datetime.now(timezone.utc) - timedelta(days=CFG.get("keep_days", 21))
    events = []
    for e in existing.values():
        try:
            if datetime.fromisoformat(e["date"]) >= cutoff:
                events.append(e)
        except Exception:
            events.append(e)
    before = len(events)
    events = dedupe(events)
    print(f"Merged {before - len(events)} duplicate posts")
    events.sort(key=lambda e: e.get("date") or "", reverse=True)
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(json.dumps({"updated": datetime.now(timezone.utc).isoformat(), "events": events},
                              ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"Saved {len(events)} events")


if __name__ == "__main__":
    main()
