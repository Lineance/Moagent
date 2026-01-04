"""
Base storage class defining the interface for all storage backends.
"""

import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, List

from ..config.settings import Config

logger = logging.getLogger(__name__)


class BaseStorage(ABC):
    """Abstract base class for all storage backends."""

    def __init__(self, config: Config):
        """
        Initialize base storage.

        Args:
            config: Configuration object
        """
        self.config = config
        self.connection = None

    @abstractmethod
    def connect(self) -> None:
        """Establish database connection."""
        pass

    @abstractmethod
    def disconnect(self) -> None:
        """Close database connection."""
        pass

    @abstractmethod
    def store(self, item: Dict[str, Any]) -> None:
        """
        Store an item.

        Args:
            item: Item to store
        """
        pass

    @abstractmethod
    def is_new(self, item: Dict[str, Any]) -> bool:
        """
        Check if item is new (not already stored).

        Args:
            item: Item to check

        Returns:
            True if new, False if duplicate
        """
        pass

    @abstractmethod
    def get_all(self) -> List[Dict[str, Any]]:
        """
        Get all stored items.

        Returns:
            List of all items
        """
        pass

    @abstractmethod
    def get_recent(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get recent items.

        Args:
            limit: Number of items to return

        Returns:
            List of recent items
        """
        pass

    @abstractmethod
    def get_by_hash(self, hash_value: str) -> Dict[str, Any] | None:
        """
        Get item by hash.

        Args:
            hash_value: Hash to search for

        Returns:
            Item or None
        """
        pass

    def batch_store(self, items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Store multiple items in batch.

        Default implementation falls back to individual store calls.
        Override in subclass for better performance.

        Args:
            items: List of items to store

        Returns:
            List of successfully stored items
        """
        stored = []
        for item in items:
            try:
                if self.store(item):
                    stored.append(item)
            except Exception as e:
                logger.error(f"Failed to store item: {e}")
        return stored

    def batch_check_and_store(self, items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Batch check if items are new and store them.

        This is more efficient than checking and storing individually.

        Args:
            items: List of items to check and store

        Returns:
            List of newly stored items
        """
        new_items = []
        for item in items:
            try:
                if self.is_new(item):
                    if self.store(item):
                        new_items.append(item)
            except Exception as e:
                logger.error(f"Failed to check/store item: {e}")
        return new_items

    def batch_is_new(self, items: List[Dict[str, Any]]) -> List[bool]:
        """
        Check if multiple items are new.

        Default implementation falls back to individual is_new calls.
        Override in subclass for better performance.

        Args:
            items: List of items to check

        Returns:
            List of booleans indicating if each item is new
        """
        return [self.is_new(item) for item in items]

    def _generate_item_hash(self, item: Dict[str, Any]) -> str:
        """
        Generate hash for item deduplication.

        Args:
            item: Item dictionary

        Returns:
            Hash string
        """
        import hashlib
        import json

        # Create normalized representation
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

    def _normalize_item(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normalize item for storage.

        Args:
            item: Raw item

        Returns:
            Normalized item
        """
        normalized = {
            "title": item.get("title", "")[:500],
            "url": item.get("url", "")[:1000],
            "content": item.get("content", ""),
            "timestamp": item.get("timestamp", ""),
            "hash": item.get("hash", self._generate_item_hash(item)),
            "source": item.get("source", "unknown"),
            "author": item.get("author", ""),
            "category": item.get("category", ""),
            "metadata": item.get("metadata", {}),
        }

        # Convert metadata to JSON string if dict
        if isinstance(normalized["metadata"], dict):
            import json
            normalized["metadata"] = json.dumps(normalized["metadata"])

        return normalized
