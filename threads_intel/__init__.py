"""threads-intel — Scrape social platforms and analyze with LLM."""

__version__ = "0.1.0"

from .scraper import scrape, scrape_threads, scrape_reddit, scrape_ptt
from .analyzer import analyze

__all__ = ["scrape", "scrape_threads", "scrape_reddit", "scrape_ptt", "analyze"]
