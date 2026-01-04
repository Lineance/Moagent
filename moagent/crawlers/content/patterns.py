"""
Pattern configuration system for fulltext crawlers.

This module provides predefined patterns for common website structures
and utilities for managing pattern configurations.
"""

from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional


@dataclass
class FullTextPattern:
    """Configuration for extracting article content from a specific site structure."""

    name: str
    description: str

    # Title extraction
    title_selector: Dict[str, Any] = field(default_factory=dict)

    # Content extraction
    content_selector: Dict[str, Any] = field(default_factory=dict)

    # Metadata extraction
    timestamp_selector: Dict[str, Any] = field(default_factory=dict)
    author_selector: Dict[str, Any] = field(default_factory=dict)
    category_selector: Dict[str, Any] = field(default_factory=dict)

    # Additional metadata fields
    metadata_selectors: Dict[str, Dict[str, Any]] = field(default_factory=dict)

    # Post-processing rules
    post_process: Dict[str, Any] = field(default_factory=dict)

    # Match criteria (optional function to check if pattern applies)
    match_criteria: Optional[Dict[str, Any]] = None


# Predefined fulltext patterns for common website structures
PREDEFINED_FULLTEXT_PATTERNS = {
    # Modern news sites with article tags
    "modern_news": FullTextPattern(
        name="modern_news",
        description="Modern news sites using <article> tag and semantic HTML5",
        title_selector={
            "type": "css",
            "selector": "h1, h1.article-title, h1.entry-title, h1.post-title",
            "attribute": "text"
        },
        content_selector={
            "type": "css",
            "selector": "article, .article-content, .entry-content, .post-content",
            "attribute": "text"
        },
        timestamp_selector={
            "type": "css",
            "selector": "time, .date, .published, .timestamp",
            "attribute": "text"
        },
        author_selector={
            "type": "css",
            "selector": ".author, .byline, [rel='author'], .article-author",
            "attribute": "text"
        },
        category_selector={
            "type": "css",
            "selector": ".category, .tags, .topic, .article-category",
            "attribute": "text",
            "multiple": True,
            "join_with": ", "
        },
        metadata_selectors={
            "description": {
                "type": "css",
                "selector": "meta[name='description'], .excerpt, .summary",
                "attribute": "content"
            },
            "image": {
                "type": "css",
                "selector": "meta[property='og:image'], img.featured",
                "attribute": "content"
            }
        },
        post_process={
            "remove_empty_lines": True,
            "trim_whitespace": True,
            "max_length": 50000
        }
    ),

    # Traditional news sites with div containers
    "traditional_news": FullTextPattern(
        name="traditional_news",
        description="Traditional news sites with div-based content containers",
        title_selector={
            "type": "css",
            "selector": "h1, h2.title, h2.news-title, .article-title",
            "attribute": "text"
        },
        content_selector={
            "type": "css",
            "selector": "div.content, div.article, div.main-content, div#content, div.article-body",
            "attribute": "text"
        },
        timestamp_selector={
            "type": "css",
            "selector": "span.date, span.time, div.date, .publish-date",
            "attribute": "text"
        },
        author_selector={
            "type": "css",
            "selector": "span.author, div.author, .byline",
            "attribute": "text"
        },
        category_selector={
            "type": "css",
            "selector": "span.category, div.tags, .news-category",
            "attribute": "text"
        },
        metadata_selectors={
            "description": {
                "type": "css",
                "selector": "meta[name='description'], .article-excerpt",
                "attribute": "content"
            }
        },
        post_process={
            "remove_empty_lines": True,
            "trim_whitespace": True
        }
    ),

    # Blog-style sites
    "blog_style": FullTextPattern(
        name="blog_style",
        description="Blog platforms and personal websites",
        title_selector={
            "type": "css",
            "selector": "h1.entry-title, h1.post-title, h1.blog-title",
            "attribute": "text"
        },
        content_selector={
            "type": "css",
            "selector": "div.entry-content, div.post-content, div.post-body, article.post",
            "attribute": "text"
        },
        timestamp_selector={
            "type": "css",
            "selector": "time.published, time.entry-date, .post-date",
            "attribute": "text"
        },
        author_selector={
            "type": "css",
            "selector": "span.author, a.author, .post-author",
            "attribute": "text"
        },
        category_selector={
            "type": "css",
            "selector": "span.category, a.category, .post-categories",
            "attribute": "text",
            "multiple": True,
            "join_with": ", "
        },
        metadata_selectors={
            "description": {
                "type": "css",
                "selector": "meta[name='description'], .post-excerpt",
                "attribute": "content"
            }
        },
        post_process={
            "remove_empty_lines": True,
            "trim_whitespace": True
        }
    ),

    # SEU News specific pattern
    "seu_news": FullTextPattern(
        name="seu_news",
        description="Southeast University news portal (wjx.seu.edu.cn)",
        title_selector={
            "type": "css",
            "selector": "h1, h1.title, .article-title, .news-title",
            "attribute": "text"
        },
        content_selector={
            "type": "css",
            "selector": "div.content, div.article-content, div#content, div.news-content",
            "attribute": "text"
        },
        timestamp_selector={
            "type": "css",
            "selector": "span.date, .publish-time, time, .news-date",
            "attribute": "text"
        },
        author_selector={
            "type": "css",
            "selector": "span.author, .article-author, .news-author",
            "attribute": "text"
        },
        category_selector={
            "type": "css",
            "selector": "span.category, .news-category, .tags",
            "attribute": "text"
        },
        metadata_selectors={
            "description": {
                "type": "css",
                "selector": "meta[name='description'], .news-summary",
                "attribute": "content"
            },
            "source": {
                "type": "css",
                "selector": ".news-source, .source",
                "attribute": "text"
            }
        },
        post_process={
            "remove_empty_lines": True,
            "trim_whitespace": True,
            "max_length": 50000,
            "exclude_patterns": [
                r'相关阅读',
                r'相关新闻',
                r'猜你喜欢'
            ]
        }
    ),

    # Corporate/organization sites
    "corporate_news": FullTextPattern(
        name="corporate_news",
        description="Corporate press releases and news sections",
        title_selector={
            "type": "css",
            "selector": "h1, h1.title, .press-title, .news-title",
            "attribute": "text"
        },
        content_selector={
            "type": "css",
            "selector": "div.press-content, div.news-body, article.release",
            "attribute": "text"
        },
        timestamp_selector={
            "type": "css",
            "selector": "span.date, .release-date, time",
            "attribute": "text"
        },
        author_selector={
            "type": "css",
            "selector": "span.author, .press-contact, .release-author",
            "attribute": "text"
        },
        category_selector={
            "type": "css",
            "selector": ".category, .tags",
            "attribute": "text"
        },
        metadata_selectors={
            "description": {
                "type": "css",
                "selector": "meta[name='description'], .press-summary",
                "attribute": "content"
            },
            "contact": {
                "type": "css",
                "selector": ".contact-info, .media-contact",
                "attribute": "text"
            }
        },
        post_process={
            "remove_empty_lines": True,
            "trim_whitespace": True
        }
    ),

    # Academic/research sites
    "academic_news": FullTextPattern(
        name="academic_news",
        description="University and academic institution news",
        title_selector={
            "type": "css",
            "selector": "h1, h1.title, .article-title",
            "attribute": "text"
        },
        content_selector={
            "type": "css",
            "selector": "div.content, div.article, .news-body",
            "attribute": "text"
        },
        timestamp_selector={
            "type": "css",
            "selector": "span.date, time, .pub-date",
            "attribute": "text"
        },
        author_selector={
            "type": "css",
            "selector": "span.author, .byline, .writer",
            "attribute": "text"
        },
        category_selector={
            "type": "css",
            "selector": ".category, .department, .research-area",
            "attribute": "text"
        },
        metadata_selectors={
            "description": {
                "type": "css",
                "selector": "meta[name='description'], .abstract",
                "attribute": "content"
            },
            "department": {
                "type": "css",
                "selector": ".dept, .department",
                "attribute": "text"
            }
        },
        post_process={
            "remove_empty_lines": True,
            "trim_whitespace": True
        }
    )
}


def get_pattern(name: str) -> Optional[FullTextPattern]:
    """
    Get a predefined pattern by name.

    Args:
        name: Pattern name

    Returns:
        FullTextPattern or None if not found
    """
    return PREDEFINED_FULLTEXT_PATTERNS.get(name)


def list_patterns() -> List[str]:
    """
    List all available predefined pattern names.

    Returns:
        List of pattern names
    """
    return list(PREDEFINED_FULLTEXT_PATTERNS.keys())


def pattern_to_config(pattern: FullTextPattern) -> Dict[str, Any]:
    """
    Convert FullTextPattern to configuration dictionary.

    Args:
        pattern: FullTextPattern instance

    Returns:
        Configuration dictionary
    """
    config = {
        "title": pattern.title_selector,
        "content": pattern.content_selector,
        "timestamp": pattern.timestamp_selector,
        "author": pattern.author_selector,
        "category": pattern.category_selector,
        "metadata": pattern.metadata_selectors,
        "post_process": pattern.post_process
    }
    return config


def create_custom_pattern(
    name: str,
    description: str,
    title_selector: Dict[str, Any],
    content_selector: Dict[str, Any],
    timestamp_selector: Optional[Dict[str, Any]] = None,
    author_selector: Optional[Dict[str, Any]] = None,
    category_selector: Optional[Dict[str, Any]] = None,
    metadata_selectors: Optional[Dict[str, Dict[str, Any]]] = None,
    post_process: Optional[Dict[str, Any]] = None
) -> FullTextPattern:
    """
    Create a custom pattern.

    Args:
        name: Pattern name
        description: Pattern description
        title_selector: Title extraction configuration
        content_selector: Content extraction configuration
        timestamp_selector: Timestamp extraction configuration
        author_selector: Author extraction configuration
        category_selector: Category extraction configuration
        metadata_selectors: Additional metadata configurations
        post_process: Post-processing rules

    Returns:
        FullTextPattern instance
    """
    return FullTextPattern(
        name=name,
        description=description,
        title_selector=title_selector,
        content_selector=content_selector,
        timestamp_selector=timestamp_selector or {},
        author_selector=author_selector or {},
        category_selector=category_selector or {},
        metadata_selectors=metadata_selectors or {},
        post_process=post_process or {}
    )


# Example configurations for common use cases
EXAMPLE_CONFIGS = {
    "seu_news_config": {
        "pattern_name": "seu_news",
        "custom_selectors": {
            "title": {
                "type": "css",
                "selector": "h1.title",
                "attribute": "text"
            },
            "content": {
                "type": "css",
                "selector": "div#content",
                "attribute": "text"
            }
        }
    },

    "llm_extraction": {
        "provider": "openai",
        "model": "gpt-4o-mini",
        "prompt_template": "standard"
    },

    "hybrid_extraction": {
        "primary": "pattern",
        "fallback": "llm",
        "pattern_name": "modern_news"
    }
}


__all__ = [
    "FullTextPattern",
    "PREDEFINED_FULLTEXT_PATTERNS",
    "get_pattern",
    "list_patterns",
    "pattern_to_config",
    "create_custom_pattern",
    "EXAMPLE_CONFIGS"
]