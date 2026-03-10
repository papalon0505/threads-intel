"""Example: Scrape any URL and analyze with LLM."""

import os
from threads_intel import scrape, analyze

# Scrape
result = scrape("https://old.reddit.com/r/LocalLLaMA")
content = result.get("text") or str(result.get("data", ""))

# Analyze
api_key = os.environ["MINIMAX_API_KEY"]
report = analyze(content, api_key=api_key, url="https://reddit.com/r/LocalLLaMA")

if report["error"]:
    print(f"Error: {report['error']}")
else:
    print(report["analysis"])
