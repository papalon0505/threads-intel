"""
LLM analysis module — feed scraped content through LLM for structured reports.

Default backend: MiniMax M2.5
"""

import json
import re
import urllib.request

DEFAULT_PROMPT = """You are an intelligence analyst. Analyze the following web content and respond in the same language as the content:

1. **One-line summary** (under 30 characters)
2. **Key points** (3-5 bullet points)
3. **Investment/tech relevance** (if any)
4. **Credibility assessment** (high/medium/low with brief reason)
5. **Suggested action** (worth deep dive? track? ignore?)

Be concise. No filler."""

THREADS_PROMPT = """You are an intelligence analyst. Analyze the following Threads account posts and respond in the same language as the content:

1. **Account positioning** (what domain this person covers)
2. **Recent highlights** (3-5 most valuable insights with quotes)
3. **Relevance** (AI agent / investment / tools / none)
4. **Worth following?** (yes/no with reason)
5. **Actionable items** (tools/methods/links worth investigating)

Be concise. No filler."""


def _clean_think_tags(text: str) -> str:
    """Remove leaked <think>...</think> tags from MiniMax output."""
    return re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL).strip()


def analyze(
    content: str,
    api_key: str,
    url: str = "",
    prompt: str | None = None,
    api_url: str = "https://api.minimax.io/v1/chat/completions",
    model: str = "MiniMax-M2.5",
    max_tokens: int = 800,
    timeout: int = 60,
) -> dict:
    """
    Analyze content using LLM.

    Args:
        content: Text content to analyze
        api_key: LLM API key
        url: Source URL (for context)
        prompt: Custom system prompt (auto-detected if None)
        api_url: LLM API endpoint
        model: Model name
        max_tokens: Max response tokens
        timeout: Request timeout

    Returns:
        dict with: analysis, error, model, url
    """
    is_threads = "threads.net" in url or "threads.com" in url
    system_prompt = prompt or (THREADS_PROMPT if is_threads else DEFAULT_PROMPT)

    if len(content) > 6000:
        content = content[:6000] + "\n\n... (truncated)"

    body = json.dumps({
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"URL: {url}\n\n{content}"},
        ],
        "max_tokens": max_tokens,
        "temperature": 0.3,
        "stream": False,
    }).encode("utf-8")

    req = urllib.request.Request(
        api_url,
        data=body,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            text = data["choices"][0]["message"]["content"]
            return {
                "analysis": _clean_think_tags(text),
                "error": None,
                "model": model,
                "url": url,
            }
    except urllib.error.HTTPError as e:
        err_body = e.read().decode("utf-8", errors="replace")[:200]
        return {"analysis": None, "error": f"API error {e.code}: {err_body}", "model": model, "url": url}
    except Exception as e:
        return {"analysis": None, "error": str(e), "model": model, "url": url}
