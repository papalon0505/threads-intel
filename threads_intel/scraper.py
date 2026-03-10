"""
Core scraper module — site-aware fetching with anti-detection.

Supported: Threads, Reddit, PTT, 5ch, Facebook (beta)
"""

import json
import random
import re
import time
from datetime import datetime
from urllib.parse import urlparse

import jmespath
from nested_lookup import nested_lookup
from scrapling import Fetcher

# ---------------------------------------------------------------------------
# User-Agent pool (latest desktop browsers)
# ---------------------------------------------------------------------------
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:134.0) Gecko/20100101 Firefox/134.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:134.0) Gecko/20100101 Firefox/134.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.2 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36 Edg/131.0.0.0",
]


def _random_ua():
    return random.choice(USER_AGENTS)


def _base_headers(url: str) -> dict:
    parsed = urlparse(url)
    return {
        "User-Agent": _random_ua(),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "zh-TW,zh;q=0.9,en-US;q=0.8,en;q=0.7",
        "Accept-Encoding": "gzip, deflate, br",
        "DNT": "1",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "Referer": f"{parsed.scheme}://{parsed.netloc}/",
    }


def _random_delay(min_s=1.0, max_s=3.0):
    time.sleep(random.uniform(min_s, max_s))


# ---------------------------------------------------------------------------
# Site-specific URL rewriting
# ---------------------------------------------------------------------------

def _prepare_request(url: str) -> dict:
    parsed = urlparse(url)
    host = parsed.netloc.lower()
    headers = _base_headers(url)
    cookies = {}

    # Reddit
    if "reddit.com" in host:
        if host in ("www.reddit.com", "reddit.com"):
            url = url.replace("://www.reddit.com", "://old.reddit.com")
            url = url.replace("://reddit.com", "://old.reddit.com")
        if not url.endswith(".json") and "/wiki/" not in url:
            url = url.rstrip("/") + ".json"
        headers["Accept"] = "text/html,application/json,*/*;q=0.8"

    # PTT
    elif "ptt.cc" in host:
        cookies["over18"] = "1"
        headers["Referer"] = "https://www.ptt.cc/"
        if "://ptt.cc" in url:
            url = url.replace("://ptt.cc", "://www.ptt.cc")

    return {"url": url, "headers": headers, "cookies": cookies}


# ---------------------------------------------------------------------------
# Threads extraction (jmespath)
# ---------------------------------------------------------------------------

def _parse_thread_item(item: dict) -> dict | None:
    """Extract structured data from a single thread_item using jmespath."""
    result = jmespath.search(
        """{
        text: post.caption.text,
        published_on: post.taken_at,
        id: post.id,
        pk: post.pk,
        code: post.code,
        username: post.user.username,
        user_pic: post.user.profile_pic_url,
        user_verified: post.user.is_verified,
        like_count: post.like_count,
        images: post.carousel_media[].image_versions2.candidates[1].url,
        videos: post.video_versions[].url
    }""",
        item,
    )
    if not result or not result.get("text"):
        return None

    result["text"] = result["text"].replace("\\n", "\n").strip()
    result["videos"] = list(set(result["videos"] or []))
    result["images"] = result["images"] or []

    if result.get("published_on"):
        try:
            result["published_on"] = datetime.fromtimestamp(
                int(result["published_on"])
            ).isoformat()
        except (ValueError, OSError):
            pass

    if result.get("username") and result.get("code"):
        result["url"] = f"https://www.threads.net/@{result['username']}/post/{result['code']}"

    return result


def _parse_profile(user_data: dict) -> dict | None:
    return jmespath.search(
        """{
        is_private: text_post_app_is_private,
        is_verified: is_verified,
        profile_pic: hd_profile_pic_versions[-1].url,
        username: username,
        full_name: full_name,
        bio: biography,
        followers: follower_count
    }""",
        user_data,
    )


def _extract_threads_regex_fallback(scripts) -> list:
    """Regex fallback when jmespath extraction fails."""
    posts = []
    seen = set()
    for script in scripts:
        content = script.text
        if len(content) < 500:
            continue
        try:
            texts = re.findall(r'"text":\s*"([^"]{10,})"', content)
            usernames = re.findall(r'"username":\s*"([^"]+)"', content)
            timestamps = re.findall(r'"taken_at":\s*(\d+)', content)
            for i, text in enumerate(texts):
                text_clean = text.replace("\\n", "\n").strip()
                if text_clean in seen or len(text_clean) < 15:
                    continue
                seen.add(text_clean)
                post = {"text": text_clean}
                if i < len(usernames):
                    post["username"] = usernames[i]
                if i < len(timestamps):
                    try:
                        post["published_on"] = datetime.fromtimestamp(
                            int(timestamps[i])
                        ).isoformat()
                    except (ValueError, OSError):
                        pass
                posts.append(post)
        except Exception:
            continue
    return posts


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def scrape_threads(url: str, timeout: int = 30, delay: bool = True) -> dict:
    """
    Scrape a Threads profile or post URL.

    Returns dict with: profile_summary, profile, posts_found, posts, extraction_method
    """
    from scrapling import StealthyFetcher

    if delay:
        _random_delay()

    fetch_kwargs = {
        "timeout": timeout * 1000,
        "wait_selector": "[data-pressable-container]",
        "wait_time": 5,
    }
    page = StealthyFetcher.fetch(url, **fetch_kwargs)

    scripts = page.css("script[data-sjs]")
    posts = []
    seen_texts = set()
    profile = None

    for script in scripts:
        content = script.text
        if len(content) < 500 or '"ScheduledServerJS"' not in content:
            continue

        try:
            data = json.loads(content)
        except (json.JSONDecodeError, Exception):
            continue

        if "thread_items" in content:
            for items in nested_lookup("thread_items", data):
                if not isinstance(items, list):
                    continue
                for item in items:
                    parsed = _parse_thread_item(item)
                    if not parsed or parsed["text"] in seen_texts or len(parsed["text"]) < 15:
                        continue
                    seen_texts.add(parsed["text"])
                    posts.append(parsed)

        if not profile and "user" in content:
            try:
                for u in nested_lookup("user", data):
                    if isinstance(u, dict) and "username" in u:
                        profile = _parse_profile(u)
                        if profile and profile.get("username"):
                            break
            except Exception:
                pass

    # Fallback
    if not posts:
        posts = _extract_threads_regex_fallback(scripts)

    og_desc = page.css('meta[property="og:description"]')
    profile_summary = og_desc[0].attrib.get("content", "") if og_desc else ""

    result = {
        "profile_summary": profile_summary,
        "posts_found": len(posts),
        "posts": posts[:20],
        "extraction_method": "jmespath" if posts else "none",
    }
    if profile:
        result["profile"] = profile
    return result


def scrape_reddit(url: str, timeout: int = 15, delay: bool = True) -> dict:
    """Scrape a Reddit URL. Returns parsed JSON or text content."""
    if delay:
        _random_delay()

    req = _prepare_request(url)
    final_url = req["url"]

    try:
        page = Fetcher.get(
            final_url, timeout=timeout, headers=req["headers"],
            stealthy_headers=False, follow_redirects=True,
        )
        body = page.html_content if hasattr(page, "html_content") else str(page)
        if "<" in body:
            body = re.sub(r"<[^>]+>", "", body).strip()
        data = json.loads(body)
        return {"source": "reddit", "url": url, "data": data}
    except (json.JSONDecodeError, Exception):
        # Fallback to HTML
        fallback_url = final_url.replace(".json", "") if final_url.endswith(".json") else final_url
        page = Fetcher.get(
            fallback_url, timeout=timeout, headers=_base_headers(fallback_url),
            stealthy_headers=False, follow_redirects=True,
        )
        body = page.css("body")
        text = body[0].text.strip() if body else ""
        lines = [l.strip() for l in text.split("\n") if l.strip()]
        return {"source": "reddit", "url": url, "text": "\n".join(lines[:200])}


def scrape_ptt(url: str, timeout: int = 15, delay: bool = True) -> dict:
    """Scrape a PTT URL with over18 cookie."""
    if delay:
        _random_delay()

    req = _prepare_request(url)
    page = Fetcher.get(
        req["url"], timeout=timeout, headers=req["headers"],
        cookies=req["cookies"], stealthy_headers=False, follow_redirects=True,
    )
    body = page.css("body")
    text = body[0].text.strip() if body else ""
    lines = [l.strip() for l in text.split("\n") if l.strip()]
    return {"source": "ptt", "url": url, "text": "\n".join(lines[:200])}


def scrape(url: str, timeout: int = 30, delay: bool = True, raw: bool = False) -> dict:
    """
    Auto-detect site and scrape accordingly.

    Args:
        url: Target URL
        timeout: Request timeout in seconds
        delay: Add random delay before request (anti rate-limit)
        raw: Return raw HTML instead of parsed content

    Returns:
        Dict with scraped content (structure varies by site)
    """
    host = urlparse(url).netloc.lower()

    # Threads
    if "threads.net" in host or "threads.com" in host:
        return scrape_threads(url, timeout=timeout, delay=delay)

    # Reddit
    if "reddit.com" in host:
        return scrape_reddit(url, timeout=timeout, delay=delay)

    # PTT
    if "ptt.cc" in host:
        return scrape_ptt(url, timeout=timeout, delay=delay)

    # Generic
    if delay:
        _random_delay()

    req = _prepare_request(url)
    page = Fetcher.get(
        req["url"], timeout=timeout, headers=req["headers"],
        cookies=req["cookies"] if req["cookies"] else None,
        stealthy_headers=False, follow_redirects=True,
    )

    if raw:
        return {"source": "generic", "url": url, "html": page.html_content if hasattr(page, "html_content") else str(page)}

    body = page.css("body")
    text = body[0].text.strip() if body else ""
    lines = [l.strip() for l in text.split("\n") if l.strip()]
    return {"source": "generic", "url": url, "text": "\n".join(lines[:200])}
