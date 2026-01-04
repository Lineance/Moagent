"""
RSS list crawler - extracts article links from RSS/Atom feeds.

This is optimized for RSS feed parsing and link extraction.
"""

import logging
from typing import List, Dict, Any
from datetime import datetime

from .base import BaseListCrawler

logger = logging.getLogger(__name__)


class RSSListCrawler(BaseListCrawler):
    """
    RSS list crawler for extracting article links from RSS/Atom feeds.

    Features:
    - Fast feed parsing with feedparser
    - Handles RSS and Atom formats
    - Extracts publication dates
    - Minimal processing overhead

    Returns:
        List of {title, url, content="", timestamp, source, type}
    """

    def crawl(self) -> List[Dict[str, Any]]:
        """Extract article links from RSS feed."""
        if not self.config.target_url:
            logger.warning("No target URL configured")
            return []

        logger.info(f"RSS list crawling: {self.config.target_url}")

        try:
            import feedparser

            feed = feedparser.parse(self.config.target_url)

            items = []
            for entry in feed.entries:
                item = {
                    "title": entry.get("title", "No title"),
                    "url": entry.get("link", ""),
                    "content": "",  # Always empty - we only extract links
                    "timestamp": entry.get("published", datetime.now().isoformat()),
                    "source": self.config.target_url,
                    "type": "rss",
                    "raw": dict(entry)
                }
                items.append(self._normalize_item(item))

            logger.info(f"RSS feed parsed: {len(items)} items")
            return items

        except Exception as e:
            logger.error(f"RSS parsing failed: {e}")
            return []


__all__ = ["RSSListCrawler"]