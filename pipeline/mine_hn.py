"""Mine Hacker News comments for YouTube videos about AI agents and coding with AI.

Uses the public HN Algolia search API (no key needed). For each search term and
each quarter since START, it pulls comments that mention YouTube plus the term,
pulls the YouTube video ids out of the comment HTML, and groups them by video.

Output: one JSON line per video with how many different people linked it, in
how many different months, and which comments. That's the "HN keeps
recommending it" signal HackerTube uses, applied to the AI-agent era.

    python3 -I pipeline/mine_hn.py data/hn_candidates.jsonl
"""

import collections
import html
import json
import re
import sys
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone

API = "https://hn.algolia.com/api/v1/search_by_date"
START = datetime(2023, 1, 1, tzinfo=timezone.utc)

TERMS = [
    "agents", "agentic", "multi-agent", "subagents", "swarm",
    "claude code", "claude", "anthropic", "codex", "cursor", "copilot", "aider", "windsurf", "devin",
    "vibe coding", "coding assistant", "ai coding", "llm", "llms",
    "mcp", "prompt engineering", "context engineering", "karpathy",
    "worktrees", "orchestration",
]
PREFIXES = ["youtube", "youtu.be"]

VID_RE = re.compile(
    r"(?:youtube\.com/(?:watch\?(?:[^\"'\s<>]*&)?v=|embed/|live/|shorts/|v/)|youtu\.be/)"
    r"([A-Za-z0-9_-]{11})"
)


def quarters(start, end):
    y, q = start.year, (start.month - 1) // 3
    while True:
        a = datetime(y, q * 3 + 1, 1, tzinfo=timezone.utc)
        if a >= end:
            return
        q += 1
        if q == 4:
            y, q = y + 1, 0
        b = datetime(y, q * 3 + 1, 1, tzinfo=timezone.utc)
        yield int(a.timestamp()), int(min(b, end).timestamp())


def fetch(query, lo, hi):
    params = {
        "query": query,
        "tags": "comment",
        "hitsPerPage": 1000,
        "typoTolerance": "false",
        "numericFilters": f"created_at_i>={lo},created_at_i<{hi}",
    }
    url = API + "?" + urllib.parse.urlencode(params)
    for attempt in range(4):
        try:
            with urllib.request.urlopen(url, timeout=60) as r:
                return json.load(r)["hits"]
        except Exception as e:  # network hiccup or rate limit
            if attempt == 3:
                print(f"  giving up on {query!r} {lo}: {e}", file=sys.stderr)
                return []
            time.sleep(2 ** (attempt + 1))


def main(out_path):
    now = datetime.now(timezone.utc)
    seen_comments = set()
    videos = collections.defaultdict(lambda: {
        "authors": set(), "months": set(), "comments": [], "terms": set(),
    })

    for term in TERMS:
        for prefix in PREFIXES:
            query = f"{prefix} {term}"
            term_re = re.compile(r"\b" + re.escape(term).replace(r"\ ", r"[\s-]+") + r"\b", re.I)
            n = 0
            for lo, hi in quarters(START, now):
                for h in fetch(query, lo, hi):
                    text = html.unescape(h.get("comment_text") or "")
                    vids = set(VID_RE.findall(text))
                    plain = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", text))
                    # Algolia matches loosely; keep only comments that really say the term.
                    if not vids or not term_re.search(plain):
                        continue
                    for vid in vids:
                        v = videos[vid]
                        v["terms"].add(term)
                        if (h["objectID"], vid) in seen_comments:
                            continue
                        seen_comments.add((h["objectID"], vid))
                        v["authors"].add(h.get("author"))
                        v["months"].add(h["created_at"][:7])
                        v["comments"].append({
                            "id": int(h["objectID"]),
                            "author": h.get("author"),
                            "month": h["created_at"][:7],
                            "story": h.get("story_title"),
                            "snippet": plain[:600],
                        })
                        n += 1
                time.sleep(0.2)
            print(f"{query!r}: {n} new links", file=sys.stderr)

    rows = []
    for vid, v in videos.items():
        rows.append({
            "vid": vid,
            "recommenders": len(v["authors"]),
            "months": len(v["months"]),
            "first_month": min(v["months"]),
            "last_month": max(v["months"]),
            "terms": sorted(v["terms"]),
            "comments": sorted(v["comments"], key=lambda c: c["month"]),
        })
    rows.sort(key=lambda r: (-r["recommenders"], -r["months"]))
    with open(out_path, "w") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")
    multi = sum(r["recommenders"] >= 2 for r in rows)
    print(f"{len(rows)} videos, {multi} linked by 2+ people -> {out_path}", file=sys.stderr)


if __name__ == "__main__":
    main(sys.argv[1])
