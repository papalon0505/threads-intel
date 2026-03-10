"""
CLI entry point for threads-intel.

Usage:
    threads-intel scrape <url> [options]
    threads-intel analyze <url> [options]
"""

import argparse
import json
import os
import sys
import time

from .scraper import scrape
from .analyzer import analyze


def main():
    parser = argparse.ArgumentParser(
        prog="threads-intel",
        description="Scrape social platforms and analyze with LLM",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # --- scrape ---
    sp_scrape = subparsers.add_parser("scrape", help="Scrape a URL")
    sp_scrape.add_argument("url", help="Target URL")
    sp_scrape.add_argument("--timeout", type=int, default=30, help="Timeout in seconds")
    sp_scrape.add_argument("--no-delay", action="store_true", help="Skip random delay")
    sp_scrape.add_argument("--raw", action="store_true", help="Output raw HTML")
    sp_scrape.add_argument("--json", action="store_true", help="JSON output")

    # --- analyze ---
    sp_analyze = subparsers.add_parser("analyze", help="Scrape + LLM analysis")
    sp_analyze.add_argument("url", help="Target URL")
    sp_analyze.add_argument("--timeout", type=int, default=30, help="Scrape timeout")
    sp_analyze.add_argument("--no-delay", action="store_true", help="Skip random delay")
    sp_analyze.add_argument("--prompt", help="Custom analysis prompt")
    sp_analyze.add_argument("--api-key", help="LLM API key (prefer MINIMAX_API_KEY env var for security)")
    sp_analyze.add_argument("--api-url", default="https://api.minimax.io/v1/chat/completions", help="LLM API endpoint")
    sp_analyze.add_argument("--model", default="MiniMax-M2.5", help="LLM model name")
    sp_analyze.add_argument("--json", action="store_true", help="JSON output")

    args = parser.parse_args()

    if args.command == "scrape":
        result = scrape(
            args.url,
            timeout=args.timeout,
            delay=not args.no_delay,
            raw=args.raw,
        )
        if args.json:
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            # Pretty print based on source type
            if "posts" in result:
                print(f"Profile: {result.get('profile_summary', '')}")
                if result.get("profile"):
                    p = result["profile"]
                    print(f"@{p.get('username', '?')} | {p.get('followers', '?')} followers")
                print(f"Posts found: {result['posts_found']}\n")
                for post in result["posts"]:
                    print(f"@{post.get('username', '?')}: {post['text'][:120]}")
                    meta = []
                    if post.get("like_count"):
                        meta.append(f"likes:{post['like_count']}")
                    if post.get("published_on"):
                        meta.append(post["published_on"])
                    if meta:
                        print(f"  [{' | '.join(meta)}]")
                    print()
            elif "text" in result:
                print(result["text"])
            elif "html" in result:
                print(result["html"][:5000])
            elif "data" in result:
                print(json.dumps(result["data"], ensure_ascii=False, indent=2)[:5000])

    elif args.command == "analyze":
        # Scrape
        scraped = scrape(args.url, timeout=args.timeout, delay=not args.no_delay)

        # Extract text content for analysis
        if "posts" in scraped:
            content = json.dumps(scraped, ensure_ascii=False)
        elif "text" in scraped:
            content = scraped["text"]
        elif "data" in scraped:
            content = json.dumps(scraped["data"], ensure_ascii=False)
        else:
            print("Error: no content scraped", file=sys.stderr)
            sys.exit(1)

        # Get API key
        api_key = args.api_key or os.environ.get("MINIMAX_API_KEY")
        if not api_key:
            print("Error: set MINIMAX_API_KEY or use --api-key", file=sys.stderr)
            sys.exit(1)

        # Analyze
        t0 = time.time()
        result = analyze(
            content,
            api_key=api_key,
            url=args.url,
            prompt=args.prompt,
            api_url=args.api_url,
            model=args.model,
        )
        elapsed = time.time() - t0

        if result["error"]:
            print(f"Error: {result['error']}", file=sys.stderr)
            sys.exit(1)

        if args.json:
            result["elapsed_seconds"] = round(elapsed, 2)
            result["content_length"] = len(content)
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            print(f"[{result['model']} | {elapsed:.1f}s]\n")
            print(result["analysis"])


if __name__ == "__main__":
    main()
