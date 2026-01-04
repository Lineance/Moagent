"""
LLM-powered parser for intelligent content extraction.
"""

import logging
import json
import re
from typing import Dict, Any, Optional

from .base import BaseParser
from ..llm.client import get_llm_client, LLMClient

logger = logging.getLogger(__name__)


class LLMParser(BaseParser):
    """LLM-powered parser for intelligent content extraction."""

    def __init__(self, config):
        super().__init__(config)
        self._client: LLMClient = get_llm_client(config=config)

    def parse(self, raw_item: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Parse raw item using LLM.

        Args:
            raw_item: Raw item from crawler

        Returns:
            Parsed item or None
        """
        try:
            # Build prompt
            prompt = self._build_prompt(raw_item)

            # Call LLM
            response = self._call_llm(prompt)

            # Parse response
            parsed = self._parse_llm_response(response, raw_item)

            if parsed:
                parsed["hash"] = self._extract_hash(parsed)

            return parsed

        except Exception as e:
            logger.error(f"LLM parsing failed: {e}")
            # Fallback to generic parser
            from .generic import GenericParser
            fallback = GenericParser(self.config)
            return fallback.parse(raw_item)

    def _build_prompt(self, item: Dict[str, Any]) -> str:
        """Build prompt for LLM."""
        content = json.dumps(item, indent=2, ensure_ascii=False)

        prompt = f"""You are a news article parser. Extract structured information from the following raw news data.

Raw data:
{content}

Please extract:
1. Title (main headline)
2. URL (link to article)
3. Content (main text, summary)
4. Timestamp (publication date/time)
5. Author (if available)
6. Category/Tags (if available)

Return ONLY valid JSON with these fields:
{{
    "title": "...",
    "url": "...",
    "content": "...",
    "timestamp": "...",
    "author": "...",
    "category": "..."
}}

Rules:
- If a field is not available, use empty string
- Clean and normalize text
- Convert timestamps to ISO format if possible
- Return only JSON, no other text
"""

        return prompt

    def _call_llm(self, prompt: str) -> str:
        """Call LLM API via unified client."""
        messages = [{"role": "user", "content": prompt}]
        return self._client.chat(
            messages,
            model=self.config.llm_model,
            temperature=0.1,
            max_tokens=1000,
        )

    def _parse_llm_response(self, response: str, raw_item: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Parse LLM response."""
        try:
            # Extract JSON from response
            json_match = re.search(r'\{[\s\S]*\}', response)
            if not json_match:
                raise ValueError("No JSON found in LLM response")

            data = json.loads(json_match.group(0))

            # Normalize
            parsed = {
                "title": self._clean_text(data.get("title", "")),
                "url": data.get("url", raw_item.get("url", "")),
                "content": self._clean_text(data.get("content", "")),
                "timestamp": self._normalize_timestamp(data.get("timestamp", "")),
                "author": self._clean_text(data.get("author", "")),
                "category": self._clean_text(data.get("category", "")),
                "source": "llm",
                "raw": raw_item
            }

            return parsed

        except Exception as e:
            logger.error(f"Failed to parse LLM response: {e}")
            return None
