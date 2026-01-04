"""
HTML list crawler - extracts article links from HTML list pages.

This is the primary list crawler for static HTML pages.
"""

import logging
from typing import List, Dict, Any
from datetime import datetime
from urllib.parse import urljoin

from .base import BaseListCrawler

logger = logging.getLogger(__name__)


class HTMLListCrawler(BaseListCrawler):
    """
    HTML list crawler for extracting article links from HTML pages.

    Features:
    - Fast HTML parsing with BeautifulSoup
    - Configurable patterns for different site structures
    - Predefined patterns for common news sites
    - Fallback generic extraction

    Returns:
        List of {title, url, content="", timestamp, source, type}
    """

    def crawl(self) -> List[Dict[str, Any]]:
        """Extract article links from HTML list page."""
        if not self.config.target_url:
            logger.warning("No target URL configured")
            return []

        logger.info(f"HTML list crawling: {self.config.target_url}")

        try:
            from requests_html import HTMLSession

            session = HTMLSession()
            response = session.get(
                self.config.target_url,
                headers=self.headers,
                timeout=self.timeout
            )
            response.raise_for_status()

            # Ensure proper encoding
            response.encoding = response.apparent_encoding

            # Render JavaScript if needed (for auto mode)
            html_content = response.text
            if self.config.crawl_mode == "auto":
                try:
                    response.html.render(timeout=10)
                    html_content = response.html.html
                except:
                    pass

            # Extract articles
            items = self._extract_articles(html_content, response.url)

            logger.info(f"HTML extraction: {len(items)} items")
            return items

        except Exception as e:
            logger.error(f"HTML extraction failed: {e}")
            return []

    def _extract_articles(self, html: str, base_url: str) -> List[Dict[str, Any]]:
        """Extract article links using configured patterns."""
        from bs4 import BeautifulSoup
        import re

        soup = BeautifulSoup(html, 'lxml')
        items = []

        # Try configured patterns first
        if hasattr(self.config, 'crawler_patterns') and self.config.crawler_patterns:
            items = self._extract_with_config_patterns(soup, base_url)
            if items:
                logger.info(f"Extracted {len(items)} articles using configured patterns")
                return items

        # Try predefined patterns
        items = self._extract_with_predefined_patterns(soup, base_url)
        if items:
            return items

        # Fallback to generic extraction
        items = self._extract_generic_articles(soup, base_url)
        
        # Apply post-processing filters if configured
        if hasattr(self.config, 'crawler_patterns') and self.config.crawler_patterns:
            post_process = self.config.crawler_patterns.get('post_process', {})
            if post_process:
                items = self._apply_post_processing_filters(items, post_process)
        
        return items

    def _extract_with_config_patterns(self, soup, base_url: str) -> List[Dict[str, Any]]:
        """Extract using user-configured patterns."""
        from .patterns import pattern_to_config

        patterns_config = self.config.crawler_patterns

        # Handle pattern name reference
        if isinstance(patterns_config, dict) and 'pattern_name' in patterns_config:
            from .patterns import get_pattern
            try:
                pattern = get_pattern(patterns_config['pattern_name'])
                patterns_config = pattern_to_config(pattern)
            except ValueError:
                logger.warning(f"Unknown pattern: {patterns_config['pattern_name']}")
                return []

        try:
            list_container = patterns_config.get('list_container', {})
            item_selector = patterns_config.get('item_selector', {})
            title_selector = patterns_config.get('title_selector', {})
            url_selector = patterns_config.get('url_selector', {})
            date_selector = patterns_config.get('date_selector', {})
            post_process = patterns_config.get('post_process', {})

            # Find list container
            list_tag = list_container.get('tag')
            list_class = list_container.get('class')
            if list_class:
                article_list = soup.find(list_tag, class_=list_class)
            else:
                article_list = soup.find(list_tag)

            if not article_list:
                return []

            # Find items
            item_tag = item_selector.get('tag')
            item_class = item_selector.get('class')
            if item_class:
                list_items = article_list.find_all(item_tag, class_=item_class)
            else:
                list_items = article_list.find_all(item_tag)

            for item in list_items[:20]:
                article_data = self._extract_item_data(
                    item, title_selector, url_selector, date_selector,
                    base_url, post_process, self.config.target_url, "html"
                )
                if article_data:
                    items.append(self._normalize_item(article_data))

            # Apply post-processing filters
            if post_process:
                items = self._apply_post_processing_filters(items, post_process)

            return items

        except Exception as e:
            logger.warning(f"Config pattern failed: {e}")
            return []

    def _extract_with_predefined_patterns(self, soup, base_url: str) -> List[Dict[str, Any]]:
        """Extract using predefined patterns."""
        from .patterns import PREDEFINED_PATTERNS

        for pattern_name, pattern in PREDEFINED_PATTERNS.items():
            try:
                # Find list container
                list_tag = pattern.list_container["tag"]
                list_class = pattern.list_container.get("class")
                if list_class:
                    article_list = soup.find(list_tag, class_=list_class)
                else:
                    article_list = soup.find(list_tag)

                if not article_list:
                    continue

                # Find items
                item_tag = pattern.item_selector["tag"]
                item_class = pattern.item_selector.get("class")
                if item_class:
                    list_items = article_list.find_all(item_tag, class_=item_class)
                else:
                    list_items = article_list.find_all(item_tag)

                if not list_items:
                    continue

                items = []
                for item in list_items[:20]:
                    article_data = self._extract_item_data(
                        item,
                        pattern.title_selector,
                        pattern.url_selector,
                        pattern.date_selector,
                        base_url,
                        pattern.post_process,
                        self.config.target_url,
                        "html"
                    )
                    if article_data:
                        items.append(self._normalize_item(article_data))

                if items:
                    # Apply post-processing filters
                    post_process = pattern.post_process if hasattr(pattern, 'post_process') else {}
                    if post_process:
                        items = self._apply_post_processing_filters(items, post_process)

                    logger.info(f"Extracted {len(items)} articles using '{pattern_name}' pattern")
                    return items

            except Exception as e:
                logger.debug(f"Pattern '{pattern_name}' failed: {e}")
                continue

        return []

    def _extract_item_data(self, item, title_selector, url_selector, date_selector, base_url, post_process, target_url, source_type):
        """Extract data from a single item."""
        try:
            title = self._extract_field(item, title_selector, base_url, "title")
            url = self._extract_field(item, url_selector, base_url, "url")
            timestamp = self._extract_field(item, date_selector, base_url, "date") if date_selector else datetime.now().isoformat()

            # Post-processing
            if post_process.get("remove_font_tags") and title:
                from bs4 import BeautifulSoup
                temp_soup = BeautifulSoup(title, 'lxml')
                for font in temp_soup.find_all('font'):
                    font.unwrap()
                title = temp_soup.get_text(strip=True)

            if not title or not url:
                return None

            return {
                "title": title,
                "url": url,
                "content": "",
                "timestamp": timestamp,
                "source": target_url,
                "type": source_type,
                "raw": str(item)
            }
        except Exception as e:
            logger.debug(f"Failed to extract item data: {e}")
            return None

    def _extract_field(self, item, selector, base_url, field_type):
        """Extract a single field using selector configuration."""
        selector_type = selector.get("type")
        selector_class = selector.get("class")
        has_link = selector.get("link", False)

        if selector_type == "direct":
            if field_type == "url":
                return item.get("href", "") if item.name == "a" else ""
            return item.get_text(strip=True)

        # Find element
        if selector_class:
            elem = item.find(selector_type, class_=selector_class)
        else:
            elem = item.find(selector_type)

        if not elem:
            return ""

        if has_link:
            link_elem = elem.find("a", href=True) if elem.name != "a" else elem
            if link_elem:
                if field_type == "url":
                    url = link_elem.get("href", "")
                    if url:
                        url = urljoin(base_url, url)
                    return url
                else:
                    return link_elem.get_text(strip=True)
            return ""

        return elem.get_text(strip=True)

    def _extract_generic_articles(self, soup, base_url: str) -> List[Dict[str, Any]]:
        """Fallback generic extraction."""
        import re

        # Common article patterns
        article_patterns = [
            {'container': 'div', 'class': re.compile(r'news-list|article-list|news-item|article-item')},
            {'container': 'li', 'class': re.compile(r'news|article')},
            {'container': 'div', 'class': re.compile(r'list-item')},
            {'container': 'article'},
        ]

        articles = []
        for pattern in article_patterns:
            if 'class' in pattern:
                articles = soup.find_all(pattern['container'], class_=pattern['class'])
            else:
                articles = soup.find_all(pattern['container'])
            if articles:
                break

        if not articles:
            links = self._extract_links(str(soup), base_url)
            items = []
            for link in links[:20]:
                items.append({
                    "title": f"Article from {link}",
                    "url": link,
                    "content": "",
                    "timestamp": datetime.now().isoformat(),
                    "source": self.config.target_url,
                    "type": "html"
                })
            return items

        items = []
        for article in articles[:20]:
            title_elem = article.find(['h1', 'h2', 'h3', 'h4', 'a'], class_=re.compile(r'title|headline'))
            title = title_elem.get_text(strip=True) if title_elem else "No title"

            link_elem = article.find('a', href=True)
            url = link_elem['href'] if link_elem else ""
            if url:
                url = urljoin(base_url, url)

            date_elem = article.find(['time', 'span'], class_=re.compile(r'date|time'))
            timestamp = date_elem.get_text(strip=True) if date_elem else datetime.now().isoformat()

            item = {
                "title": title,
                "url": url,
                "content": "",
                "timestamp": timestamp,
                "source": self.config.target_url,
                "type": "html",
                "raw": str(article)
            }

            items.append(self._normalize_item(item))

        # Note: post_process filtering is applied in _extract_articles after this method returns
        return items

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


__all__ = ["HTMLListCrawler"]