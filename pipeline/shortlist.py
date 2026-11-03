"""Turn the mined HN candidates into a shortlist a person can read and pick from.

Keeps videos that 2+ different people linked in comments that really talk about
LLMs, agents or AI coding tools, looks up each title and channel with YouTube's
oEmbed (cached in data/oembed_cache.json), and writes data/shortlist.md with a
couple of the comments for each, so you can see why people linked it.

    python3 -I pipeline/shortlist.py data/hn_candidates.jsonl data/shortlist.md
"""

import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from build import P, load_cache, oembed  # noqa: E402

TOPIC = re.compile(
    r"\b(claude( code)?|codex|coding agents?|ai agents?|llm agents?|agentic|sub-?agents?|multi-agent|"
    r"vibe cod\w*|cursor|aider|copilot|windsurf|devin|karpathy|context engineering|"
    r"prompt\w*|orchestrat\w*|llms?|gpt\w*|chatgpt|language models?|transformers?)\b",
    re.I,
)


def main(src, out):
    cache = load_cache(P("data", "oembed_cache.json"))
    rows = []
    for line in open(src):
        r = json.loads(line)
        good = [c for c in r["comments"] if TOPIC.search(c["snippet"])]
        people = {c["author"] for c in good}
        if len(people) >= 2:
            rows.append((len(people), len({c["month"] for c in good}), r, good))
    rows.sort(key=lambda x: (-x[0], -x[1]))

    lines = ["# HN shortlist", "",
             f"{len(rows)} videos that 2+ different people linked in HN comments about LLMs, agents or AI coding (2023 on).",
             "Sorted by number of people. Gone, private or not embeddable videos are marked.", ""]
    for people, months, r, good in rows:
        m = oembed(r["vid"], cache)
        title = m.get("title", f"(unavailable: HTTP {m.get('status')})")
        chan = m.get("channel", "")
        lines.append(f"## {title}")
        lines.append(f"`{r['vid']}` · {chan} · **{people} people**, {months} months, "
                     f"{r['first_month']} to {r['last_month']} · https://www.youtube.com/watch?v={r['vid']}")
        lines.append("")
        for c in good[:3]:
            lines.append(f"> [{c['month']}, on \"{c['story']}\"](https://news.ycombinator.com/item?id={c['id']}) "
                         f"{c['snippet'][:280]}")
            lines.append("")
    json.dump(cache, open(P("data", "oembed_cache.json"), "w"), indent=1, sort_keys=True)
    open(out, "w").write("\n".join(lines))
    print(f"{len(rows)} videos -> {out}", file=sys.stderr)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
