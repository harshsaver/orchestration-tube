# Caught Up

**AI agents in 20 videos, in order.** For the thousands of people who feel they've missed the boat on AI agents and coding with AI: a short path through the videos Hacker News keeps recommending, from "what is an LLM" to running a swarm of agents. No login; progress is saved in your browser.

It's the top of a funnel for [October](https://www.october.dev): Instagram reels spotlight one video each, the reels lead to the site, and October shows up on the path once it's useful, when people start running more than one agent (levels 3 and 4).

"Caught Up" is a working name.

## What's here

| Path | What it is |
|---|---|
| `site/` | The site. Plain HTML/CSS/JS, no build step. `data.js` is generated. |
| `curation/path.json` | **The picks.** The levels, the 20 videos, why each one, a take-away, a reel hook, the October notes, the method text. Edit this. |
| `pipeline/mine_hn.py` | Finds YouTube videos linked in Hacker News comments since 2023 that talk about agents, AI coding tools, LLMs. Counts how many different people linked each one, in how many months. |
| `pipeline/from_hackertube.py` | Pulls the AI / LLM videos out of [HackerTube's dataset](https://hackertube.org/data) (20 years of HN, strict filter). Good for the foundations. |
| `pipeline/build.py` | Checks every pick still exists and can be embedded, adds the HN numbers (and durations, with an API key), writes `site/data.js` and `content/reels.md`. |
| `content/reels.md` | One reel brief per video: hook, take-away, link. Generated. |
| `data/` | Candidate lists from the two sources plus small caches. `data/raw/` is not committed. |

## Run it

The site is static. Open `site/index.html` directly, or serve the folder:

```bash
python3 -m http.server -d site 8000
```

## Refresh the picks

```bash
mkdir -p data/raw && curl -sSfL -o data/raw/videos.jsonl https://hackertube.org/download/videos.jsonl
```

```bash
python3 -I pipeline/from_hackertube.py data/raw/videos.jsonl data/hackertube_ai.jsonl
```

```bash
python3 -I pipeline/mine_hn.py data/hn_candidates.jsonl
```

Mining takes a few minutes; it is polite to the API. Then look through `data/hn_candidates.jsonl` (sorted by how many people linked each video), edit `curation/path.json`, and rebuild:

```bash
python3 -I pipeline/build.py
```

`build.py` fails if a pick has been deleted, made private, or can't be embedded, so a monthly rebuild catches rot.

### Durations

YouTube's oEmbed doesn't give durations. To show them (and "~N hours total" on the site), create a free YouTube Data API key in Google Cloud and run:

```bash
YOUTUBE_API_KEY=... python3 -I pipeline/build.py
```

## Credits and licences

- Foundational picks and their HN numbers come from [HackerTube](https://hackertube.org/data)'s dataset, ODC-By 1.0, built on the [open-index/hacker-news](https://huggingface.co/datasets/open-index/hacker-news) archive. Credit both wherever the data shows up.
- Agent-era candidates come from the public [HN Algolia API](https://hn.algolia.com/api).
- Videos are embedded with YouTube's player (`youtube-nocookie.com`). Nothing is rehosted.
