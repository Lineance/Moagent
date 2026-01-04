"""
LLM-based list crawler for intelligent article link discovery.

This crawler uses Large Language Models to extract article URLs from list pages,
particularly useful for complex or non-standard list structures where traditional
selectors might fail.
"""

import logging
from typing import List, Dict, Any, Optional

from .base import BaseListCrawler
from ...llm.client import OpenAILikeClient, LLMClient

logger = logging.getLogger(__name__)


class LLMListCrawler(BaseListCrawler):
    """
    LLM-powered list crawler for intelligent link discovery.

    Features:
    - Intelligent article link extraction using LLM
    - Handles complex list structures
    - Extracts titles and URLs together
    - Fallback to traditional methods
    - Configurable prompts

    Use Cases:
    - Complex JavaScript-rendered lists
    - Non-standard HTML structures
    - Sites with dynamic content loading
    - When traditional selectors fail

    Returns:
        List of {title, url, content="", timestamp, source, type}
    """

    def __init__(self, config):
        super().__init__(config)
        self._client: Optional[LLMClient] = None
        self._init_llm()

    def _init_llm(self):
        """Initialize LLM client (OpenAI/Anthropic via unified wrapper)."""
        provider = self.config.llm_provider
        try:
            if provider in ("openai", "anthropic"):
                self._client = OpenAILikeClient(self.config)
            elif provider == "local":
                logger.info("Using local LLM provider for list crawler")
                self._client = None
            else:
                raise ValueError(f"Unsupported LLM provider: {provider}")
        except Exception as e:  # noqa: BLE001
            logger.error(f"Failed to initialize LLM client: {e}")
            raise

    def crawl(self) -> List[Dict[str, Any]]:
        """
        Extract article links from list page using LLM.

        Returns:
            List of {title, url, content="", timestamp, source, type}
        """
        if not self.config.target_url:
            logger.warning("No target URL configured")
            return []

        logger.info(f"LLM list crawling: {self.config.target_url}")

        try:
            # Fetch HTML
            html = self._fetch_list_html()

            # Extract using LLM
            items = self._extract_links_with_llm(html)

            if items:
                logger.info(f"LLM extracted {len(items)} article links")
                return [self._normalize_item(item) for item in items]

            # Fallback to traditional extraction
            logger.info("LLM extraction failed, falling back to traditional methods")
            return self._fallback_traditional(html)

        except Exception as e:
            logger.error(f"LLM list crawling failed: {e}")
            return []

    def _fetch_list_html(self) -> str:
        """
        Fetch HTML from list page.

        Returns:
            HTML content
        """
        import requests
        import time

        for attempt in range(self.max_retries):
            try:
                response = requests.get(
                    self.config.target_url,
                    headers=self.headers,
                    timeout=self.timeout
                )
                response.raise_for_status()
                response.encoding = response.apparent_encoding
                return response.text
            except Exception as e:
                logger.warning(f"Attempt {attempt + 1} failed: {e}")
                if attempt < self.max_retries - 1:
                    time.sleep(2 ** attempt)
                else:
                    raise

    def _extract_links_with_llm(self, html: str) -> List[Dict[str, Any]]:
        """
        Extract article links using LLM.

        Args:
            html: HTML content

        Returns:
            List of article dictionaries
        """
        try:
            # Clean HTML
            cleaned_html = self._clean_html_for_llm(html)

            # Build prompt
            prompt = self._build_list_extraction_prompt(cleaned_html)

            # Call LLM
            response = self._call_llm(prompt)

            # Parse response
            items = self._parse_llm_list_response(response)

            return items

        except Exception as e:
            logger.error(f"LLM list extraction failed: {e}")
            return []

    def _clean_html_for_llm(self, html: str) -> str:
        """
        Clean HTML to reduce token usage.

        Args:
            html: Raw HTML

        Returns:
            Cleaned HTML
        """
        from bs4 import BeautifulSoup
        import re

        soup = BeautifulSoup(html, 'lxml')

        # Remove unwanted elements
        for tag in soup(['script', 'style', 'nav', 'header', 'footer', 'aside', 'form', 'iframe']):
            tag.decompose()

        # Remove comments
        for comment in soup.find_all(string=lambda text: isinstance(text, str) and text.strip().startswith('<!--')):
            comment.extract()

        cleaned = str(soup)
        cleaned = re.sub(r'\s+', ' ', cleaned)
        cleaned = re.sub(r'>\s+<', '><', cleaned)

        return cleaned

    def _build_list_extraction_prompt(self, html: str) -> str:
        """
        Build prompt for list extraction.

        Args:
            html: Cleaned HTML

        Returns:
            Prompt string
        """
        # Truncate if too long
        max_length = 15000
        if len(html) > max_length:
            html = html[:max_length] + "... [truncated]"

        prompt = f"""You are an expert article link extractor. Analyze the following HTML list page and extract article links.

HTML Content:
```html
{html}
```

Please extract ALL article links and return ONLY valid JSON:

{{
    "articles": [
        {{
            "title": "Article Title 1",
            "url": "https://example.com/article1",
            "timestamp": "2024-01-01 (if visible)",
            "type": "article"
        }},
        {{
            "title": "Article Title 2",
            "url": "https://example.com/article2",
            "timestamp": "2024-01-02 (if visible)",
            "type": "article"
        }}
    ]
}}

Rules:
1. Extract ALL article links from the list
2. Include the full URL (handle relative URLs)
3. Extract titles accurately
4. Include timestamps if visible
5. Return 5-20 articles (most recent/relevant first)
6. Return ONLY JSON, no explanations
7. Ensure JSON is valid and parseable

Focus on:
- Main content area (not navigation, ads, sidebars)
- Article titles and their links
- Date information if available
- Exclude non-article links (login, contact, etc.)
"""

        return prompt

    def _call_llm(self, prompt: str) -> str:
        """
        Call LLM API.

        Args:
            prompt: Prompt string

        Returns:
            LLM response
        """
        provider = self.config.llm_provider

        if provider in ("openai", "anthropic"):
            if not self._client:
                raise RuntimeError("LLM client not initialized")
            messages = [{"role": "user", "content": prompt}]
            return self._client.chat(
                messages,
                model=self.config.llm_model,
                temperature=0.1,
                max_tokens=2000,
            )

        if provider == "local":
            import requests
            import json

            payload = {
                "model": self.config.llm_model,
                "prompt": prompt,
                "stream": False,
                "format": "json",
                "options": {
                    "temperature": 0.1,
                    "num_predict": 2000
                }
            }

            response = requests.post(
                "http://localhost:11434/api/generate",
                json=payload,
                timeout=60
            )
            response.raise_for_status()
            result = response.json()
            return result.get("response", "")

        raise ValueError(f"Unsupported provider: {provider}")

    def _parse_llm_list_response(self, response: str) -> List[Dict[str, Any]]:
        """
        Parse LLM response into list of articles.

        Args:
            response: LLM response

        Returns:
            List of article dictionaries
        """
        import json
        import re
        from urllib.parse import urljoin
        from datetime import datetime

        try:
            # Extract JSON
            json_match = re.search(r'\{[\s\S]*\}', response)
            if not json_match:
                raise ValueError("No JSON found in LLM response")

            data = json.loads(json_match.group(0))

            # Extract articles list
            articles = data.get("articles", [])
            if not articles:
                return []

            # Normalize and validate
            normalized = []
            for article in articles:
                title = article.get("title", "").strip()
                url = article.get("url", "").strip()
                timestamp = article.get("timestamp", "")

                # Validate
                if not title or not url:
                    continue

                # Handle relative URLs
                if not url.startswith(('http://', 'https://')):
                    url = urljoin(self.config.target_url, url)

                # Normalize timestamp
                if not timestamp:
                    timestamp = datetime.now().isoformat()

                normalized.append({
                    "title": title,
                    "url": url,
                    "content": "",
                    "timestamp": timestamp,
                    "source": self.config.target_url,
                    "type": article.get("type", "article"),
                    "raw": str(article)
                })

            return normalized

        except Exception as e:
            logger.error(f"Failed to parse LLM list response: {e}")
            return []

    def _fallback_traditional(self, html: str) -> List[Dict[str, Any]]:
        """
        Fallback to traditional extraction methods.

        Args:
            html: HTML content

        Returns:
            List of article dictionaries
        """
        from bs4 import BeautifulSoup
        from urllib.parse import urljoin
        from datetime import datetime

        soup = BeautifulSoup(html, 'lxml')
        items = []

        # Find all links
        links = soup.find_all('a', href=True)

        for link in links[:30]:  # Limit to 30
            href = link.get('href', '')
            if not href or href.startswith(('#', 'javascript:', 'mailto:')):
                continue

            # Handle relative URLs
            if href.startswith(('http://', 'https://')):
                url = href
            else:
                url = urljoin(self.config.target_url, href)

            title = link.get_text(strip=True)
            if not title or len(title) < 3:
                continue

            items.append({
                "title": title,
                "url": url,
                "content": "",
                "timestamp": datetime.now().isoformat(),
                "source": self.config.target_url,
                "type": "html",
                "raw": str(link)
            })

        return items


class HybridListCrawler(BaseListCrawler):
    """
    Hybrid list crawler with intelligent fallback.

    Combines traditional and LLM methods for best results.
    """

    def crawl(self) -> List[Dict[str, Any]]:
        """
        Extract links using hybrid approach.

        Returns:
            List of article dictionaries
        """
        if not self.config.target_url:
            logger.warning("No target URL configured")
            return []

        logger.info(f"Hybrid list crawling: {self.config.target_url}")

        # Stage 1: Try traditional methods first (faster)
        logger.debug("Stage 1: Traditional extraction")
        try:
            from .html import HTMLListCrawler
            traditional = HTMLListCrawler(self.config)
            results = traditional.crawl()
            if results and len(results) >= 3:
                logger.info(f"Traditional extraction successful: {len(results)} items")
                return results
            logger.debug("Traditional extraction insufficient")
        except Exception as e:
            logger.debug(f"Traditional extraction failed: {e}")

        # Stage 2: Try LLM extraction
        logger.debug("Stage 2: LLM extraction")
        try:
            llm = LLMListCrawler(self.config)
            results = llm.crawl()
            if results:
                logger.info(f"LLM extraction successful: {len(results)} items")
                return results
            logger.debug("LLM extraction failed")
        except Exception as e:
            logger.debug(f"LLM extraction failed: {e}")

        logger.warning("All extraction methods failed")
        return []


__all__ = ["LLMListCrawler", "HybridListCrawler"]