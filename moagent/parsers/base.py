"""
Base parser class defining the interface for all parsers.
"""

import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional

from ..config.settings import Config

logger = logging.getLogger(__name__)


class BaseParser(ABC):
    """Abstract base class for all parsers."""

    def __init__(self, config: Config):
        """
        Initialize base parser.

        Args:
            config: Configuration object
        """
        self.config = config

    @abstractmethod
    def parse(self, raw_item: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Parse raw crawled item into structured data.

        Args:
            raw_item: Raw item from crawler

        Returns:
            Parsed item or None if parsing fails
        """
        pass

    def _clean_text(self, text: str) -> str:
        """
        Clean and normalize text.

        Args:
            text: Text to clean

        Returns:
            Cleaned text
        """
        import re

        if not text:
            return ""

        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text)
        # Remove special characters
        text = re.sub(r'[\u0000-\u001f\u007f-\u009f]', '', text)
        # Strip
        text = text.strip()

        return text

    def _normalize_timestamp(self, timestamp: str) -> str:
        """
        Normalize timestamp to ISO format.

        Args:
            timestamp: Raw timestamp string

        Returns:
            ISO format timestamp
        """
        import dateparser
        from datetime import datetime

        if not timestamp:
            return datetime.now().isoformat()

        try:
            # Try to parse with dateparser
            dt = dateparser.parse(timestamp)
            if dt:
                return dt.isoformat()
        except Exception:
            pass

        # Fallback: return as-is or current time
        return timestamp if timestamp else datetime.now().isoformat()

    def _extract_hash(self, item: Dict[str, Any]) -> str:
        """
        Generate hash for item deduplication.

        Args:
            item: Item dictionary

        Returns:
            Hash string
        """
        import hashlib
        import json

        # Create a normalized representation
        data = {
            "title": item.get("title", ""),
            "url": item.get("url", ""),
            "content_hash": hashlib.md5(
                item.get("content", "").encode('utf-8')
            ).hexdigest()[:16]
        }

        hash_str = hashlib.md5(
            json.dumps(data, sort_keys=True).encode('utf-8')
        ).hexdigest()

        return hash_str
