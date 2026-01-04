"""
Base crawler class defining the interface for all crawlers.
"""

import logging
from abc import ABC, abstractmethod
from typing import List, Dict, Any

from ...config.settings import Config

logger = logging.getLogger(__name__)


class BaseCrawler(ABC):
    """Abstract base class for all crawlers."""

    def __init__(self, config: Config):
        """
        Initialize base crawler.

        Args:
            config: Configuration object
        """
        self.config = config
        self.headers = config.headers
        self.timeout = config.timeout
        self.max_retries = config.max_retries

    @abstractmethod
    def crawl(self) -> List[Dict[str, Any]]:
        """
        Crawl the target URL and return raw data.

        Returns:
            List of dictionaries containing raw crawled data
        """
        pass

    def _fetch_with_retry(self, url: str, **kwargs) -> Any:
        """
        Fetch URL with retry logic.

        Args:
            url: URL to fetch
            **kwargs: Additional arguments for fetch

        Returns:
            Response content
        """
        import time
        import requests

        for attempt in range(self.max_retries):
            try:
                response = requests.get(
                    url,
                    headers=self.headers,
                    timeout=self.timeout,
                    **kwargs
                )
                response.raise_for_status()
                return response
            except Exception as e:
                logger.warning(f"Attempt {attempt + 1} failed: {e}")
                if attempt < self.max_retries - 1:
                    time.sleep(2 ** attempt)  # Exponential backoff
                else:
                    raise

    def _extract_links(self, html: str, base_url: str) -> List[str]:
        """
        Extract links from HTML content.

        Args:
            html: HTML content as string
            base_url: Base URL for relative links

        Returns:
            List of absolute URLs
        """
        from urllib.parse import urljoin
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

    def _extract_text(self, html: str) -> str:
        """
        Extract clean text from HTML.

        Args:
            html: HTML content

        Returns:
            Clean text
        """
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(html, 'lxml')

        # Remove script and style elements
        for script in soup(["script", "style"]):
            script.decompose()

        # Get text
        text = soup.get_text(separator=' ', strip=True)
        return text

    def _normalize_item(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normalize a crawled item.

        Args:
            item: Raw item data

        Returns:
            Normalized item
        """
        # Ensure required fields
        if "title" not in item:
            item["title"] = "Untitled"
        if "url" not in item:
            item["url"] = ""
        # Content is always empty
        item["content"] = ""
        if "timestamp" not in item:
            from datetime import datetime
            item["timestamp"] = datetime.now().isoformat()
        # Default type if not set
        if "type" not in item:
            item["type"] = "unknown"

        # Clean whitespace
        if isinstance(item.get("title"), str):
            item["title"] = item["title"].strip()

        return item


__all__ = ["BaseCrawler"]