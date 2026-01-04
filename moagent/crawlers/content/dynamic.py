"""
Dynamic fulltext crawler - extracts complete article content from JavaScript-rendered pages.

This uses Playwright to handle JavaScript-heavy article pages and extract
complete content after full page rendering.
"""

import logging
from typing import Dict, Any, Optional
from datetime import datetime

from .base import BaseFullTextCrawler

logger = logging.getLogger(__name__)


class DynamicFullTextCrawler(BaseFullTextCrawler):
    """
    Dynamic fulltext crawler for JavaScript-rendered article pages.

    Features:
    - Uses Playwright for full JavaScript rendering
    - Handles SPAs and dynamic content loading
    - Extracts complete article content after page loads
    - Supports rich content (images, videos, embedded media)

    Returns:
        Dictionary with full article data:
        - title: Article title
        - url: Article URL
        - content: Full article text/content
        - timestamp: Publication date
        - author: Article author (if available)
        - category: Category/tags (if available)
        - source: Source URL
        - type: Content type (dynamic)
        - metadata: Additional metadata dict
        - raw: Raw content for debugging
    """

    def __init__(self, config):
        super().__init__(config)
        self._playwright = None
        self._browser = None

    def crawl(self, url: str) -> Optional[Dict[str, Any]]:
        """
        Extract complete article content from dynamic page.

        Args:
            url: Article URL to crawl

        Returns:
            Dictionary with full article data or None if failed
        """
        if not url:
            logger.warning("No URL provided")
            return None

        logger.info(f"Dynamic fulltext crawling: {url}")

        try:
            self._init_playwright()
            return self._crawl_with_playwright(url)

        except Exception as e:
            logger.error(f"Dynamic fulltext crawling failed: {e}")
            return None
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
            logger.debug("Playwright initialized for fulltext crawling")
        except Exception as e:
            logger.error(f"Failed to initialize Playwright: {e}")
            raise

    def _crawl_with_playwright(self, url: str) -> Optional[Dict[str, Any]]:
        """
        Crawl article using Playwright with full content extraction.

        Args:
            url: Article URL

        Returns:
            Article data dictionary or None
        """
        if not self._browser:
            raise RuntimeError("Browser not initialized")

        page = self._browser.new_page(
            viewport={'width': 1920, 'height': 1080},
            user_agent=self.headers.get('User-Agent', '')
        )

        try:
            # Navigate to page
            page.goto(
                url,
                wait_until='networkidle',
                timeout=self.content_timeout * 1000
            )

            # Wait for content to load (dynamic content)
            page.wait_for_timeout(3000)

            # Try to scroll to load more content
            self._scroll_to_load_content(page)

            # Get page content
            html_content = page.content()
            current_url = page.url

            # Extract article data using multiple strategies
            article_data = self._extract_article_dynamic(page, html_content, current_url)

            if article_data:
                # Add raw content for debugging
                article_data["raw"] = html_content[:1000] if len(html_content) > 1000 else html_content
                logger.info(f"Successfully extracted article: {article_data.get('title', 'Unknown')[:50]}...")
                return article_data
            else:
                logger.warning(f"Failed to extract article content from {url}")
                return None

        except Exception as e:
            logger.error(f"Playwright fulltext crawling error: {e}")
            return None

    def _scroll_to_load_content(self, page) -> None:
        """Scroll page to load dynamic content."""
        try:
            # Scroll down to load lazy content
            page.evaluate("""
                window.scrollTo(0, document.body.scrollHeight);
            """)
            page.wait_for_timeout(1000)

            # Scroll back to top
            page.evaluate("""
                window.scrollTo(0, 0);
            """)
            page.wait_for_timeout(500)
        except Exception as e:
            logger.debug(f"Scroll loading failed: {e}")

    def _extract_article_dynamic(self, page, html_content: str, url: str) -> Optional[Dict[str, Any]]:
        """
        Extract article data using Playwright page context.

        Args:
            page: Playwright page object
            html_content: Page HTML content
            url: Article URL

        Returns:
            Article data dictionary or None
        """
        # Strategy 1: Try to find main article content using common selectors
        article_data = self._extract_with_selectors(page, url)
        if article_data and self._is_quality_article(article_data):
            return article_data

        # Strategy 2: Try pattern-based extraction with HTML content
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html_content, 'lxml')

        # Try predefined patterns
        if hasattr(self.config, 'article_link_patterns') and self.config.article_link_patterns:
            for pattern_config in self.config.article_link_patterns:
                patterns = pattern_config.get('patterns', {})
                if patterns:
                    article_data = self._extract_with_patterns(html_content, url, patterns)
                    if article_data and self._is_quality_article(article_data):
                        return article_data

        # Strategy 3: Try structured data extraction
        article_data = self._extract_with_structured_data(html_content, url)
        if article_data and self._is_quality_article(article_data):
            return article_data

        # Strategy 4: Fallback to basic extraction
        return self._extract_basic_article(page, url)

    def _extract_with_selectors(self, page, url: str) -> Optional[Dict[str, Any]]:
        """
        Extract article using common Playwright selectors.

        Args:
            page: Playwright page object
            url: Article URL

        Returns:
            Article data dictionary or None
        """
        try:
            # Try to find title
            title_selectors = [
                'h1', 'h1.title', 'h1.article-title', 'h1.entry-title',
                '.title', '.article-title', '.entry-title', '.headline',
                'title'
            ]

            title = None
            for selector in title_selectors:
                try:
                    elem = page.query_selector(selector)
                    if elem:
                        title = elem.text_content().strip()
                        if title and len(title) > 3:
                            break
                except:
                    continue

            # Try to find main content
            content_selectors = [
                'article', '.article-content', '.entry-content', '.post-content',
                '.content', '.main-content', '.article-body', '.entry-body',
                '[class*="content"]', '[class*="article"]', '[class*="post"]'
            ]

            content = None
            for selector in content_selectors:
                try:
                    elem = page.query_selector(selector)
                    if elem:
                        # Remove unwanted elements
                        page.evaluate("""
                            (selector) => {
                                const element = document.querySelector(selector);
                                if (element) {
                                    // Remove scripts, styles, navigation
                                    element.querySelectorAll('script, style, nav, header, footer, aside, .ads, .advertisement').forEach(el => el.remove());
                                    return element.textContent || element.innerText || '';
                                }
                                return '';
                            }
                        """, selector)
                        content = elem.text_content().strip()
                        if content and len(content) > 50:
                            break
                except:
                    continue

            # Try to find metadata
            timestamp = self._extract_timestamp(page)
            author = self._extract_author(page)
            category = self._extract_category(page)

            if title or content:
                return self._normalize_item({
                    "title": title or "Untitled Article",
                    "url": url,
                    "content": content or "",
                    "timestamp": timestamp,
                    "author": author,
                    "category": category,
                    "source": url,
                    "type": "dynamic",
                    "metadata": {
                        "extraction_method": "playwright_selectors",
                        "dynamic": True
                    }
                })

        except Exception as e:
            logger.debug(f"Selector extraction failed: {e}")

        return None

    def _extract_timestamp(self, page) -> str:
        """Extract timestamp using Playwright."""
        timestamp_selectors = [
            'time', '.date', '.time', '.published', '.post-date',
            '[datetime]', '[class*="date"]', '[class*="time"]'
        ]

        for selector in timestamp_selectors:
            try:
                elem = page.query_selector(selector)
                if elem:
                    # Try datetime attribute first
                    datetime_attr = elem.get_attribute('datetime')
                    if datetime_attr:
                        return datetime_attr

                    # Try text content
                    text = elem.text_content().strip()
                    if text:
                        return text
            except:
                continue

        # Fallback to current time
        return datetime.now().isoformat()

    def _extract_author(self, page) -> str:
        """Extract author using Playwright."""
        author_selectors = [
            '.author', '.byline', '.writer', '.post-author',
            '[class*="author"]', '[rel="author"]', '.meta-author'
        ]

        for selector in author_selectors:
            try:
                elem = page.query_selector(selector)
                if elem:
                    text = elem.text_content().strip()
                    if text and len(text) < 100:  # Reasonable author name length
                        return text
            except:
                continue

        return ""

    def _extract_category(self, page) -> str:
        """Extract category using Playwright."""
        category_selectors = [
            '.category', '.tag', '.topic', '.section',
            '[class*="category"]', '[class*="tag"]'
        ]

        categories = []
        for selector in category_selectors:
            try:
                elems = page.query_selector_all(selector)
                for elem in elems[:3]:  # Limit to first 3 categories
                    text = elem.text_content().strip()
                    if text and len(text) < 50:
                        categories.append(text)
            except:
                continue

        return ', '.join(categories) if categories else ""

    def _extract_basic_article(self, page, url: str) -> Optional[Dict[str, Any]]:
        """
        Basic article extraction as last resort.

        Args:
            page: Playwright page object
            url: Article URL

        Returns:
            Basic article data
        """
        try:
            # Get all visible text
            visible_text = page.evaluate("""
                () => {
                    const elements = document.querySelectorAll('p, h1, h2, h3, h4, h5, h6, div, span');
                    let text = '';
                    for (const elem of elements) {
                        const style = window.getComputedStyle(elem);
                        if (style.display !== 'none' && style.visibility !== 'hidden' &&
                            elem.textContent && elem.textContent.trim().length > 10) {
                            text += elem.textContent.trim() + '\\n\\n';
                        }
                    }
                    return text.substring(0, 10000); // Limit length
                }
            """)

            if visible_text and len(visible_text.strip()) > 100:
                # Try to extract title from the beginning
                lines = visible_text.split('\n')
                title = lines[0].strip() if lines else "Dynamic Article"

                return self._normalize_item({
                    "title": title,
                    "url": url,
                    "content": visible_text.strip(),
                    "timestamp": datetime.now().isoformat(),
                    "author": "",
                    "category": "",
                    "source": url,
                    "type": "dynamic",
                    "metadata": {
                        "extraction_method": "basic_dynamic",
                        "dynamic": True
                    }
                })

        except Exception as e:
            logger.debug(f"Basic extraction failed: {e}")

        return None

    def _is_quality_article(self, article_data: Dict[str, Any]) -> bool:
        """
        Check if extracted article data is of sufficient quality.

        Args:
            article_data: Extracted article data

        Returns:
            True if quality is sufficient
        """
        content = article_data.get('content', '').strip()
        title = article_data.get('title', '').strip()

        # Must have some content
        if not content or len(content) < 50:
            return False

        # Title should be reasonable
        if not title or len(title) < 3 or title == "Untitled Article":
            return False

        # Content should be substantial
        if len(content) < 100:
            return False

        return True

    def _cleanup(self) -> None:
        """Cleanup Playwright resources."""
        try:
            if self._browser:
                self._browser.close()
            if self._playwright:
                self._playwright.stop()
            logger.debug("Playwright cleaned up for fulltext crawler")
        except Exception as e:
            logger.warning(f"Cleanup warning: {e}")


__all__ = ["DynamicFullTextCrawler"]
