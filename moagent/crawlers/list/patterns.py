"""
Pattern configuration system for list crawlers.

This module provides predefined patterns for different website structures,
allowing the static crawler to adapt without code changes.
"""

from typing import Dict, Any, List
from dataclasses import dataclass, field


@dataclass
class ListPattern:
    """
    Configuration for extracting article links from a specific site structure.
    
    Post-processing options (post_process dict):
    - remove_font_tags: bool - Remove <font> tags from titles
    - exclude_url_patterns: List[str] - Exclude items whose URL contains any of these substrings (case-insensitive)
    - exclude_url_regex: List[str] - Exclude items whose URL matches any of these regex patterns
    - exclude_titles: List[str] - Exclude items with exact title matches
    - exclude_titles_like: List[str] - Exclude items whose title contains any of these substrings (case-insensitive)
    - exclude_title_regex: List[str] - Exclude items whose title matches any of these regex patterns
    - min_title_length: int - Minimum title length (default: 0, no minimum)
    - require_title: bool - Require non-empty title (default: False)
    """

    name: str
    description: str
    # Container for article list
    list_container: Dict[str, Any]
    # Individual article items
    item_selector: Dict[str, Any]
    # Title extraction
    title_selector: Dict[str, Any]
    # URL extraction
    url_selector: Dict[str, Any]
    # Date extraction (optional)
    date_selector: Dict[str, Any] = None
    # Content extraction (optional)
    content_selector: Dict[str, Any] = None
    # Post-processing options
    post_process: Dict[str, Any] = field(default_factory=dict)


# Predefined patterns for common website structures
PREDEFINED_PATTERNS = {
    "seu_news": ListPattern(
        name="Southeast University News",
        description="Standard SEU news portal structure with wp_article_list",
        list_container={"tag": "ul", "class": "wp_article_list"},
        item_selector={"tag": "li", "class": "list_item"},
        title_selector={"type": "span", "class": "Article_Title", "link": True},
        url_selector={"type": "span", "class": "Article_Title", "link": True},
        date_selector={"type": "span", "class": "Article_PublishDate"},
        post_process={"remove_font_tags": True}
    ),

    "university_news": ListPattern(
        name="Generic University News",
        description="Common university news list structure",
        list_container={"tag": "div", "class": "news-list"},
        item_selector={"tag": "div", "class": "news-item"},
        title_selector={"type": "h3", "class": "news-title", "link": True},
        url_selector={"type": "h3", "class": "news-title", "link": True},
        date_selector={"type": "span", "class": "news-date"},
    ),

    "blog_articles": ListPattern(
        name="Blog Article List",
        description="Standard blog article listing",
        list_container={"tag": "div", "class": "article-list"},
        item_selector={"tag": "article"},
        title_selector={"type": "h2", "class": "entry-title", "link": True},
        url_selector={"type": "h2", "class": "entry-title", "link": True},
        date_selector={"type": "time", "class": "entry-date"},
        content_selector={"type": "div", "class": "entry-content"},
    ),

    "simple_links": ListPattern(
        name="Simple Link List",
        description="Basic list of links, fallback pattern",
        list_container={"tag": "div", "class": "content"},
        item_selector={"tag": "a"},
        title_selector={"type": "direct", "link": False},
        url_selector={"type": "direct", "link": True},
    ),
}


def get_pattern(name: str) -> ListPattern:
    """
    Get a predefined list crawler pattern by name.

    Args:
        name: Pattern name (e.g., "seu_news", "university_news")

    Returns:
        ListPattern instance

    Raises:
        ValueError: If pattern name is not found
    """
    if name not in PREDEFINED_PATTERNS:
        available = ", ".join(PREDEFINED_PATTERNS.keys())
        raise ValueError(f"Pattern '{name}' not found. Available: {available}")

    return PREDEFINED_PATTERNS[name]


def list_patterns() -> List[str]:
    """List all available pattern names."""
    return list(PREDEFINED_PATTERNS.keys())


def pattern_to_config(pattern: ListPattern) -> Dict[str, Any]:
    """
    Convert a ListPattern to config format.

    Args:
        pattern: ListPattern instance

    Returns:
        Dictionary suitable for config.crawler_patterns
    """
    config = {
        "list_container": {
            "tag": pattern.list_container["tag"],
            "class": pattern.list_container.get("class"),
        },
        "item_selector": {
            "tag": pattern.item_selector["tag"],
            "class": pattern.item_selector.get("class"),
        },
        "title_selector": {
            "type": pattern.title_selector["type"],
            "class": pattern.title_selector.get("class"),
            "link": pattern.title_selector.get("link", False),
        },
        "url_selector": {
            "type": pattern.url_selector["type"],
            "class": pattern.url_selector.get("class"),
            "link": pattern.url_selector.get("link", False),
        },
    }

    # Add optional selectors
    if pattern.date_selector:
        config["date_selector"] = {
            "type": pattern.date_selector["type"],
            "class": pattern.date_selector.get("class"),
        }

    if pattern.content_selector:
        config["content_selector"] = {
            "type": pattern.content_selector["type"],
            "class": pattern.content_selector.get("class"),
        }

    if pattern.post_process:
        config["post_process"] = pattern.post_process

    return config


def create_custom_pattern(
    name: str,
    description: str,
    list_container_tag: str,
    list_container_class: str,
    item_selector_tag: str,
    item_selector_class: str,
    title_type: str,
    title_class: str = None,
    title_has_link: bool = True,
    url_type: str = None,
    url_class: str = None,
    url_has_link: bool = True,
    date_type: str = None,
    date_class: str = None,
    content_type: str = None,
    content_class: str = None,
    remove_font_tags: bool = False,
    exclude_url_patterns: List[str] = None,
    exclude_url_regex: List[str] = None,
    exclude_titles: List[str] = None,
    exclude_titles_like: List[str] = None,
    exclude_title_regex: List[str] = None,
    min_title_length: int = 0,
    require_title: bool = False,
) -> ListPattern:
    """
    Create a custom list crawler pattern programmatically.

    Args:
        name: Pattern name
        description: Pattern description
        list_container_tag: HTML tag for article list container
        list_container_class: CSS class for article list container
        item_selector_tag: HTML tag for individual items
        item_selector_class: CSS class for individual items
        title_type: Type of title extraction ("span", "h3", "direct", etc.)
        title_class: CSS class for title element
        title_has_link: Whether title contains a link
        url_type: Type of URL extraction (defaults to title_type)
        url_class: CSS class for URL element (defaults to title_class)
        url_has_link: Whether URL is in a link element
        date_type: Type of date extraction
        date_class: CSS class for date element
        content_type: Type of content extraction
        content_class: CSS class for content element
        remove_font_tags: Whether to remove font tags from titles
        exclude_url_patterns: List of URL substrings to exclude (case-insensitive)
        exclude_url_regex: List of regex patterns to match against URL for exclusion
        exclude_titles: List of exact title strings to exclude
        exclude_titles_like: List of substrings to match in title for exclusion
        exclude_title_regex: List of regex patterns to match against title for exclusion
        min_title_length: Minimum title length (0 = no minimum)
        require_title: Whether title is required (items without title will be excluded)

    Returns:
        ListPattern instance
    """
    if url_type is None:
        url_type = title_type
    if url_class is None:
        url_class = title_class

    list_container = {"tag": list_container_tag}
    if list_container_class:
        list_container["class"] = list_container_class

    item_selector = {"tag": item_selector_tag}
    if item_selector_class:
        item_selector["class"] = item_selector_class

    title_selector = {"type": title_type, "link": title_has_link}
    if title_class:
        title_selector["class"] = title_class

    url_selector = {"type": url_type, "link": url_has_link}
    if url_class:
        url_selector["class"] = url_class

    date_selector = None
    if date_type:
        date_selector = {"type": date_type}
        if date_class:
            date_selector["class"] = date_class

    content_selector = None
    if content_type:
        content_selector = {"type": content_type}
        if content_class:
            content_selector["class"] = content_class

    post_process = {}
    if remove_font_tags:
        post_process["remove_font_tags"] = True
    
    # Add exclusion filters
    if exclude_url_patterns:
        post_process["exclude_url_patterns"] = exclude_url_patterns
    if exclude_url_regex:
        post_process["exclude_url_regex"] = exclude_url_regex
    if exclude_titles:
        post_process["exclude_titles"] = exclude_titles
    if exclude_titles_like:
        post_process["exclude_titles_like"] = exclude_titles_like
    if exclude_title_regex:
        post_process["exclude_title_regex"] = exclude_title_regex
    if min_title_length > 0:
        post_process["min_title_length"] = min_title_length
    if require_title:
        post_process["require_title"] = require_title

    return ListPattern(
        name=name,
        description=description,
        list_container=list_container,
        item_selector=item_selector,
        title_selector=title_selector,
        url_selector=url_selector,
        date_selector=date_selector,
        content_selector=content_selector,
        post_process=post_process,
    )


__all__ = [
    "ListPattern",
    "PREDEFINED_PATTERNS",
    "get_pattern",
    "list_patterns",
    "pattern_to_config",
    "create_custom_pattern",
]
