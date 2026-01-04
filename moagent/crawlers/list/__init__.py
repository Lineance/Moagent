"""List crawlers - extract article links from list pages.

This module provides crawlers that focus exclusively on discovering
and extracting article URLs from list pages (RSS feeds, HTML pages, etc.).
These crawlers return lightweight link data, NOT full article content.

Architecture:
    BaseListCrawler: Abstract base class for all list crawlers

    HTMLListCrawler: Static HTML pages with configurable patterns
    RSSListCrawler: RSS/Atom feed parsing
    DynamicListCrawler: JavaScript-rendered pages (Playwright)
    LLMListCrawler: LLM-powered intelligent extraction
    HybridListCrawler: Traditional + LLM with fallback

All crawlers return:
    List of {title, url, content="", timestamp, source, type}

Usage:
    from moagent.crawlers.list import HTMLListCrawler
    from moagent.config.settings import Config

    config = Config(target_url="https://example.com/news")
    crawler = HTMLListCrawler(config)
    links = crawler.crawl()
"""

from .base import BaseListCrawler
from .html import HTMLListCrawler
from .rss import RSSListCrawler
from .dynamic import DynamicListCrawler
from .llm import LLMListCrawler, HybridListCrawler
from .patterns import (
    ListPattern,
    PREDEFINED_PATTERNS,
    get_pattern,
    list_patterns,
    pattern_to_config,
    create_custom_pattern,
)

__all__ = [
    "BaseListCrawler",
    "HTMLListCrawler",
    "RSSListCrawler",
    "DynamicListCrawler",
    "LLMListCrawler",
    "HybridListCrawler",
    "ListPattern",
    "PREDEFINED_PATTERNS",
    "get_pattern",
    "list_patterns",
    "pattern_to_config",
    "create_custom_pattern",
]
