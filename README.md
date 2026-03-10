# threads-intel

**Scrape Threads, Reddit, PTT, 5ch & more — then analyze with LLM in one pipeline.**

A Python CLI tool that extracts structured data from public social platform pages and feeds it through LLM analysis for structured reports.

## Why?

Most scrapers give you raw HTML. Most LLM tools need clean input. **threads-intel** bridges the gap:

```
URL → Scrape (full content) → LLM Analysis → Structured Report
```

## Features

- **Threads** — Full post extraction via `data-sjs` + jmespath (not just og:meta)
- **Reddit** — Auto old.reddit.com + JSON API with HTML fallback
- **PTT** — Auto over18 cookie bypass
- **5ch** — Japan boards via VPN Gate proxy (optional)
- **Facebook** — Public pages via cookie-based scraping
- **LLM Analysis** — Pluggable backend (any OpenAI-compatible API)
- **Anti-detection** — UA rotation, random delays, stealth mode
- **Breakage SOP** — Built-in verification flow when sites change

## Quick Start

```bash
pip install threads-intel
```

### Scrape only

```bash
threads-intel scrape "https://www.threads.net/@zuck"
threads-intel scrape "https://old.reddit.com/r/LocalLLaMA"
threads-intel scrape "https://www.ptt.cc/bbs/Stock/index.html"
```

### Scrape + Analyze

```bash
export MINIMAX_API_KEY="your-key"
threads-intel analyze "https://www.threads.net/@zuck"
threads-intel analyze "https://old.reddit.com/r/LocalLLaMA" --prompt "focus on open source models"
```

### Output formats

```bash
threads-intel analyze "https://example.com" --json    # JSON output
threads-intel scrape "https://example.com" --raw      # Raw HTML
threads-intel scrape "https://example.com" --tables   # Tables as JSON
threads-intel scrape "https://example.com" --links    # All links
```

## Supported Sites

| Site | Status | Method | Notes |
|------|--------|--------|-------|
| Threads | Working | data-sjs + jmespath | Full posts, likes, usernames |
| Reddit | Working | old.reddit.com + .json | Auto fallback to HTML |
| PTT | Working | over18 cookie | |
| 5ch | Working | Direct + VPN Gate | Japan IP recommended |
| Facebook | Beta | Public pages | Cookie auth optional |
| Dcard | Blocked | - | Aggressive anti-bot |
| X/Twitter | Blocked | - | Requires login |

## Threads Extraction

Threads hides full post data inside `<script data-sjs>` tags as JSON. We use StealthyFetcher to render the page, then jmespath to extract structured data:

```python
from threads_intel import scrape

result = scrape("https://www.threads.net/@zuck")
for post in result["posts"]:
    print(f"@{post['username']}: {post['text'][:80]}")
    print(f"  Likes: {post.get('like_count', '?')} | {post.get('published_on', '')}")
```

Output fields per post:
- `text` — Full post content
- `username`, `user_verified`, `user_pic`
- `like_count`, `published_on`
- `url` — Direct link to post
- `images`, `videos` — Media URLs

## LLM Analysis

Default analysis produces a structured report:

1. One-line summary (30 chars)
2. Key points (3-5 bullets)
3. Investment/tech relevance
4. Credibility assessment (high/medium/low)
5. Suggested action

Custom prompts supported via `--prompt`.

## When Things Break

Sites change. Scrapers break. We include a [Breakage Verification SOP](docs/BREAKAGE_SOP.md) so you know exactly what to do:

1. Confirm temporary vs permanent failure
2. Check HTTP status codes
3. Test against known-working baseline URLs
4. Log the incident
5. Decision table for fixes

## Architecture

```
┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│  CLI / API  │────▶│   Scraper    │────▶│  Analyzer   │
│             │     │              │     │  (LLM)      │
│ threads-intel│     │ Scrapling    │     │ MiniMax/etc │
│  analyze    │     │ StealthyFetch│     │             │
└─────────────┘     └──────────────┘     └─────────────┘
                           │
                    Site-specific:
                    - Threads: data-sjs + jmespath
                    - Reddit: .json API
                    - PTT: over18 cookie
                    - 5ch: VPN Gate proxy
```

## First Run

Threads scraping uses a headless browser (Playwright/Chromium). On first run, it will automatically download Chromium (~150MB). This is a one-time setup:

```bash
# If auto-download fails, run manually:
playwright install chromium
```

Other sites (Reddit, PTT) use lightweight HTTP requests — no browser needed.

> **Note:** Prefer environment variables over `--api-key` for passing API keys. Command-line arguments may be visible in process listings.

## Requirements

- Python 3.10+
- Linux / macOS recommended (Windows experimental)
- [Scrapling](https://github.com/D4Vinci/Scrapling) (auto-installed)
- jmespath, nested_lookup (auto-installed)
- LLM API key (for analysis mode only)

## Disclaimer

This tool is for educational and research purposes. It only accesses publicly available data. Users are responsible for complying with each platform's Terms of Service and applicable laws. Do not use this tool to stalk, harass, or collect personal information about individuals without consent. The authors are not liable for misuse.

## Credits

- [Scrapling](https://github.com/D4Vinci/Scrapling) — Core fetching engine
- [Scrapfly](https://scrapfly.io/blog/posts/how-to-scrape-threads) — data-sjs extraction technique reference
- [jmespath](https://jmespath.org/) — JSON query language

## License

MIT

## Contributing

Issues and PRs welcome. See [BREAKAGE_SOP.md](docs/BREAKAGE_SOP.md) when reporting scraper failures.
