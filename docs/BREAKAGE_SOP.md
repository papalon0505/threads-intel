# Breakage Verification SOP

When a scraper fails (empty results, errors, or blocks), follow these steps:

## Step 1: Confirm temporary vs permanent

```bash
# Run 3 times, 30s apart
for i in 1 2 3; do
  threads-intel scrape "<url>" --no-delay --timeout 30 2>&1 | head -5
  sleep 30
done
```
- All 3 fail → likely permanent (site changed)
- Intermittent → rate limiting, increase delays

## Step 2: Check HTTP status

```bash
threads-intel scrape "<url>" --raw --no-delay 2>&1 | head -3
```
- 200 + empty content → page structure changed
- 301/302 → redirected (possibly to login page)
- 403 → blocked
- 429 → rate limited

## Step 3: Test baseline URLs

```bash
# Known-working URLs for comparison
threads-intel scrape "https://www.threads.net/@zuck" --no-delay
threads-intel scrape "https://old.reddit.com/r/stocks" --no-delay
threads-intel scrape "https://www.ptt.cc/bbs/Stock/index.html" --no-delay
```

## Step 4: Decision table

| Situation | Action |
|-----------|--------|
| 200 but empty | Update CSS selector or data-sjs parsing |
| 403 blocked | Try stealth mode, rotate UA/delays |
| 301 to login | Evaluate cookie/session auth |
| API endpoint dead | Search for new endpoints |
| Rate limited (429) | Increase delays, reduce frequency |

## Step 5: Update docs

After fixing, update the Site Compatibility table in README.md.

## Repair History

| Date | Site | Issue | Fix |
|------|------|-------|-----|
| 2026-03-10 | Threads | Only og:meta, no full content | Added data-sjs + jmespath extraction |
| 2026-03-10 | Reddit | Blocked | old.reddit.com + .json API |
| 2026-03-10 | PTT | Blocked | over18=1 cookie |
| 2026-03-10 | Dcard | 403 | Abandoned (too aggressive anti-bot) |
