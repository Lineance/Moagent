"""
Fulltext crawler module - specialized for extracting complete article content.

This module provides crawlers that focus exclusively on extracting full article
content from individual article pages, NOT on discovering links from list pages.

Architecture:
    BaseFullTextCrawler: Abstract base class
    PatternFullTextCrawler: Pattern-based extraction (CSS, XPath, regex)
    LLMFullTextCrawler: LLM-powered intelligent extraction
    HybridFullTextCrawler: Combines pattern + LLM with fallback

All crawlers return complete article dictionaries with full content and metadata.

Key Features:
- Pattern-based extraction with configurable selectors
- LLM-powered extraction for complex structures
- Hybrid mode with intelligent fallback
- Predefined patterns for common news sites
- Support for SEU news portal and similar sites

Usage:
    from moagent.crawlers.fulltextcrawler import get_fulltext_crawler
    from moagent.config.settings import Config

    # Pattern-based extraction
    config = Config(article_patterns={"pattern_name": "seu_news"})
    crawler = get_fulltext_crawler(config, mode="pattern")
    article = crawler.crawl("https://example.com/article/123")

    # LLM-based extraction
    config = Config(llm_provider="openai", openai_api_key="sk-...")
    crawler = get_fulltext_crawler(config, mode="llm")
    article = crawler.crawl("https://example.com/article/123")

    # Hybrid mode (recommended)
    crawler = get_fulltext_crawler(config, mode="hybrid")
    articles = crawler.crawl_batch(urls)
"""

import logging
from typing import Any, Dict, List, Optional, Union

from ...config.settings import Config
from ..list.llm import HybridListCrawler, LLMListCrawler
from .base import BaseFullTextCrawler
from .dynamic import DynamicFullTextCrawler
from .html import HtmlTextCrawler
from .llm import LLMFullTextCrawler
from .patterns import PREDEFINED_FULLTEXT_PATTERNS, get_pattern, pattern_to_config

logger = logging.getLogger(__name__)


class HybridFullTextCrawler(BaseFullTextCrawler):
    """
    Hybrid fulltext crawler with intelligent fallback logic.

    This crawler implements a smart multi-stage approach:
    1. First tries pattern-based extraction (fast, deterministic)
    2. If pattern fails or returns poor results, falls back to LLM
    3. Combines results for maximum accuracy

    This provides the best balance of speed, reliability, and content quality.

    When to use:
        - Unknown site structure
        - Mixed content types
        - Need high-quality extraction
        - Want best performance with good reliability
    """

    def crawl(self, url: str) -> Optional[Dict[str, Any]]:
        """
        Crawl article URL with hybrid approach.

        Args:
            url: Article URL

        Returns:
            Article data or None
        """
        if not url:
            logger.warning("No URL provided")
            return None

        logger.info(f"Hybrid crawling: {url}")

        # Stage 1: Try pattern-based extraction
        logger.debug("Stage 1: Pattern-based extraction")
        pattern_crawler = HtmlTextCrawler(self.config)
        try:
            result = pattern_crawler.crawl(url)
            if result and self._is_quality_result(result):
                logger.info("Pattern extraction successful and quality")
                return result
            logger.debug("Pattern extraction failed or low quality")
        except Exception as e:
            logger.debug(f"Pattern extraction failed: {e}")

        # Stage 2: Try LLM extraction
        logger.debug("Stage 2: LLM-based extraction")
        try:
            llm_crawler = LLMFullTextCrawler(self.config)
            result = llm_crawler.crawl(url)
            if result:
                logger.info("LLM extraction successful")
                return result
            logger.debug("LLM extraction failed")
        except Exception as e:
            logger.debug(f"LLM extraction failed: {e}")

        # Stage 3: Try structured data extraction
        logger.debug("Stage 3: Structured data extraction")
        try:
            html = self._fetch_article_html(url)
            result = self._extract_with_structured_data(html, url)
            if result:
                logger.info("Structured data extraction successful")
                return result
        except Exception as e:
            logger.debug(f"Structured data extraction failed: {e}")

        logger.warning(f"All extraction methods failed for {url}")
        return None

    def _is_quality_result(self, result: Dict[str, Any]) -> bool:
        """
        Check if extraction result is of sufficient quality.

        Args:
            result: Extracted article data

        Returns:
            True if quality is sufficient
        """
        content = result.get('content', '')
        title = result.get('title', '')

        # Must have content
        if not content or len(content.strip()) < 50:
            return False

        # Title should be reasonable
        if not title or len(title.strip()) < 5:
            return False

        # Content should have multiple paragraphs or reasonable length
        paragraphs = [p for p in content.split('\n') if p.strip()]
        if len(paragraphs) < 2 and len(content) < 200:
            return False

        return True


class ListToFullTextCrawler(BaseFullTextCrawler):
    """
    Pipeline crawler that converts list crawler results to full articles.

    This crawler takes a list of article URLs (from list crawlers) and
    fetches full content for each one.

    Use Cases:
    - Processing results from list crawlers
    - Batch content extraction
    - Complete pipeline testing

    Note: Slower than individual crawlers, but convenient for pipelines.
    """

    def __init__(self, config: Config, list_crawler=None):
        super().__init__(config)
        self.list_crawler = list_crawler

    def crawl(self, url: str) -> List[Dict[str, Any]]:
        """
        Crawl a list page and extract full content for all articles.

        Args:
            url: page URL

        Returns:
            List of complete article data
        """
        if not url:
            logger.warning("No URL configured")
            return []

        logger.info(f"Pipeline crawling: {url}")

        # Step 1: Extract article links
        if self.list_crawler is None:
            from .. import ListCrawler
            list_crawler = ListCrawler(self.config)
        else:
            list_crawler = self.list_crawler

        try:
            links = list_crawler.crawl()
            if not links:
                logger.warning("No article links found")
                return []
            logger.info(f"Found {len(links)} article links")
        except Exception as e:
            logger.error(f"List crawling failed: {e}")
            return []

        # Step 2: Fetch full content for each article
        return self.crawl_batch([link.get("url") for link in links if link.get("url")])

    def crawl_batch(self, urls: List[str]) -> List[Dict[str, Any]]:
        """
        Fetch full content for multiple article URLs.

        Args:
            urls: List of article URLs

        Returns:
            List of complete article data
        """
        if not urls:
            return []

        logger.info(f"Fetching full content for {len(urls)} articles")

        articles = []
        crawler = self._get_content_crawler()

        for i, url in enumerate(urls[:self.config.max_articles]):
            try:
                article = crawler.crawl(url)
                if article:
                    articles.append(article)
                    logger.info(f"({i+1}/{len(urls)}) Crawled: {article['title'][:50]}...")
                else:
                    logger.warning(f"Failed to crawl: {url}")
            except Exception as e:
                logger.warning(f"Error crawling {url}: {e}")
                continue

        logger.info(f"Pipeline complete: {len(articles)} articles with content")
        return articles

    def _get_content_crawler(self) -> BaseFullTextCrawler:
        """Get appropriate content crawler based on config."""
        mode = getattr(self.config, 'fulltext_mode', 'hybrid')

        if mode == 'pattern':
            return HtmlTextCrawler(self.config)
        elif mode == 'llm':
            return LLMFullTextCrawler(self.config)
        elif mode == 'hybrid':
            return HybridFullTextCrawler(self.config)
        else:
            return HybridFullTextCrawler(self.config)


def get_fulltext_crawler(
    config: Config,
    mode: str = "hybrid"
) -> BaseFullTextCrawler:
    """
    Factory function to get the appropriate fulltext crawler.

    Args:
        config: Configuration object
        mode: Extraction mode ("pattern", "llm", "hybrid")

    Returns:
        BaseFullTextCrawler instance

    Raises:
        ValueError: If mode is not valid

    Mode Comparison:
        - pattern: Fast, deterministic, uses CSS/XPath/regex
        - llm: Intelligent, handles complex structures, slower
        - dynamic: JavaScript rendering, handles SPAs and dynamic content
        - hybrid: Best of both, automatic fallback (recommended)
    """
    mode = mode.lower()

    if mode == "pattern":
        return HtmlTextCrawler(config)
    elif mode == "llm":
        return LLMFullTextCrawler(config)
    elif mode == "dynamic":
        return DynamicFullTextCrawler(config)
    elif mode == "hybrid":
        return HybridFullTextCrawler(config)
    else:
        raise ValueError(f"Unknown fulltext mode: {mode}")


def get_pipeline_crawler(
    config: Config,
    content_mode: str = "hybrid"
) -> ListToFullTextCrawler:
    """
    Factory function to get a pipeline crawler.

    Args:
        config: Configuration object
        content_mode: Mode for content extraction

    Returns:
        ListToFullTextCrawler instance
    """
    return ListToFullTextCrawler(config)


def extract_fulltext(
    url: str,
    config: Optional[Config] = None,
    mode: str = "hybrid"
) -> Optional[Dict[str, Any]]:
    """
    Convenience function to extract fulltext from a single URL.

    Args:
        url: Article URL
        config: Configuration (optional)
        mode: Extraction mode

    Returns:
        Article data or None
    """
    if config is None:
        config = Config()

    crawler = get_fulltext_crawler(config, mode)
    return crawler.crawl(url)


def extract_fulltext_batch(
    urls: List[str],
    config: Optional[Config] = None,
    mode: str = "hybrid"
) -> List[Dict[str, Any]]:
    """
    Convenience function to extract fulltext from multiple URLs.

    Args:
        urls: List of article URLs
        config: Configuration (optional)
        mode: Extraction mode

    Returns:
        List of article data
    """
    if config is None:
        config = Config()

    crawler = get_fulltext_crawler(config, mode)
    return crawler.crawl_batch(urls)


def list_available_patterns() -> List[str]:
    """
    List all available predefined fulltext patterns.

    Returns:
        List of pattern names
    """
    return list(PREDEFINED_FULLTEXT_PATTERNS.keys())


def get_pattern_info(name: str) -> Optional[Dict[str, Any]]:
    """
    Get information about a predefined pattern.

    Args:
        name: Pattern name

    Returns:
        Pattern information dictionary or None
    """
    pattern = get_pattern(name)
    if pattern:
        return {
            "name": pattern.name,
            "description": pattern.description,
            "config": pattern_to_config(pattern)
        }
    return None


def get_list_crawler(
    config: Config,
    mode: str = "hybrid"
) -> Union[LLMListCrawler, HybridListCrawler]:
    """
    Factory function to get the appropriate LLM-based list crawler.

    Args:
        config: Configuration object
        mode: Extraction mode ("llm", "hybrid")

    Returns:
        LLM-based list crawler instance

    Raises:
        ValueError: If mode is not valid

    Mode Comparison:
        - llm: Pure LLM extraction for complex structures
        - hybrid: Traditional + LLM with fallback (recommended)
    """
    mode = mode.lower()

    if mode == "llm":
        return LLMListCrawler(config)
    elif mode == "hybrid":
        return HybridListCrawler(config)
    else:
        raise ValueError(f"Unknown list crawler mode: {mode}")


def extract_list(
    config: Config,
    mode: str = "hybrid"
) -> List[Dict[str, Any]]:
    """
    Convenience function to extract article list from a URL.

    Args:
        config: Configuration with target_url
        mode: Extraction mode

    Returns:
        List of article dictionaries
    """
    crawler = get_list_crawler(config, mode)
    return crawler.crawl()


__all__ = [
    "BaseFullTextCrawler",
    "HtmlTextCrawler",
    "LLMFullTextCrawler",
    "DynamicFullTextCrawler",
    "HybridFullTextCrawler",
    "ListToFullTextCrawler",
    "LLMListCrawler",
    "HybridListCrawler",
    "get_fulltext_crawler",
    "get_pipeline_crawler",
    "get_list_crawler",
    "extract_fulltext",
    "extract_fulltext_batch",
    "extract_list",
    "list_available_patterns",
    "get_pattern_info",
    "PREDEFINED_FULLTEXT_PATTERNS"
]