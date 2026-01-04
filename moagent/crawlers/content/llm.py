"""
LLM-based fulltext crawler for intelligent article content extraction.

This crawler uses Large Language Models to extract structured article content
from HTML pages. It's particularly effective for complex or non-standard
website structures where pattern-based extraction might fail.
"""

import logging
from typing import Any, Dict, List, Optional

from ...llm.client import LLMClient, OpenAILikeClient
from .base import BaseFullTextCrawler

logger = logging.getLogger(__name__)


class LLMFullTextCrawler(BaseFullTextCrawler):
    """
    LLM-powered fulltext crawler.

    Features:
    - Intelligent content extraction using LLM APIs
    - Handles complex HTML structures
    - Extracts metadata, authors, categories
    - Fallback to pattern-based extraction
    - Configurable prompts and models

    Extraction Process:
    1. Fetch HTML content
    2. Optionally clean HTML (remove scripts, styles)
    3. Send to LLM with structured prompt
    4. Parse JSON response
    5. Validate and normalize output

    Supported Providers:
    - OpenAI (GPT-4, GPT-3.5)
    - Anthropic (Claude)
    - Local (via Ollama, etc.)
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
                # Local LLM via Ollama or similar; handled separately in _call_llm
                logger.info("Using local LLM provider for fulltext crawler")
                self._client = None
            else:
                raise ValueError(f"Unsupported LLM provider: {provider}")
        except Exception as e:  # noqa: BLE001
            logger.error(f"Failed to initialize LLM client: {e}")
            raise

    def crawl(self, url: str) -> Optional[Dict[str, Any]]:
        """
        Crawl a single article URL using LLM extraction.

        Args:
            url: Article URL to crawl

        Returns:
            Article data dictionary or None if failed
        """
        if not url:
            logger.warning("No URL provided")
            return None

        logger.info(f"LLM-based crawling: {url}")

        try:
            # Fetch HTML
            html = self._fetch_article_html(url)

            # Extract using LLM
            result = self._extract_with_llm(html, url)

            if result:
                logger.info(f"LLM extraction successful: {result['title'][:50]}...")
                return self._normalize_item(result)

            logger.warning(f"LLM extraction failed for {url}")
            return None

        except Exception as e:
            logger.error(f"LLM crawling failed for {url}: {e}")
            # Fallback to pattern-based
            logger.info("Falling back to pattern-based extraction...")
            return self._fallback_to_pattern(url)

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
            # Clean HTML before sending to LLM
            cleaned_html = self._clean_html_for_llm(html)

            # Build prompt
            prompt = self._build_extraction_prompt(cleaned_html, url)

            # Call LLM
            response = self._call_llm(prompt)

            # Parse response
            result = self._parse_llm_response(response, url)

            return result

        except Exception as e:
            logger.error(f"LLM extraction failed: {e}")
            return None

    def _clean_html_for_llm(self, html: str) -> str:
        """
        Clean HTML to reduce token usage and improve LLM focus.

        Removes:
        - Scripts and styles
        - Navigation elements
        - Comments
        - Excessive whitespace
        """
        import re

        from bs4 import BeautifulSoup

        soup = BeautifulSoup(html, 'lxml')

        # Remove unwanted elements
        for tag in soup(['script', 'style', 'nav', 'header', 'footer', 'aside', 'form', 'iframe', 'noscript']):
            tag.decompose()

        # Remove comments
        for comment in soup.find_all(string=lambda text: isinstance(text, str) and text.strip().startswith('<!--')):
            comment.extract()

        # Get cleaned HTML
        cleaned = str(soup)

        # Remove excessive whitespace
        cleaned = re.sub(r'\s+', ' ', cleaned)
        cleaned = re.sub(r'>\s+<', '><', cleaned)

        return cleaned

    def _build_extraction_prompt(self, html: str, url: str) -> str:
        """
        Build prompt for LLM extraction.

        Args:
            html: Cleaned HTML content
            url: Article URL

        Returns:
            Prompt string
        """
        # Truncate HTML if too long (to avoid token limits)
        max_html_length = 15000  # Rough estimate for ~4000 token limit
        if len(html) > max_html_length:
            html = html[:max_html_length] + "... [truncated]"

        prompt = f"""You are an expert article content extractor. Analyze the following HTML content and extract structured article information.

URL: {url}

HTML Content:
```html
{html}
```

Please extract the following information and return ONLY valid JSON:

{{
    "title": "Main article title",
    "content": "Full article text content (preserve paragraphs, formatting)",
    "timestamp": "Publication date/time (ISO format if possible)",
    "author": "Author name(s)",
    "category": "Category or tags (comma-separated)",
    "metadata": {{
        "description": "Article description/summary",
        "image": "Main image URL if available",
        "publisher": "Publisher/organization name"
    }}
}}

Rules:
1. Extract the MAIN article title (not site title)
2. Extract FULL content - include all paragraphs, don't summarize
3. Clean up content: remove extra whitespace, preserve paragraphs
4. If a field is not available, use empty string ""
5. Convert dates to ISO format when possible (YYYY-MM-DDTHH:MM:SS)
6. Return ONLY JSON, no other text or explanations
7. Ensure JSON is valid and parseable

Focus on:
- Main article content (not sidebars, ads, navigation)
- Author bylines
- Publication dates
- Categories/tags
- Article description/summary
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
            # Local LLM via Ollama
            import json

            import requests

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

    def _parse_llm_response(self, response: str, url: str) -> Optional[Dict[str, Any]]:
        """
        Parse LLM response into structured data.

        Args:
            response: LLM response string
            url: Article URL

        Returns:
            Structured article data or None
        """
        import json
        import re

        try:
            # Extract JSON from response
            # Handle cases where LLM might add explanations
            json_match = re.search(r'\{[\s\S]*\}', response)
            if not json_match:
                raise ValueError("No JSON found in LLM response")

            data = json.loads(json_match.group(0))

            # Validate and normalize
            title = data.get("title", "")
            content = data.get("content", "")
            timestamp = data.get("timestamp", "")
            author = data.get("author", "")
            category = data.get("category", "")
            metadata = data.get("metadata", {})

            # Clean content
            content = self._clean_extracted_content(content)

            # Validate minimum requirements
            if not content and not title:
                logger.warning("LLM returned no usable content")
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
                "raw": response[:500] if len(response) > 500 else response
            }

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM response as JSON: {e}")
            logger.debug(f"Raw response: {response}")
            return None
        except Exception as e:
            logger.error(f"Failed to parse LLM response: {e}")
            return None

    def _clean_extracted_content(self, content: str) -> str:
        """
        Clean extracted content.

        Args:
            content: Raw content from LLM

        Returns:
            Cleaned content
        """
        if not content:
            return ""

        # Remove excessive whitespace
        lines = [line.strip() for line in content.split('\n') if line.strip()]
        content = '\n\n'.join(lines)

        # Remove common artifacts
        content = content.replace('"""', '"')
        content = content.replace("'''", "'")

        return content

    def _fallback_to_pattern(self, url: str) -> Optional[Dict[str, Any]]:
        """
        Fallback to pattern-based extraction if LLM fails.

        Args:
            url: Article URL

        Returns:
            Article data or None
        """
        try:
            from .html import HtmlTextCrawler

            pattern_crawler = HtmlTextCrawler(self.config)
            return pattern_crawler.crawl(url)

        except Exception as e:
            logger.error(f"Pattern fallback also failed: {e}")
            return None

    def _normalize_item(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normalize item (inherited from base).
        """
        return super()._normalize_item(item)


__all__ = ["LLMFullTextCrawler"]