"""
Pattern-based fulltext crawler for extracting article content using configurable patterns.

This crawler uses CSS selectors, XPath, and regex patterns to extract structured
article content from HTML pages. It supports both user-defined patterns and
predefined patterns for common website structures.
"""

import logging
from typing import Any, Dict, List, Optional
from urllib.parse import urljoin

from .base import BaseFullTextCrawler

logger = logging.getLogger(__name__)


class HtmlTextCrawler(BaseFullTextCrawler):
    """
    Pattern-based fulltext crawler.

    Features:
    - Configurable patterns for different site structures
    - Predefined patterns for common news sites
    - Multiple extraction methods (CSS, XPath, regex)
    - Fallback to generic extraction
    - Post-processing filters

    Pattern Configuration Format:
    {
        "title": {
            "type": "css" | "xpath" | "regex",
            "selector": "...",
            "attribute": "text" | "href" | None,
            "multiple": False
        },
        "content": {
            "type": "css",
            "selector": "article, .content, #main",
            "attribute": "text",
            "multiple": False
        },
        "timestamp": {
            "type": "css",
            "selector": "time, .date, .published",
            "attribute": "text"
        },
        "author": {
            "type": "css",
            "selector": ".author, .byline",
            "attribute": "text"
        },
        "category": {
            "type": "css",
            "selector": ".category, .tags",
            "attribute": "text",
            "multiple": True,
            "join_with": ", "
        },
        "metadata": {
            "description": {
                "type": "css",
                "selector": "meta[name='description']",
                "attribute": "content"
            }
        },
        "post_process": {
            "remove_empty_lines": True,
            "trim_whitespace": True,
            "max_length": 50000
        }
    }
    """

    def crawl(self, url: str) -> Optional[Dict[str, Any]]:
        """
        Crawl a single article URL using patterns.

        Args:
            url: Article URL to crawl

        Returns:
            Article data dictionary or None if failed
        """
        if not url:
            logger.warning("No URL provided")
            return None

        logger.info(f"Pattern-based crawling: {url}")

        try:
            # Fetch HTML
            html = self._fetch_article_html(url)

            # Try configured patterns first
            if hasattr(self.config, 'article_patterns') and self.config.article_patterns:
                result = self._extract_with_patterns(html, url, self.config.article_patterns)
                if result:
                    logger.info(f"Extracted using configured patterns: {result['title'][:50]}...")
                    return self._apply_post_processing(result)

            # Try predefined patterns
            result = self._extract_with_predefined_patterns(html, url)
            if result:
                logger.info(f"Extracted using predefined patterns: {result['title'][:50]}...")
                return self._apply_post_processing(result)

            # Fallback to generic extraction
            result = self._extract_generic(html, url)
            if result:
                logger.info(f"Extracted using generic method: {result['title'][:50]}...")
                return self._apply_post_processing(result)

            logger.warning(f"No content extracted from {url}")
            return None

        except Exception as e:
            logger.error(f"Pattern crawling failed for {url}: {e}")
            return None

    def _extract_with_predefined_patterns(self, html: str, url: str) -> Optional[Dict[str, Any]]:
        """
        Extract using predefined patterns for common news sites.

        Returns:
            Article data or None
        """
        import re

        from bs4 import BeautifulSoup

        soup = BeautifulSoup(html, 'lxml')

        # Predefined patterns for common structures
        patterns_list = [
            # Pattern 1: Modern news sites (article tag)
            {
                "name": "modern_article",
                "title": {"type": "css", "selector": "h1, h1.article-title, h1.entry-title", "attribute": "text"},
                "content": {"type": "css", "selector": "article, .article-content, .entry-content", "attribute": "text"},
                "timestamp": {"type": "css", "selector": "time, .date, .published", "attribute": "text"},
                "author": {"type": "css", "selector": ".author, .byline, [rel='author']", "attribute": "text"},
                "category": {"type": "css", "selector": ".category, .tags, .topic", "attribute": "text", "multiple": True, "join_with": ", "},
                "match": lambda s: s.find('article') is not None
            },
            # Pattern 2: Traditional news sites (div containers)
            {
                "name": "traditional_news",
                "title": {"type": "css", "selector": "h1, h2.title, h2.news-title", "attribute": "text"},
                "content": {"type": "css", "selector": "div.content, div.article, div.main-content, div#content", "attribute": "text"},
                "timestamp": {"type": "css", "selector": "span.date, span.time, div.date", "attribute": "text"},
                "author": {"type": "css", "selector": "span.author, div.author", "attribute": "text"},
                "category": {"type": "css", "selector": "span.category, div.tags", "attribute": "text", "multiple": True, "join_with": ", "},
                "match": lambda s: s.find('div', class_=re.compile(r'content|article|main')) is not None
            },
            # Pattern 3: Blog-style sites
            {
                "name": "blog_style",
                "title": {"type": "css", "selector": "h1.entry-title, h1.post-title", "attribute": "text"},
                "content": {"type": "css", "selector": "div.entry-content, div.post-content, div.post-body", "attribute": "text"},
                "timestamp": {"type": "css", "selector": "time.published, time.entry-date", "attribute": "text"},
                "author": {"type": "css", "selector": "span.author, a.author", "attribute": "text"},
                "category": {"type": "css", "selector": "span.category, a.category", "attribute": "text", "multiple": True, "join_with": ", "},
                "match": lambda s: s.find('div', class_=re.compile(r'entry|post')) is not None
            },
            # Pattern 4: SEU News specific pattern
            {
                "name": "seu_news",
                "title": {"type": "css", "selector": "h1, h1.title, .article-title", "attribute": "text"},
                "content": {"type": "css", "selector": "div.content, div.article-content, div#content", "attribute": "text"},
                "timestamp": {"type": "css", "selector": "span.date, .publish-time, time", "attribute": "text"},
                "author": {"type": "css", "selector": "span.author, .article-author", "attribute": "text"},
                "category": {"type": "css", "selector": "span.category, .news-category", "attribute": "text"},
                "match": lambda s: True  # Always try this pattern
            }
        ]

        for pattern in patterns_list:
            try:
                # Check if pattern matches
                if 'match' in pattern and not pattern['match'](soup):
                    continue

                # Extract using pattern
                result = self._extract_with_patterns(html, url, pattern)
                if result and result.get('content'):
                    logger.info(f"Successfully extracted using pattern: {pattern['name']}")
                    return result

            except Exception as e:
                logger.debug(f"Pattern {pattern['name']} failed: {e}")
                continue

        return None

    def _extract_generic(self, html: str, url: str) -> Optional[Dict[str, Any]]:
        """
        Generic extraction as fallback.

        Uses heuristics to find article content.
        """
        import re

        from bs4 import BeautifulSoup

        soup = BeautifulSoup(html, 'lxml')

        # Try to find title
        title = ""
        for selector in ['h1', 'h2', 'title']:
            elem = soup.find(selector)
            if elem:
                title = elem.get_text(strip=True)
                if len(title) > 10:  # Reasonable title length
                    break

        # Try to find content
        content = ""
        content_selectors = [
            'article',
            'div.content',
            'div.article',
            'div.main-content',
            'div#content',
            'div#main',
            'div#article'
        ]

        for selector in content_selectors:
            elem = soup.select_one(selector)
            if elem:
                # Remove unwanted elements
                for unwanted in elem(['script', 'style', 'nav', 'header', 'footer', 'aside', 'form']):
                    unwanted.decompose()
                content = elem.get_text(separator='\n\n', strip=True)
                if len(content) > 100:  # Reasonable content length
                    break

        # If still no content, try to find the largest text block
        if not content:
            all_divs = soup.find_all('div')
            if all_divs:
                longest_div = max(all_divs, key=lambda d: len(d.get_text(strip=True)))
                content = longest_div.get_text(separator='\n\n', strip=True)

        # Extract metadata
        timestamp = ""
        for selector in ['time', '.date', '.published', '.timestamp']:
            elem = soup.select_one(selector)
            if elem:
                timestamp = elem.get_text(strip=True)
                break

        author = ""
        for selector in ['.author', '.byline', '[rel="author"]']:
            elem = soup.select_one(selector)
            if elem:
                author = elem.get_text(strip=True)
                break

        if not content:
            return None

        return {
            "title": title or "Untitled",
            "url": url,
            "content": content,
            "timestamp": timestamp,
            "author": author,
            "category": "",
            "source": url,
            "type": "html",
            "metadata": {},
            "raw": html[:500] if len(html) > 500 else html
        }

    def _apply_post_processing(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """
        Apply post-processing to clean up extracted content.

        Args:
            item: Raw extracted item

        Returns:
            Processed item
        """
        if not item:
            return item

        # Get post-process config
        post_process = {}
        if hasattr(self.config, 'article_patterns') and self.config.article_patterns:
            post_process = self.config.article_patterns.get('post_process', {})

        content = item.get('content', '')
        title = item.get('title', '')

        # Remove empty lines
        if post_process.get('remove_empty_lines', True):
            content = '\n'.join(line for line in content.split('\n') if line.strip())

        # Trim whitespace
        if post_process.get('trim_whitespace', True):
            content = ' '.join(content.split())
            title = ' '.join(title.split())

        # Limit length
        max_length = post_process.get('max_length', 50000)
        if len(content) > max_length:
            content = content[:max_length] + "... [truncated]"

        # Clean up title
        title = title.strip()
        if title.endswith('|') or title.endswith('-'):
            title = title[:-1].strip()

        # Update item
        item['content'] = content
        item['title'] = title

        return item

    def _extract_with_patterns(self, html: str, url: str, patterns: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Extract using provided patterns (inherited from base).
        """
        return super()._extract_with_patterns(html, url, patterns)


__all__ = ["HtmlTextCrawler"]