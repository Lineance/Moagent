"""
Base class for fulltext crawlers - crawlers that extract full article content.

Fulltext crawlers focus ONLY on extracting complete article content from
individual article pages, NOT on discovering links from list pages.

All crawlers in this folder should inherit from BaseFullTextCrawler and
focus on extracting:
- Full article content/text
- Article metadata (title, author, timestamp, etc.)
- Rich content (images, videos, embedded media)
- Structured data (JSON-LD, OpenGraph, etc.)
"""

import logging
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from urllib.parse import urljoin

from ...config.settings import Config
from ..base import BaseCrawler

logger = logging.getLogger(__name__)


class BaseFullTextCrawler(BaseCrawler):
    """
    Abstract base class for fulltext crawlers.

    All fulltext crawlers should:
    1. Accept article URLs as input (not list pages)
    2. Extract complete article content with rich formatting
    3. Return structured data with full content and metadata
    4. Handle various content formats (HTML, PDF, etc.)
    5. Support pattern-based and LLM-based extraction

    Key Differences from List Crawlers:
    - Input: Single article URL (not list page)
    - Output: Full content + metadata (not just links)
    - Focus: Content depth (not link discovery)
    - Performance: Slower but thorough (not fast)

    Returns:
        Dictionary with keys:
        - title: Article title
        - url: Article URL
        - content: Full article text/content
        - timestamp: Publication date
        - author: Article author (if available)
        - category: Category/tags (if available)
        - source: Source URL
        - type: Content type (html, pdf, etc.)
        - metadata: Additional metadata dict
        - raw: Raw content for debugging
    """

    def __init__(self, config: Config):
        super().__init__(config)
        self.content_timeout = config.content_timeout

    @abstractmethod
    def crawl(self, url: str) -> Optional[Dict[str, Any]]:
        """
        Crawl a single article URL and extract full content.

        Args:
            url: URL of the article to crawl

        Returns:
            Dictionary with full article data or None if failed
        """
        pass

    def crawl_batch(self, urls: List[str]) -> List[Dict[str, Any]]:
        """
        Crawl multiple article URLs.

        Args:
            urls: List of article URLs

        Returns:
            List of article data dictionaries
        """
        results = []
        for url in urls:
            try:
                result = self.crawl(url)
                if result:
                    results.append(result)
            except Exception as e:
                logger.warning(f"Failed to crawl {url}: {e}")
        return results

    def _fetch_article_html(self, url: str) -> str:
        """
        Fetch HTML content from article URL with extended timeout.

        Args:
            url: Article URL

        Returns:
            HTML content as string
        """
        import requests
        import time

        for attempt in range(self.max_retries):
            try:
                response = requests.get(
                    url,
                    headers=self.headers,
                    timeout=self.content_timeout
                )
                response.raise_for_status()
                response.encoding = response.apparent_encoding
                return response.text
            except Exception as e:
                logger.warning(f"Attempt {attempt + 1} failed for {url}: {e}")
                if attempt < self.max_retries - 1:
                    time.sleep(2 ** attempt)
                else:
                    raise

    def _extract_with_patterns(self, html: str, url: str, patterns: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Extract article content using configured patterns.

        Args:
            html: HTML content
            url: Article URL
            patterns: Pattern configuration

        Returns:
            Extracted article data or None
        """
        from bs4 import BeautifulSoup
        import re

        soup = BeautifulSoup(html, 'lxml')

        # Extract title
        title = self._extract_title_with_patterns(soup, patterns.get('title', {}))

        # Extract content
        content = self._extract_content_with_patterns(soup, patterns.get('content', {}))

        # Extract metadata
        metadata = {}
        if 'metadata' in patterns:
            metadata = self._extract_metadata_with_patterns(soup, patterns['metadata'])

        # Extract timestamp
        timestamp = self._extract_timestamp_with_patterns(soup, patterns.get('timestamp', {}))

        # Extract author
        author = self._extract_author_with_patterns(soup, patterns.get('author', {}))

        # Extract category
        category = self._extract_category_with_patterns(soup, patterns.get('category', {}))

        if not content and not title:
            return None

        return {
            "title": self._clean_text(title),
            "url": url,
            "content": self._clean_text(content),
            "timestamp": self._normalize_timestamp(timestamp),
            "author": self._clean_text(author),
            "category": self._clean_text(category),
            "source": url,
            "type": "html",
            "metadata": metadata,
            "raw": html[:500] if len(html) > 500 else html
        }

    def _extract_title_with_patterns(self, soup, patterns: Dict[str, Any]) -> str:
        """Extract title using patterns."""
        if not patterns:
            # Fallback: try common title selectors
            for selector in ['h1', 'h2', 'title']:
                elem = soup.find(selector)
                if elem:
                    return elem.get_text(strip=True)
            return ""

        return self._extract_field_with_config(soup, patterns, "title")

    def _extract_content_with_patterns(self, soup, patterns: Dict[str, Any]) -> str:
        """Extract content using patterns."""
        if not patterns:
            # Fallback: try common content containers
            for selector in [
                {'tag': 'article'},
                {'tag': 'div', 'class': re.compile(r'content|article|main')},
                {'tag': 'div', 'class': re.compile(r'body|entry')}
            ]:
                if 'class' in selector:
                    elem = soup.find(selector['tag'], class_=selector['class'])
                else:
                    elem = soup.find(selector['tag'])
                if elem:
                    # Remove unwanted elements
                    for unwanted in elem(['script', 'style', 'nav', 'header', 'footer', 'aside']):
                        unwanted.decompose()
                    return elem.get_text(separator='\n\n', strip=True)
            return ""

        return self._extract_field_with_config(soup, patterns, "content")

    def _extract_metadata_with_patterns(self, soup, patterns: Dict[str, Any]) -> Dict[str, Any]:
        """Extract metadata using patterns."""
        metadata = {}
        for key, selector in patterns.items():
            value = self._extract_field_with_config(soup, selector, key)
            if value:
                metadata[key] = value
        return metadata

    def _extract_timestamp_with_patterns(self, soup, patterns: Dict[str, Any]) -> str:
        """Extract timestamp using patterns."""
        if not patterns:
            from datetime import datetime
            return datetime.now().isoformat()
        return self._extract_field_with_config(soup, patterns, "timestamp")

    def _extract_author_with_patterns(self, soup, patterns: Dict[str, Any]) -> str:
        """Extract author using patterns."""
        if not patterns:
            return ""
        return self._extract_field_with_config(soup, patterns, "author")

    def _extract_category_with_patterns(self, soup, patterns: Dict[str, Any]) -> str:
        """Extract category using patterns."""
        if not patterns:
            return ""
        return self._extract_field_with_config(soup, patterns, "category")

    def _extract_field_with_config(self, soup, config: Dict[str, Any], field_name: str) -> str:
        """
        Extract a field using configuration.

        Config format:
        {
            "type": "css" | "xpath" | "regex",
            "selector": "...",
            "attribute": "href" | "text" | None,
            "multiple": False | True,
            "join_with": " " | "\n" | ", "
        }
        """
        if not config:
            return ""

        selector_type = config.get("type", "css")
        selector = config.get("selector", "")
        attribute = config.get("attribute", "text")
        multiple = config.get("multiple", False)
        join_with = config.get("join_with", " ")

        try:
            if selector_type == "css":
                if multiple:
                    elements = soup.select(selector)
                else:
                    elements = [soup.select_one(selector)]
            elif selector_type == "xpath":
                from lxml import etree
                tree = etree.HTML(str(soup))
                if multiple:
                    elements = tree.xpath(selector)
                else:
                    result = tree.xpath(selector)
                    elements = [result] if result else []
            elif selector_type == "regex":
                import re
                text = soup.get_text()
                if multiple:
                    matches = re.findall(selector, text)
                    return join_with.join(matches)
                else:
                    match = re.search(selector, text)
                    return match.group(1) if match else ""
            else:
                return ""

            if not elements or elements[0] is None:
                return ""

            if attribute == "text":
                texts = [elem.get_text(strip=True) if hasattr(elem, 'get_text') else str(elem) for elem in elements if elem]
                return join_with.join(texts) if multiple else texts[0] if texts else ""
            elif attribute:
                values = []
                for elem in elements:
                    if hasattr(elem, 'get'):
                        values.append(elem.get(attribute, ""))
                    elif hasattr(elem, 'xpath'):
                        # lxml element
                        attr_val = elem.get(attribute)
                        if attr_val:
                            values.append(attr_val)
                return join_with.join(values) if multiple else values[0] if values else ""
            else:
                texts = [elem.get_text(strip=True) if hasattr(elem, 'get_text') else str(elem) for elem in elements if elem]
                return join_with.join(texts) if multiple else texts[0] if texts else ""

        except Exception as e:
            logger.debug(f"Failed to extract field {field_name} with config: {e}")
            return ""

    def _extract_with_llm(self, html: str, url: str) -> Optional[Dict[str, Any]]:
        """
        Extract article content using LLM.

        Args:
            html: HTML content
            url: Article URL

        Returns:
            Extracted article data or None
        """
        try:
            from ...parsers.llm import LLMParser

            # Create raw item for parser
            raw_item = {
                "html": html,
                "url": url,
                "source": url,
                "type": "html"
            }

            # Use LLM parser
            parser = LLMParser(self.config)
            result = parser.parse(raw_item)

            if result:
                # Ensure all required fields
                result.setdefault("metadata", {})
                result.setdefault("raw", html[:500] if len(html) > 500 else html)

            return result

        except Exception as e:
            logger.error(f"LLM extraction failed: {e}")
            return None

    def _extract_with_structured_data(self, html: str, url: str) -> Optional[Dict[str, Any]]:
        """
        Extract using structured data (JSON-LD, OpenGraph, etc.).

        Args:
            html: HTML content
            url: Article URL

        Returns:
            Extracted article data or None
        """
        from bs4 import BeautifulSoup
        import json
        import re

        soup = BeautifulSoup(html, 'lxml')

        # Try JSON-LD
        json_ld_scripts = soup.find_all('script', type='application/ld+json')
        for script in json_ld_scripts:
            try:
                data = json.loads(script.string)
                if isinstance(data, list):
                    for item in data:
                        if item.get('@type') in ['Article', 'NewsArticle', 'BlogPosting']:
                            return self._parse_json_ld(item, url)
                elif isinstance(data, dict) and data.get('@type') in ['Article', 'NewsArticle', 'BlogPosting']:
                    return self._parse_json_ld(data, url)
            except:
                continue

        # Try OpenGraph
        og_title = soup.find('meta', property='og:title')
        og_desc = soup.find('meta', property='og:description')
        og_type = soup.find('meta', property='og:type')

        if og_title or og_desc:
            return {
                "title": og_title['content'] if og_title else "",
                "url": url,
                "content": og_desc['content'] if og_desc else "",
                "timestamp": "",
                "author": "",
                "category": "",
                "source": url,
                "type": "html",
                "metadata": {
                    "og_type": og_type['content'] if og_type else ""
                },
                "raw": html[:500] if len(html) > 500 else html
            }

        return None

    def _parse_json_ld(self, data: Dict[str, Any], url: str) -> Dict[str, Any]:
        """Parse JSON-LD data into article format."""
        return {
            "title": data.get('headline', ''),
            "url": data.get('url', url),
            "content": data.get('articleBody', '') or data.get('description', ''),
            "timestamp": data.get('datePublished', ''),
            "author": data.get('author', {}).get('name', '') if isinstance(data.get('author'), dict) else data.get('author', ''),
            "category": ', '.join(data.get('keywords', [])) if isinstance(data.get('keywords'), list) else data.get('keywords', ''),
            "source": url,
            "type": "html",
            "metadata": {
                "dateModified": data.get('dateModified', ''),
                "publisher": data.get('publisher', {}).get('name', '') if isinstance(data.get('publisher'), dict) else data.get('publisher', '')
            },
            "raw": str(data)
        }

    def _normalize_item(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normalize a crawled article item.

        Ensures all required fields are present and properly formatted.
        """
        # Ensure required fields
        if "title" not in item:
            item["title"] = "Untitled"
        if "url" not in item:
            item["url"] = ""
        if "content" not in item:
            item["content"] = ""
        if "timestamp" not in item:
            from datetime import datetime
            item["timestamp"] = datetime.now().isoformat()
        if "type" not in item:
            item["type"] = "article"

        # Clean whitespace
        if isinstance(item.get("title"), str):
            item["title"] = item["title"].strip()
        if isinstance(item.get("content"), str):
            item["content"] = item["content"].strip()
        if isinstance(item.get("author"), str):
            item["author"] = item["author"].strip()

        # Ensure metadata exists
        if "metadata" not in item:
            item["metadata"] = {}

        return item

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(config={self.config.target_url})"


__all__ = ["BaseFullTextCrawler"]