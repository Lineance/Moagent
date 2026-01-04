"""
Crawler module for fetching content from various sources.

This module provides multiple crawling strategies to fetch news content
from different types of sources with a clean, layered architecture.

Architecture:
    Separation of concerns for clarity and performance:

    BASE CLASSES (moagent.crawlers.base):
    - BaseCrawler: Core HTTP fetching, retry logic, utilities
    - BaseExtractor: Content extraction interface

    LIST CRAWLING (moagent.crawlers.list):
    - HTMLListCrawler: Static HTML pages
    - RSSListCrawler: RSS/Atom feeds
    - DynamicListCrawler: JavaScript-rendered pages
    - LLMListCrawler: LLM-powered intelligent extraction
    - HybridListCrawler: Traditional + LLM with fallback

    CONTENT CRAWLING (moagent.crawlers.content):
    - PatternFullTextCrawler: Pattern-based extraction (CSS/XPath/regex)
    - LLMFullTextCrawler: LLM-powered extraction
    - HybridFullTextCrawler: Pattern + LLM with intelligent fallback

    PIPELINE (moagent.crawlers.pipeline):
    - ListToFullTextCrawler: Complete pipeline (list → content)

Usage:
    # List crawling (extract article links)
    from moagent.crawlers import get_crawler, ListCrawler
    from moagent.config.settings import Config

    config = Config(target_url="https://example.com/news", crawl_mode="list")
    crawler = get_crawler(config)
    links = crawler.crawl()  # Returns {title, url, content=""}

    # Content crawling (extract full article)
    from moagent.crawlers.content import get_fulltext_crawler

    crawler = get_fulltext_crawler(config, mode="hybrid")
    article = crawler.crawl("https://example.com/article/123")

Factory Pattern:
    Use get_crawler(config) for list crawling
    Use get_fulltext_crawler(config, mode) for content extraction
"""

import logging
from typing import Any, Dict, List, Union

from ..config.settings import Config

logger = logging.getLogger(__name__)

# Import base classes
from .base import BaseCrawler

# Import content crawlers (for backward compatibility)
from .content import (
    BaseFullTextCrawler,
    HtmlTextCrawler,
    HybridFullTextCrawler,
    LLMFullTextCrawler,
    extract_fulltext,
    extract_fulltext_batch,
    get_fulltext_crawler,
)
from .list.dynamic import DynamicListCrawler

# Import list crawlers
from .list.html import HTMLListCrawler
from .list.llm import HybridListCrawler, LLMListCrawler
from .list.rss import RSSListCrawler


class ListCrawler(BaseCrawler):
    """
    Smart list crawler that automatically chooses the right list extractor.

    This router examines the target URL and automatically selects:
    - RSSListCrawler for RSS/Atom feeds
    - HTMLListCrawler for HTML pages
    - DynamicListCrawler can be used via 'dynamic' mode

    Returns:
        List of {title, url, content=""} dictionaries
    """

    def crawl(self) -> List[Dict[str, Any]]:
        if not self.config.target_url:
            logger.warning("No target URL configured")
            return []

        # Check for RSS
        if self._is_rss_feed(self.config.target_url):
            crawler = RSSListCrawler(self.config)
        else:
            # Use HTML crawler (handles auto rendering if needed)
            crawler = HTMLListCrawler(self.config)

        return crawler.crawl()

    def _is_rss_feed(self, url: str) -> bool:
        """Check if URL is an RSS feed."""
        rss_indicators = ['rss', 'feed', 'xml']
        return any(indicator in url.lower() for indicator in rss_indicators)


class AutoCrawler(BaseCrawler):
    """
    Auto mode crawler with intelligent fallback logic.

    This crawler implements a smart two-stage approach:
    1. First tries ListC (fast,, lightweight link extraction)
    2. If that fails or returns empty, falls back to DynamicListCrawler

    This provides the best balance of speed and reliability for most use cases.

    When to use:
        - Unknown target type
        - Mixed static/dynamic content
        - Want best performance with good reliability
    """

    def crawl(self) -> List[Dict[str, Any]]:
        if not self.config.target_url:
            logger.warning("No target URL configured")
            return []

        logger.info(f"Auto crawling: {self.config.target_url}")

        # Try list crawler first (fast, lightweight)
        list_crawler = ListCrawler(self.config)
        try:
            results = list_crawler.crawl()
            if results:
                logger.info(f"List crawler succeeded with {len(results)} items")
                return results
        except Exception as e:
            logger.warning(f"List crawler failed: {e}")

        # Fall back to dynamic list crawler (handles JS)
        logger.info("Falling back to dynamic list crawler...")
        dynamic_crawler = DynamicListCrawler(self.config)
        try:
            results = dynamic_crawler.crawl()
            logger.info(f"Dynamic crawler succeeded with {len(results)} items")
            return results
        except Exception as e:
            logger.error(f"Dynamic crawler also failed: {e}")
            return []


class FullCrawler(BaseCrawler):
    """
    Full pipeline crawler for testing convenience.

    This crawler combines list crawling and article crawling:
    1. Extracts article links from list page
    2. Visits each article to fetch full content
    3. Returns complete article data

    Use:
    - Testing the complete pipeline
    - One-shot full content extraction
    - Development and debugging

    Note: Slower than individual crawlers, but convenient for testing.
    """

    def crawl(self) -> List[Dict[str, Any]]:
        if not self.config.target_url:
            logger.warning("No target URL configured")
            return []

        logger.info(f"Full pipeline crawling: {self.config.target_url}")

        # Step 1: Extract article links
        list_crawler = ListCrawler(self.config)
        try:
            links = list_crawler.crawl()
            if not links:
                logger.warning("No article links found")
                return []
            logger.info(f"Found {len(links)} article links")
        except Exception as e:
            logger.error(f"List crawling failed: {e}")
            return []

        # Step 2: Fetch full content for each article
        from .content import get_fulltext_crawler
        article_crawler = get_fulltext_crawler(self.config, mode="hybrid")
        articles = []

        for i, link_item in enumerate(links[:self.config.max_articles]):
            article_url = link_item.get("url")
            if not article_url:
                continue

            try:
                article = article_crawler.crawl(article_url)
                if article:
                    # Preserve original list data if article crawler didn't get it
                    if not article.get("title"):
                        article["title"] = link_item.get("title", "Untitled")
                    if not article.get("timestamp"):
                        article["timestamp"] = link_item.get("timestamp")

                    articles.append(article)
                    logger.info(f"({i+1}/{len(links)}) Crawled: {article['title'][:50]}...")
                else:
                    logger.warning(f"Failed to crawl: {article_url}")
            except Exception as e:
                logger.warning(f"Error crawling {article_url}: {e}")
                continue

        logger.info(f"Full pipeline complete: {len(articles)} articles with content")
        return articles


def get_crawler(config: Config) -> BaseCrawler:
    """Factory function to get the appropriate crawler based on configuration.

    Args:
        config: Configuration object with crawl_mode setting

    Returns:
        BaseCrawler instance

    Raises:
        ValueError: If crawl_mode is not valid

    Mode Comparison:
        - list:     Fast link extraction, no content fetching
        - dynamic:  JavaScript support for dynamic list pages
        - auto:     Smart fallback (list → dynamic)
        - article:  Full content extraction from article pages
        - full:     Complete pipeline: list + article (for testing)
    """
    mode = config.crawl_mode

    if mode == "list":
        return ListCrawler(config)
    elif mode == "static":
        # Backward compatibility
        logger.warning("crawl_mode='static' is deprecated, use 'list' instead")
        return ListCrawler(config)
    elif mode == "dynamic":
        return DynamicListCrawler(config)
    elif mode == "auto":
        return AutoCrawler(config)
    elif mode == "article":
        # For article mode, use content crawler
        from .content import get_fulltext_crawler
        return get_fulltext_crawler(config, mode="hybrid")
    elif mode == "full":
        return FullCrawler(config)
    else:
        raise ValueError(f"Unknown crawl mode: {mode}")


__all__ = [
    # Base classes
    "BaseCrawler",
    "BaseFullTextCrawler",

    # List crawlers
    "ListCrawler",
    "HTMLListCrawler",
    "RSSListCrawler",
    "DynamicListCrawler",
    "LLMListCrawler",
    "HybridListCrawler",

    # Content crawlers
    "HtmlTextCrawler",
    "LLMFullTextCrawler",
    "HybridFullTextCrawler",

    # Pipeline crawlers
    "AutoCrawler",
    "FullCrawler",

    # Factory functions
    "get_crawler",
    "get_fulltext_crawler",
    "extract_fulltext",
    "extract_fulltext_batch",
]
