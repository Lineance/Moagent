"""
Base class for list crawlers - crawlers that only extract article links.

All crawlers in this folder should inherit from BaseListCrawler and
focus ONLY on extracting article URLs from list pages, NOT fetching
full article content.
"""

import logging
from abc import ABC, abstractmethod
from typing import List, Dict, Any
from urllib.parse import urljoin

from ...config.settings import Config
from ..base import BaseCrawler

logger = logging.getLogger(__name__)


class BaseListCrawler(BaseCrawler):
    """
    Abstract base class for list crawlers.

    All list crawlers should:
    1. Extract article links from list pages (RSS, HTML, etc.)
    2. Return {title, url, content=\"\"} dictionaries
    3. NOT fetch full article content
    4. Be fast and lightweight

    This separation of concerns allows for:
    - Faster crawling for link discovery
    - Independent optimization of list vs content extraction
    - Clear architecture boundaries
    """

    @abstractmethod
    def crawl(self) -> List[Dict[str, Any]]:
        """
        Extract article links from target URL.

        Returns:
            List of dictionaries with keys: title, url, content=\"\", timestamp, source, type
        """
        pass

    def _extract_links(self, html: str, base_url: str) -> List[str]:
        """Extract all links from HTML content."""
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(html, 'lxml')
        links = []

        for link in soup.find_all('a', href=True):
            href = link['href']
            if href.startswith(('http://', 'https://')):
                links.append(href)
            elif href.startswith('/'):
                links.append(urljoin(base_url, href))
            elif not href.startswith(('#', 'javascript:', 'mailto:')):
                links.append(urljoin(base_url, href))

        return list(set(links))

    def _normalize_item(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize a crawled item."""
        if "title" not in item:
            item["title"] = "Untitled"
        if "url" not in item:
            item["url"] = ""
        item["content"] = ""  # Always empty for list crawlers
        if "timestamp" not in item:
            from datetime import datetime
            item["timestamp"] = datetime.now().isoformat()
        if "type" not in item:
            item["type"] = "unknown"

        # Clean whitespace
        if isinstance(item.get("title"), str):
            item["title"] = item["title"].strip()

        return item

    def _is_rss_feed(self, url: str) -> bool:
        """Check if URL is an RSS feed."""
        rss_indicators = ['rss', 'feed', 'xml']
        return any(indicator in url.lower() for indicator in rss_indicators)

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(config={self.config.target_url})"


__all__ = ["BaseListCrawler"]