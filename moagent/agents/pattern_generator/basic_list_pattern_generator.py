"""
Basic List Pattern Generator - Rule-based HTML analysis for list patterns.

Fast, no-API-cost pattern detection using BeautifulSoup and heuristics.
Optimized for speed and reduced code complexity.
"""

import logging
import re
from typing import Dict, Any, List, Optional, Tuple
from pathlib import Path
from dataclasses import dataclass
from collections import Counter

from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


@dataclass
class PatternAnalysis:
    """Results from analyzing HTML structure."""
    list_container: Dict[str, Any]
    item_selector: Dict[str, Any]
    title_selector: Dict[str, Any]
    url_selector: Dict[str, Any]
    date_selector: Optional[Dict[str, Any]]
    content_selector: Optional[Dict[str, Any]]
    confidence: float
    sample_items: List[Dict[str, str]]
    issues: List[str]
    post_process: Dict[str, Any]


class PatternGeneratorAgent:
    """Rule-based agent that generates crawler patterns from HTML files."""

    # Common patterns for list pages
    CONTAINER_PATTERNS = [
        ('ul', 'wp_article_list'), ('div', 'article-list'), ('div', 'news-list'),
        ('ul', 'news-list'), ('div', 'list'), ('ul', 'list'), ('article', None),
        ('ul', None), ('ol', None), ('div', None)
    ]

    ITEM_PATTERNS = [
        ('li', 'list_item'), ('li', 'item'), ('div', 'article-item'),
        ('div', 'news-item'), ('article', None), ('div', 'item'),
        ('li', None), ('div', None)
    ]

    TITLE_PATTERNS = [
        ('h3', 'title'), ('h2', 'title'), ('h3', 'article-title'),
        ('h2', 'article-title'), ('a', 'title'), ('span', 'title'),
        ('h3', None), ('h2', None), ('a', None)
    ]

    DATE_PATTERNS = [
        ('span', 'date'), ('span', 'time'), ('span', 'publish-date'),
        ('time', None), ('div', 'date'), ('span', 'article-date'),
        ('div', 'meta')
    ]

    CONTENT_PATTERNS = [
        ('p', 'summary'), ('div', 'content'), ('p', 'excerpt'),
        ('div', 'description'), ('p', None), ('div', None)
    ]

    def __init__(self):
        """Initialize the pattern generator."""
        self.min_confidence_threshold = 0.6
        self.max_sample_items = 5

    def analyze_html_file(self, file_path: str) -> PatternAnalysis:
        """Analyze HTML file."""
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"HTML file not found: {file_path}")

        with open(path, 'r', encoding='utf-8', errors='ignore') as f:
            html_content = f.read()

        return self.analyze_html_content(html_content)

    def analyze_html_content(self, html_content: str) -> PatternAnalysis:
        """Analyze HTML content to detect list patterns."""
        soup = BeautifulSoup(html_content, 'lxml')
        issues = []

        # Find container
        list_container, container_conf = self._find_container(soup)
        if not list_container:
            issues.append("Could not find article list container")
            list_container = {"tag": "div"}

        # Find items
        item_selector, item_conf = self._find_items(soup, list_container)
        if not item_selector:
            issues.append("Could not find article item selector")
            item_selector = {"tag": "div"}

        # Extract samples
        sample_items = self._extract_samples(soup, list_container, item_selector)

        # Analyze fields
        if sample_items:
            title_selector, title_conf = self._analyze_field(sample_items, self.TITLE_PATTERNS, self._is_title)
            url_selector, url_conf = self._analyze_field(sample_items, self.TITLE_PATTERNS, self._is_title, need_link=True)
            date_selector, date_conf = self._analyze_field(sample_items, self.DATE_PATTERNS, self._is_date)
            content_selector, content_conf = self._analyze_field(sample_items, self.CONTENT_PATTERNS, self._is_content)
        else:
            issues.append("No sample items found")
            title_selector, url_selector = {"type": "h3", "link": True}, {"type": "h3", "link": True}
            date_selector, content_selector = None, None
            title_conf = url_conf = date_conf = content_conf = 0.0

        # Calculate confidence
        confs = [container_conf, item_conf, title_conf, url_conf]
        if date_conf > 0: confs.append(date_conf)
        if content_conf > 0: confs.append(content_conf)
        overall_conf = sum(confs) / len(confs) if confs else 0.0

        # Detect post-processing
        post_process = self._detect_post_process(soup, sample_items)

        return PatternAnalysis(
            list_container=list_container, item_selector=item_selector,
            title_selector=title_selector, url_selector=url_selector,
            date_selector=date_selector, content_selector=content_selector,
            confidence=overall_conf, sample_items=sample_items[:self.max_sample_items],
            issues=issues, post_process=post_process
        )

    def _find_container(self, soup: BeautifulSoup) -> Tuple[Optional[Dict[str, Any]], float]:
        """Find list container - excludes navigation elements."""
        for tag, class_name in self.CONTAINER_PATTERNS:
            container = soup.find(tag, class_=class_name) if class_name else soup.find(tag)
            if container:
                # Exclude navigation containers
                if self._is_navigation_element(container):
                    continue
                children = container.find_all(recursive=False)
                if len(children) >= 3:
                    result = {"tag": tag}
                    if class_name: result["class"] = class_name
                    return result, 0.8 if class_name else 0.6
        return None, 0.0

    def _is_navigation_element(self, elem) -> bool:
        """Check if element is a navigation element."""
        # Check element itself
        elem_name = elem.name or ""
        elem_classes = elem.get('class', [])

        # Navigation indicators
        nav_indicators = ['nav', 'header', 'footer', 'menu', 'sidebar', 'breadcrumb']

        if any(indicator in elem_name.lower() for indicator in nav_indicators):
            return True

        if any(indicator in str(cls).lower() for cls in elem_classes for indicator in nav_indicators):
            return True

        # Check parent context
        parent = elem.parent
        if parent:
            parent_name = parent.name or ""
            parent_classes = parent.get('class', [])
            if any(indicator in parent_name.lower() for indicator in nav_indicators):
                return True
            if any(indicator in str(cls).lower() for cls in parent_classes for indicator in nav_indicators):
                return True

        return False

    def _find_items(self, soup: BeautifulSoup, container: Dict[str, Any]) -> Tuple[Optional[Dict[str, Any]], float]:
        """Find item selector."""
        if not container:
            return None, 0.0

        container_elem = soup.find(container["tag"], class_=container.get("class"))
        if not container_elem:
            return None, 0.0

        for tag, class_name in self.ITEM_PATTERNS:
            items = container_elem.find_all(tag, class_=class_name) if class_name else container_elem.find_all(tag)
            if len(items) >= 3:
                result = {"tag": tag}
                if class_name: result["class"] = class_name
                return result, 0.8 if class_name else 0.5
        return None, 0.0

    def _extract_samples(self, soup: BeautifulSoup, container: Dict[str, Any], item: Dict[str, Any]) -> List:
        """Extract sample items."""
        if not container or not item:
            return []

        container_elem = soup.find(container["tag"], class_=container.get("class"))
        if not container_elem:
            return []

        items = container_elem.find_all(item["tag"], class_=item.get("class")) if item.get("class") else container_elem.find_all(item["tag"])
        return items[:self.max_sample_items * 2]

    def _analyze_field(self, samples: List, patterns: List, validator, need_link=False) -> Tuple[Dict[str, Any], float]:
        """Analyze field patterns."""
        for tag, class_name in patterns:
            matches = 0
            for item in samples:
                elem = item.find(tag, class_=class_name) if class_name else item.find(tag)
                if elem and validator(elem):
                    matches += 1
            if matches / len(samples) >= 0.5:
                # Check for link
                has_link = need_link
                if need_link:
                    for item in samples[:3]:
                        elem = item.find(tag, class_=class_name) if class_name else item.find(tag)
                        if elem and (elem.name == "a" or elem.find("a", href=True)):
                            has_link = True
                            break
                result = {"type": tag, "link": has_link} if need_link else {"type": tag}
                if class_name: result["class"] = class_name
                return result, 0.8
        return {"type": "h3", "link": True}, 0.3

    def _is_title(self, elem) -> bool:
        """Check if element looks like a title."""
        text = elem.get_text(strip=True)
        return 5 < len(text) < 200

    def _is_date(self, elem) -> bool:
        """Check if element looks like a date."""
        text = elem.get_text(strip=True)
        if len(text) < 4:
            return False
        patterns = [
            r'\d{4}-\d{1,2}-\d{1,2}', r'\d{1,2}/\d{1,2}/\d{4}',
            r'\d{4}年\d{1,2}月\d{1,2}日', r'\d{1,2}\s+(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{4}'
        ]
        if any(re.search(p, text) for p in patterns):
            return True
        months = ['jan', 'feb', 'mar', 'apr', 'may', 'jun', 'jul', 'aug', 'sep', 'oct', 'nov', 'dec',
                  '一月', '二月', '三月', '四月', '五月', '六月', '七月', '八月', '九月', '十月', '十一月', '十二月']
        return any(m in text.lower() for m in months)

    def _is_content(self, elem) -> bool:
        """Check if element looks like content."""
        text = elem.get_text(strip=True)
        return len(text) > 20

    def _detect_post_process(self, soup: BeautifulSoup, samples: List) -> Dict[str, Any]:
        """Detect post-processing needs including navigation filters."""
        post_process = {}

        # Font tag detection
        for item in samples[:3]:
            if item.find("font"):
                post_process["remove_font_tags"] = True
                break

        # Entity decoding
        html_str = str(soup)
        if "&" in html_str or "<" in html_str or ">" in html_str:
            post_process["decode_entities"] = True

        # Navigation exclusion filters
        nav_patterns = self._detect_navigation_patterns(soup, samples)
        if nav_patterns:
            post_process.update(nav_patterns)

        return post_process

    def _detect_navigation_patterns(self, soup: BeautifulSoup, samples: List) -> Dict[str, Any]:
        """Detect navigation patterns to exclude."""
        filters = {}

        # Check for navigation URLs in samples
        nav_url_indicators = ['/menu', '/nav', '/footer', '/header', '/sidebar', '/category', '/tag', '/author']
        nav_titles = ['Home', 'About', 'Contact', 'More', 'Next', 'Previous', 'Login', 'Register']

        found_nav_urls = []
        found_nav_titles = []
        found_nav_titles_like = []

        for item in samples[:5]:
            # Check links
            links = item.find_all('a', href=True)
            for link in links:
                href = link.get('href', '').lower()
                title = link.get_text(strip=True)

                # Detect navigation URL patterns
                for indicator in nav_url_indicators:
                    if indicator in href and href not in found_nav_urls:
                        found_nav_urls.append(indicator)

                # Detect navigation titles
                if title in nav_titles and title not in found_nav_titles:
                    found_nav_titles.append(title)

                # Detect short/generic titles
                if len(title) > 0 and len(title) < 5 and title not in found_nav_titles_like:
                    found_nav_titles_like.append(title)

        # Build filter config
        if found_nav_urls:
            filters["exclude_url_patterns"] = found_nav_urls

        if found_nav_titles:
            filters["exclude_titles"] = found_nav_titles

        if found_nav_titles_like:
            filters["exclude_titles_like"] = found_nav_titles_like

        # Always add minimum title length filter
        filters["min_title_length"] = 5

        # Check if any items have titles that are too short (likely navigation)
        short_titles = 0
        for item in samples[:5]:
            title_elem = item.find(['h1', 'h2', 'h3', 'h4', 'a'])
            if title_elem:
                title = title_elem.get_text(strip=True)
                if len(title) > 0 and len(title) < 5:
                    short_titles += 1

        if short_titles >= 2:
            filters["require_title"] = True

        return filters

    def generate_config_yaml(self, analysis: PatternAnalysis, name: str, description: str = None) -> Dict[str, Any]:
        """Generate configuration dictionary."""
        config = {
            "target_url": "https://example.com/news",
            "crawl_mode": "static",
            "crawler_patterns": {
                "list_container": analysis.list_container,
                "item_selector": analysis.item_selector,
                "title_selector": analysis.title_selector,
                "url_selector": analysis.url_selector,
            },
            "check_interval": 3600,
            "timeout": 30,
            "max_retries": 3,
        }

        for key, value in [
            ("date_selector", analysis.date_selector),
            ("content_selector", analysis.content_selector),
            ("post_process", analysis.post_process),
        ]:
            if value:
                config["crawler_patterns"][key] = value

        config["crawler_patterns"]["_metadata"] = {
            "name": name,
            "description": description or f"Auto-generated pattern for {name}",
            "confidence": analysis.confidence,
            "generated_by": "PatternGeneratorAgent",
            "issues": analysis.issues,
        }

        return config

    def generate_pattern_code(self, analysis: PatternAnalysis, name: str, description: str = None) -> str:
        """Generate Python code for pattern."""
        desc = description or f"Auto-generated pattern for {name}"
        code = f'''    "{name}": CrawlerPattern(
        name="{name.title()}",
        description="{desc}",
        list_container={analysis.list_container},
        item_selector={analysis.item_selector},
        title_selector={analysis.title_selector},
        url_selector={analysis.url_selector}'''

        if analysis.date_selector:
            code += f",\n        date_selector={analysis.date_selector}"
        if analysis.content_selector:
            code += f",\n        content_selector={analysis.content_selector}"
        if analysis.post_process:
            code += f",\n        post_process={analysis.post_process}"

        code += "\n    ),"
        return code

    def compare_patterns(self, pattern1: Dict[str, Any], pattern2: Dict[str, Any]) -> Dict[str, Any]:
        """Compare two patterns."""
        differences = {}
        for key in ["list_container", "item_selector", "title_selector", "url_selector"]:
            if key in pattern1 and key in pattern2 and pattern1[key] != pattern2[key]:
                differences[key] = {"pattern1": pattern1[key], "pattern2": pattern2[key]}
        return differences

    def validate_pattern(self, pattern: Dict[str, Any], html_content: str) -> Dict[str, Any]:
        """Validate pattern against HTML."""
        try:
            soup = BeautifulSoup(html_content, 'lxml')
            items = self._extract_with_pattern(soup, pattern)
            return {"success": True, "items_found": len(items), "sample_items": items[:3], "issues": []}
        except Exception as e:
            return {"success": False, "items_found": 0, "sample_items": [], "issues": [str(e)]}

    def _extract_with_pattern(self, soup: BeautifulSoup, pattern: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract items using pattern with post-processing."""
        list_container = pattern.get("list_container", {})
        item_selector = pattern.get("item_selector", {})
        post_process = pattern.get("post_process", {})

        container = soup.find(list_container.get("tag"), class_=list_container.get("class")) if list_container.get("class") else soup.find(list_container.get("tag"))
        if not container:
            return []

        items = container.find_all(item_selector.get("tag"), class_=item_selector.get("class")) if item_selector.get("class") else container.find_all(item_selector.get("tag"))

        results = []
        for item in items[:20]:  # Extract more to allow filtering
            title = self._extract_field(item, pattern.get("title_selector", {}))
            url = self._extract_field(item, pattern.get("url_selector", {}))
            if title and url:
                results.append({"title": title, "url": url})

        # Apply post-processing filters
        if post_process:
            results = self._apply_post_processing(results, post_process)

        return results

    def _apply_post_processing(self, items: List[Dict[str, Any]], post_process: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Apply post-processing filters to clean up results.
        
        Supported filters:
        - exclude_url_patterns: List of URL substrings to exclude (case-insensitive)
        - exclude_url_regex: List of regex patterns to match against URL
        - exclude_titles: List of exact title strings to exclude
        - exclude_titles_like: List of substrings to match in title
        - exclude_title_regex: List of regex patterns to match against title
        - min_title_length: Minimum title length (0 = no minimum)
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

    def _extract_field(self, item, selector: Dict[str, Any]) -> str:
        """Extract single field."""
        if not selector:
            return ""

        selector_type = selector.get("type")
        selector_class = selector.get("class")
        has_link = selector.get("link", False)

        elem = item.find(selector_type, class_=selector_class) if selector_class else item.find(selector_type)
        if not elem:
            return ""

        if has_link:
            link_elem = elem.find("a", href=True) if elem.name != "a" else elem
            return link_elem.get_text(strip=True) if link_elem else ""

        return elem.get_text(strip=True)
