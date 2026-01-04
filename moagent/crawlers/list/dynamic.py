"""
Dynamic list crawler - extracts article links from JavaScript-rendered pages.

This uses Playwright to handle JavaScript-heavy list pages.
"""

import logging
from typing import List, Dict, Any
from datetime import datetime

from .base import BaseListCrawler

logger = logging.getLogger(__name__)


class DynamicListCrawler(BaseListCrawler):
    """
    Dynamic list crawler for JavaScript-rendered list pages.

    Features:
    - Uses Playwright for full JavaScript rendering
    - Handles SPAs and dynamic content loading
    - Extracts links after page fully loads

    Returns:
        List of {title, url, content="", timestamp, source, type}
    """

    def __init__(self, config):
        super().__init__(config)
        self._playwright = None
        self._browser = None

    def crawl(self) -> List[Dict[str, Any]]:
        """Extract article links from dynamic list page."""
        if not self.config.target_url:
            logger.warning("No target URL configured")
            return []

        logger.info(f"Dynamic list crawling: {self.config.target_url}")

        try:
            self._init_playwright()
            return self._crawl_with_playwright()

        except Exception as e:
            logger.error(f"Dynamic crawling failed: {e}")
            return []
        finally:
            self._cleanup()

    def _init_playwright(self) -> None:
        """Initialize Playwright browser."""
        try:
            from playwright.sync_api import sync_playwright

            self._playwright = sync_playwright().start()
            self._browser = self._playwright.chromium.launch(
                headless=True,
                args=['--no-sandbox', '--disable-dev-shm-usage']
            )
            logger.debug("Playwright initialized")
        except Exception as e:
            logger.error(f"Failed to initialize Playwright: {e}")
            raise

    def _crawl_with_playwright(self) -> List[Dict[str, Any]]:
        """Crawl using Playwright."""
        if not self._browser:
            raise RuntimeError("Browser not initialized")

        page = self._browser.new_page(
            viewport={'width': 1920, 'height': 1080},
            user_agent=self.headers.get('User-Agent', '')
        )

        try:
            # Navigate to page
            page.goto(
                self.config.target_url,
                wait_until='networkidle',
                timeout=self.config.timeout * 1000
            )

            # Wait for content to load
            page.wait_for_timeout(2000)

            # Get page content
            html_content = page.content()
            current_url = page.url

            # Extract articles
            items = self._extract_articles_dynamic(page)

            # Fallback to HTML parsing if no items found
            if not items:
                from bs4 import BeautifulSoup
                from urllib.parse import urljoin

                soup = BeautifulSoup(html_content, 'lxml')
                links = self._extract_links(html_content, current_url)

                for link in links[:20]:
                    items.append({
                        "title": f"Article from {link}",
                        "url": link,
                        "content": "",
                        "timestamp": datetime.now().isoformat(),
                        "source": self.config.target_url,
                        "type": "dynamic"
                    })

            # Apply post-processing filters if configured
            if hasattr(self.config, 'crawler_patterns') and self.config.crawler_patterns:
                post_process = self.config.crawler_patterns.get('post_process', {})
                if post_process:
                    items = self._apply_post_processing_filters(items, post_process)

            logger.info(f"Dynamic crawling: {len(items)} items")
            return items

        except Exception as e:
            logger.error(f"Playwright crawling error: {e}")
            return []

    def _extract_articles_dynamic(self, page) -> List[Dict[str, Any]]:
        """Extract articles using Playwright page context."""
        items = []

        # Try to find common article containers
        selectors = [
            'div.news-list', 'div.article-list', 'div.news-item', 'div.article-item',
            'li.news', 'li.article', 'div.list-item', 'article',
            'a[href*="news"]', 'a[href*="article"]'
        ]

        for selector in selectors:
            try:
                elements = page.query_selector_all(selector)
                if elements:
                    for elem in elements[:20]:
                        item = self._extract_item_from_element(elem, page)
                        if item:
                            items.append(item)
                    if items:
                        break
            except Exception:
                continue

        return items

    def _extract_item_from_element(self, element, page) -> Dict[str, Any]:
        """Extract item data from a Playwright element."""
        try:
            # Get title
            title_elem = element.query_selector('h1, h2, h3, h4, a')
            title = title_elem.text_content().strip() if title_elem else "No title"

            # Get link
            link_elem = element.query_selector('a')
            url = link_elem.get_attribute('href') if link_elem else ""

            # Get date
            date_elem = element.query_selector('time, .date, .time')
            timestamp = date_elem.text_content().strip() if date_elem else datetime.now().isoformat()

            return self._normalize_item({
                "title": title,
                "url": url,
                "content": "",
                "timestamp": timestamp,
                "source": self.config.target_url,
                "type": "dynamic"
            })

        except Exception as e:
            logger.debug(f"Failed to extract item: {e}")
            return {}

    def _apply_post_processing_filters(self, items: List[Dict[str, Any]], post_process: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Apply post-processing filters to clean up extracted items.
        
        Supported filters:
        - exclude_url_patterns: List of strings to match in URL (substring match)
        - exclude_url_regex: List of regex patterns to match against URL
        - exclude_titles: List of exact title strings to exclude
        - exclude_titles_like: List of substrings to match in title
        - exclude_title_regex: List of regex patterns to match against title
        - min_title_length: Minimum title length
        - require_title: Whether title is required
        """
        if not post_process:
            return items

        filtered = []
        import re

        # URL pattern exclusions (substring match)
        exclude_url_patterns = post_process.get("exclude_url_patterns", [])
        # URL regex exclusions
        exclude_url_regex = post_process.get("exclude_url_regex", [])
        # Compile regex patterns for URL
        url_regex_patterns = []
        for pattern_str in exclude_url_regex:
            try:
                url_regex_patterns.append(re.compile(pattern_str, re.IGNORECASE))
            except re.error as e:
                logger.warning(f"Invalid URL regex pattern '{pattern_str}': {e}")
        
        # Title exclusions
        exclude_titles = post_process.get("exclude_titles", [])
        exclude_titles_like = post_process.get("exclude_titles_like", [])
        # Title regex exclusions
        exclude_title_regex = post_process.get("exclude_title_regex", [])
        # Compile regex patterns for title
        title_regex_patterns = []
        for pattern_str in exclude_title_regex:
            try:
                title_regex_patterns.append(re.compile(pattern_str, re.IGNORECASE))
            except re.error as e:
                logger.warning(f"Invalid title regex pattern '{pattern_str}': {e}")
        
        min_title_length = post_process.get("min_title_length", 0)
        require_title = post_process.get("require_title", False)

        for item in items:
            url = item.get("url", "")
            title = item.get("title", "").strip()
            url_lower = url.lower()
            title_lower = title.lower()

            skip = False

            # Check URL substring patterns
            for pattern in exclude_url_patterns:
                if pattern.lower() in url_lower:
                    skip = True
                    break
            if skip:
                continue

            # Check URL regex patterns
            for pattern in url_regex_patterns:
                if pattern.search(url):
                    skip = True
                    break
            if skip:
                continue

            # Check exact title exclusions
            if title in exclude_titles:
                continue

            # Check title-like exclusions (partial match)
            for exclude in exclude_titles_like:
                if exclude.lower() in title_lower:
                    skip = True
                    break
            if skip:
                continue

            # Check title regex patterns
            for pattern in title_regex_patterns:
                if pattern.search(title):
                    skip = True
                    break
            if skip:
                continue

            # Check minimum title length
            if min_title_length and len(title) < min_title_length:
                continue

            # Check require title
            if require_title and not title:
                continue

            filtered.append(item)

        return filtered

    def _cleanup(self) -> None:
        """Cleanup Playwright resources."""
        try:
            if self._browser:
                self._browser.close()
            if self._playwright:
                self._playwright.stop()
            logger.debug("Playwright cleaned up")
        except Exception as e:
            logger.warning(f"Cleanup warning: {e}")


__all__ = ["DynamicListCrawler"]