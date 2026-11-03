"""Pull AI / LLM / agent videos out of HackerTube's public dataset.

HackerTube (https://hackertube.org/data) publishes its 6,454 videos under
ODC-By 1.0: reuse is fine as long as HackerTube and the open-index/hacker-news
dataset are credited. Its filter is strict (3+ people, 3+ months), so it is a
good source for the "foundations" end of the path, and thin on agent-era
material, which mine_hn.py covers.

    curl -sSfL -o data/raw/videos.jsonl https://hackertube.org/download/videos.jsonl
    python3 -I pipeline/from_hackertube.py data/raw/videos.jsonl data/hackertube_ai.jsonl
"""

import json
import re
import sys

AI_AREA = "AI, Machine Learning & Data"
KEYWORDS = re.compile(
    r"\b(llms?|gpt|chatgpt|claude|large language models?|transformers?|"
    r"ai agents?|agentic|multi-agent|coding agents?|copilot|vibe coding|"
    r"prompt\w*|neural networks?|deep learning)\b",
    re.I,
)


def main(src, out):
    kept = []
    for line in open(src):
        r = json.loads(line)
        text = " ".join([r["title"], r["summary"], r.get("primary_topic", ""), " ".join(r["tags"])])
        in_area = any(c["area_name"] == AI_AREA for c in r["categories"])
        if not (in_area and KEYWORDS.search(text)):
            continue
        kept.append({
            "vid": r["vid"],
            "title": r["title"],
            "channel": r["channel"],
            "summary": r["summary"],
            "why_hn": r["why_hn"],
            "level": r.get("level"),
            "content_type": r.get("content_type"),
            "shelf_life": r.get("shelf_life"),
            "quote": r.get("quote"),
            "hn": r["hn"],
            "score": r["score"],
        })
    kept.sort(key=lambda r: -r["score"])
    with open(out, "w") as f:
        for r in kept:
            f.write(json.dumps(r) + "\n")
    print(f"{len(kept)} AI videos -> {out}", file=sys.stderr)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
