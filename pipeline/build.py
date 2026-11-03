"""Turn the hand-checked picks in curation/path.json into the site's data file.

For every video it:
  * checks with YouTube's public oEmbed endpoint that it exists and can be
    embedded (no API key needed), and takes the real title and channel;
  * attaches the Hacker News signal (how many people linked it, since when)
    from data/hn_candidates.jsonl, falling back to data/hackertube_ai.jsonl;
  * checks each quote really appears in the HN comment it links to;
  * if YOUTUBE_API_KEY is set, adds durations from the YouTube Data API.

Writes site/data.js and content/reels.md (one reel brief per video).

    python3 -I pipeline/build.py
"""

import html
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
P = lambda *a: os.path.join(ROOT, *a)  # noqa: E731


def read_jsonl(path):
    if not os.path.exists(path):
        return {}
    return {r["vid"]: r for r in map(json.loads, open(path))}


def load_cache(path):
    return json.load(open(path)) if os.path.exists(path) else {}


def oembed(vid, cache):
    if vid in cache:
        return cache[vid]
    url = "https://www.youtube.com/oembed?" + urllib.parse.urlencode(
        {"url": f"https://www.youtube.com/watch?v={vid}", "format": "json"})
    try:
        with urllib.request.urlopen(url, timeout=30) as r:
            d = json.load(r)
            cache[vid] = {"ok": True, "title": d["title"], "channel": d["author_name"]}
    except urllib.error.HTTPError as e:
        # 404: gone or private. 401: owner turned off embedding.
        cache[vid] = {"ok": False, "status": e.code}
    return cache[vid]


def iso_dur(s):
    m = re.fullmatch(r"P(?:(\d+)D)?T?(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", s or "")
    if not m:
        return None
    d, h, mi, se = (int(x or 0) for x in m.groups())
    return d * 86400 + h * 3600 + mi * 60 + se


def durations(vids, cache):
    key = os.environ.get("YOUTUBE_API_KEY")
    missing = [v for v in vids if v not in cache]
    if key and missing:
        for i in range(0, len(missing), 50):
            q = urllib.parse.urlencode({"part": "contentDetails", "id": ",".join(missing[i:i + 50]), "key": key})
            with urllib.request.urlopen("https://www.googleapis.com/youtube/v3/videos?" + q, timeout=30) as r:
                for item in json.load(r).get("items", []):
                    cache[item["id"]] = iso_dur(item["contentDetails"]["duration"])
    return {v: cache.get(v) for v in vids}


def signal(vid, ht, hn):
    """Use whichever source saw more people point to the video."""
    best = (0, "")
    if vid in hn:
        r = hn[vid]
        people = "person" if r["recommenders"] == 1 else "people"
        best = (r["recommenders"], f"Linked by {r['recommenders']} {people} in HN comments since {r['first_month'][:4]}")
    if vid in ht and ht[vid]["hn"]["recommenders"] > best[0]:
        h = ht[vid]["hn"]
        best = (h["recommenders"], f"Recommended by {h['recommenders']} people on HN since {h['first_year']}")
    return best


def norm(t):
    t = html.unescape(re.sub(r"<[^>]+>", " ", t))
    t = t.translate(str.maketrans({"\u2018": "'", "\u2019": "'", "\u201c": '"', "\u201d": '"'}))
    return re.sub(r"\s+", " ", t).strip().lower()


def quote_ok(q, cache):
    key = str(q["hn"])
    if key not in cache:
        url = f"https://hn.algolia.com/api/v1/items/{q['hn']}"
        try:
            with urllib.request.urlopen(url, timeout=30) as r:
                cache[key] = json.load(r).get("text") or ""
        except urllib.error.HTTPError:
            cache[key] = ""
    return norm(q["text"]) in norm(cache[key])


def main():
    cur = json.load(open(P("curation", "path.json")))
    ht = read_jsonl(P("data", "hackertube_ai.jsonl"))
    hn = read_jsonl(P("data", "hn_candidates.jsonl"))
    oe_cache = load_cache(P("data", "oembed_cache.json"))
    dur_cache = load_cache(P("data", "durations_cache.json"))
    q_cache = load_cache(P("data", "quotes_cache.json"))

    all_videos = [v for lvl in cur["levels"] for v in lvl["videos"]] + cur.get("thisMonth", [])
    vids = [v["vid"] for v in all_videos]
    dupes = {v for v in vids if vids.count(v) > 1}
    if dupes:
        sys.exit(f"duplicate picks: {sorted(dupes)}")

    bad = []
    for v in all_videos:
        meta = oembed(v["vid"], oe_cache)
        if not meta["ok"]:
            bad.append((v["vid"], meta["status"]))
            continue
        v.setdefault("title", meta["title"])
        v.setdefault("channel", meta["channel"])
        n, text = signal(v["vid"], ht, hn)
        v["hn_people"] = n
        v["signal"] = text
        if v.get("quote") and not quote_ok(v["quote"], q_cache):
            bad.append((v["vid"], f"quote not found in HN comment {v['quote']['hn']}"))
    json.dump(oe_cache, open(P("data", "oembed_cache.json"), "w"), indent=1, sort_keys=True)
    json.dump(q_cache, open(P("data", "quotes_cache.json"), "w"), indent=1, sort_keys=True)
    if bad:
        sys.exit("problems with these picks:\n  " + "\n  ".join(f"{v}: {why}" for v, why in bad))

    durs = durations(vids, dur_cache)
    json.dump(dur_cache, open(P("data", "durations_cache.json"), "w"), indent=1, sort_keys=True)
    for v in all_videos:
        if durs.get(v["vid"]):
            v["duration"] = durs[v["vid"]]

    site = {k: cur[k] for k in ("updated", "lede", "levels", "thisMonth", "method", "credits")}
    for v in all_videos:
        v.pop("hook", None)  # reel hooks are for content/reels.md, not the site
    with open(P("site", "data.js"), "w") as f:
        f.write("// Generated by pipeline/build.py from curation/path.json. Edit that file, not this one.\n")
        f.write("window.CAUGHT_UP = " + json.dumps(site, indent=1, ensure_ascii=False) + ";\n")

    write_reels(json.load(open(P("curation", "path.json"))), oe_cache)
    n = sum(len(lvl["videos"]) for lvl in cur["levels"])
    print(f"ok: {n} videos on the path, {len(cur.get('thisMonth', []))} this month -> site/data.js, content/reels.md")


def write_reels(cur, oe):
    os.makedirs(P("content"), exist_ok=True)
    out = ["# Reel briefs", "",
           "One reel per video on the path. Generated by `pipeline/build.py` from `curation/path.json`.", "",
           "Every reel follows the same shape:", "",
           "1. **Hook (0-2s):** the line below, on screen and spoken.",
           "2. **Why it's worth your time (2-15s):** the why, in your own words, over a still of the talk or your own screen. Optionally the HN quote on screen. Don't reupload their footage.",
           "3. **Where it sits (15-20s):** \"It's video N of 20 on the path. You don't need the rest of YouTube.\"",
           "4. **Ask:** \"Comment PATH and I'll send you all 20.\" The DM links to the site.", ""]
    n = 0
    for lvl in cur["levels"]:
        out += [f"## Level {lvl['id']}: {lvl['name']}", ""]
        for v in lvl["videos"]:
            n += 1
            title = v.get("title") or oe.get(v["vid"], {}).get("title", v["vid"])
            out += [f"### {n}. {title}", "",
                    f"- **Hook:** {v.get('hook', '')}",
                    f"- **Why:** {v.get('why', '')}"]
            if v.get("quote"):
                q = v["quote"]
                out.append(f"- **HN quote:** \"{q['text']}\" ([{q['year']}](https://news.ycombinator.com/item?id={q['hn']}))")
            out += [f"- **Link:** https://www.youtube.com/watch?v={v['vid']}", ""]
    open(P("content", "reels.md"), "w").write("\n".join(out))


if __name__ == "__main__":
    main()
