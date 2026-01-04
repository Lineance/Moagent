"""SQLite storage - simplified version.

This module provides a simplified SQLite-based storage backend for MoAgent.
It replaces the complex PostgreSQL setup with a simple file-based database
that requires no external dependencies or configuration.

Key Features:
- Zero setup: Database is auto-created
- File-based: data/moagent.db
- Hash-based deduplication: Prevents duplicate items
- Simple API: connect(), store(), is_new(), get_recent()

Database Schema:
    news_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        hash TEXT UNIQUE NOT NULL,      -- MD5 hash for deduplication
        title TEXT NOT NULL,            -- Article title (max 500 chars)
        url TEXT NOT NULL,              -- Article URL (max 1000 chars)
        content TEXT,                   -- Full article content
        timestamp TEXT NOT NULL,        -- ISO format timestamp
        source TEXT,                    -- Source identifier
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )

Hash Generation:
    Hash = MD5(JSON of {title, url, content_hash[:16]})

Usage:
    storage = SQLiteStorage(config)
    storage.connect()

    if storage.is_new(item):
        storage.store(item)

    recent = storage.get_recent(limit=10)
    all_items = storage.get_all()

    storage.disconnect()
"""

import sqlite3
import json
import hashlib
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional

from .base import BaseStorage

logger = logging.getLogger(__name__)


class SQLiteStorage(BaseStorage):
    """Simple SQLite storage for news items.

    This class provides all necessary database operations for MoAgent using
    SQLite. It's designed to be simple and require no external setup.

    Attributes:
        config: Configuration object containing database_url
        connection: SQLite connection object (None until connect() is called)

    Example:
        >>> from moagent.config.settings import Config
        >>> config = Config(database_url="sqlite:///./data/moagent.db")
        >>> storage = SQLiteStorage(config)
        >>> storage.connect()
        >>> storage.store({"title": "News", "url": "...", ...})
        >>> storage.disconnect()
    """

    def __init__(self, config):
        """Initialize SQLite storage.

        Args:
            config: Config object with database_url setting
        """
        self.config = config
        self.connection = None

    def connect(self):
        """Connect to SQLite database and initialize schema.

        Creates the data directory if it doesn't exist and establishes
        a connection to the SQLite database. The database file is created
        automatically if it doesn't exist.

        Note:
            Uses check_same_thread=False to allow the connection to be
            used across different threads (useful for async operations).
        """
        if self.connection:
            return

        db_path = "data/moagent.db"
        Path("data").mkdir(exist_ok=True)

        self.connection = sqlite3.connect(db_path, check_same_thread=False)
        self.connection.row_factory = sqlite3.Row  # Access columns by name
        self._init_schema()

    def _init_schema(self):
        """Create database schema if it doesn't exist.

        This method is called automatically when connect() is first called.
        It creates the news_items table with the required columns and
        constraints.

        Constraints:
            - id: Auto-incrementing primary key
            - hash: UNIQUE constraint prevents duplicate entries
            - title, url, timestamp: NOT NULL constraints
        """
        cursor = self.connection.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS news_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                hash TEXT UNIQUE NOT NULL,
                title TEXT NOT NULL,
                url TEXT NOT NULL,
                content TEXT,
                timestamp TEXT NOT NULL,
                source TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        self.connection.commit()

    def _generate_hash(self, item: Dict[str, Any]) -> str:
        """Generate deterministic hash for item deduplication.

        Uses the base class implementation to ensure consistency.

        Args:
            item: Dictionary containing item data with 'title', 'url', 'content' keys

        Returns:
            32-character hexadecimal MD5 hash

        Example:
            >>> item = {"title": "News", "url": "https://example.com", "content": "..."}
            >>> hash = storage._generate_hash(item)
            >>> len(hash) == 32  # True
        """
        # Use base class method for consistency
        return BaseStorage._generate_item_hash(self, item)

    def store(self, item: Dict[str, Any]) -> bool:
        """Store an item in the database.

        Args:
            item: Dictionary containing item data. Expected keys:
                  - title: Article title (truncated to 500 chars)
                  - url: Article URL (truncated to 1000 chars)
                  - content: Full article content
                  - timestamp: ISO format timestamp
                  - source: Source identifier (default: "unknown")

        Returns:
            True if stored successfully, False if duplicate

        Raises:
            sqlite3.Error: If database error occurs (except IntegrityError)

        Example:
            >>> item = {
            ...     "title": "Breaking News",
            ...     "url": "https://example.com/article",
            ...     "content": "Full article text...",
            ...     "timestamp": "2024-01-01T12:00:00",
            ...     "source": "seu_news"
            ... }
            >>> storage.store(item)
            True
        """
        if not self.connection:
            self.connect()

        hash_value = self._generate_hash(item)

        cursor = self.connection.cursor()
        try:
            cursor.execute("""
                INSERT INTO news_items (hash, title, url, content, timestamp, source)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                hash_value,
                item.get("title", "")[:500],  # Truncate to prevent overflow
                item.get("url", "")[:1000],
                item.get("content", ""),
                item.get("timestamp", ""),
                item.get("source", "unknown")
            ))
            self.connection.commit()
            logger.debug(f"Stored: {item.get('title', '')[:50]}...")
            return True
        except sqlite3.IntegrityError:
            logger.debug("Duplicate item skipped")
            return False

    def is_new(self, item: Dict[str, Any]) -> bool:
        """Check if item is new (not already in database).

        Args:
            item: Dictionary containing item data

        Returns:
            True if item is new (not found in database), False if duplicate

        Example:
            >>> if storage.is_new(item):
            ...     storage.store(item)
            ... else:
            ...     print("Duplicate, skipping")
        """
        if not self.connection:
            self.connect()

        hash_value = self._generate_hash(item)
        cursor = self.connection.cursor()
        cursor.execute("SELECT 1 FROM news_items WHERE hash = ?", (hash_value,))
        return cursor.fetchone() is None

    def get_recent(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get most recent items, ordered by timestamp.

        Args:
            limit: Maximum number of items to return (default: 10)

        Returns:
            List of item dictionaries, most recent first

        Example:
            >>> recent = storage.get_recent(limit=5)
            >>> for item in recent:
            ...     print(item["title"])
        """
        if not self.connection:
            self.connect()

        cursor = self.connection.cursor()
        cursor.execute(
            "SELECT * FROM news_items ORDER BY timestamp DESC LIMIT ?",
            (limit,)
        )
        return [dict(row) for row in cursor.fetchall()]

    def get_all(self) -> List[Dict[str, Any]]:
        """Get all items from database, ordered by timestamp.

        Returns:
            List of all item dictionaries, most recent first

        Warning:
            This can return a large number of items. Use get_recent() for
            limited results.
        """
        if not self.connection:
            self.connect()

        cursor = self.connection.cursor()
        cursor.execute("SELECT * FROM news_items ORDER BY timestamp DESC")
        return [dict(row) for row in cursor.fetchall()]

    def get_by_hash(self, hash_value: str) -> Optional[Dict[str, Any]]:
        """Retrieve a specific item by its hash.

        Args:
            hash_value: The 32-character MD5 hash of the item

        Returns:
            Item dictionary if found, None otherwise

        Example:
            >>> hash = storage._generate_hash(item)
            >>> stored = storage.get_by_hash(hash)
            >>> if stored:
            ...     print(f"Found: {stored['title']}")
        """
        if not self.connection:
            self.connect()

        cursor = self.connection.cursor()
        cursor.execute("SELECT * FROM news_items WHERE hash = ?", (hash_value,))
        row = cursor.fetchone()
        return dict(row) if row else None

    def batch_is_new(self, items: List[Dict[str, Any]]) -> List[bool]:
        """Check if multiple items are new using a single query.

        This is much more efficient than checking each item individually.

        Args:
            items: List of item dictionaries to check

        Returns:
            List of booleans indicating if each item is new

        Example:
            >>> items = [item1, item2, item3]
            >>> is_new_list = storage.batch_is_new(items)
            >>> [is_new_list[i] for i in range(len(items))]
            [True, False, True]
        """
        if not items:
            return []

        if not self.connection:
            self.connect()

        # Generate hashes for all items
        hashes = [self._generate_hash(item) for item in items]

        # Single query to check all hashes
        cursor = self.connection.cursor()
        placeholders = ','.join(['?'] * len(hashes))
        cursor.execute(
            f"SELECT hash FROM news_items WHERE hash IN ({placeholders})",
            hashes
        )
        existing_hashes = {row[0] for row in cursor.fetchall()}

        # Return True for items not in database
        return [h not in existing_hashes for h in hashes]

    def batch_check_and_store(self, items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Batch check if items are new and store them efficiently.

        Uses batch_is_new for checking and executemany for storing.

        Args:
            items: List of items to check and store

        Returns:
            List of newly stored items

        Example:
            >>> items = [item1, item2, item3]
            >>> new_items = storage.batch_check_and_store(items)
            >>> print(f"Stored {len(new_items)} new items")
        """
        if not items:
            return []

        if not self.connection:
            self.connect()

        # Check which items are new
        is_new_list = self.batch_is_new(items)

        # Filter to only new items
        new_items = [item for item, is_new in zip(items, is_new_list) if is_new]

        if not new_items:
            return []

        # Prepare data for batch insert
        insert_data = []
        for item in new_items:
            hash_value = self._generate_hash(item)
            insert_data.append((
                hash_value,
                item.get("title", "")[:500],
                item.get("url", "")[:1000],
                item.get("content", ""),
                item.get("timestamp", ""),
                item.get("source", "unknown")
            ))

        # Batch insert with executemany
        cursor = self.connection.cursor()
        try:
            cursor.executemany("""
                INSERT INTO news_items (hash, title, url, content, timestamp, source)
                VALUES (?, ?, ?, ?, ?, ?)
            """, insert_data)
            self.connection.commit()
            logger.info(f"Batch stored {len(new_items)} new items")
            return new_items
        except sqlite3.IntegrityError as e:
            logger.error(f"Batch insert failed: {e}")
            # Fall back to individual inserts
            return super().batch_check_and_store(items)

    def batch_store(self, items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Store multiple items in batch using executemany.

        Args:
            items: List of items to store

        Returns:
            List of successfully stored items
        """
        if not items:
            return []

        if not self.connection:
            self.connect()

        # Prepare data for batch insert
        insert_data = []
        for item in items:
            hash_value = self._generate_hash(item)
            insert_data.append((
                hash_value,
                item.get("title", "")[:500],
                item.get("url", "")[:1000],
                item.get("content", ""),
                item.get("timestamp", ""),
                item.get("source", "unknown")
            ))

        # Batch insert
        cursor = self.connection.cursor()
        try:
            cursor.executemany("""
                INSERT OR IGNORE INTO news_items (hash, title, url, content, timestamp, source)
                VALUES (?, ?, ?, ?, ?, ?)
            """, insert_data)
            self.connection.commit()

            # Return successfully stored items
            stored_hashes = {row[0] for row in insert_data}
            return [item for item in items
                    if self._generate_hash(item) in stored_hashes]
        except sqlite3.Error as e:
            logger.error(f"Batch store failed: {e}")
            # Fall back to individual stores
            return super().batch_store(items)

    def disconnect(self):
        """Close database connection.

        Should be called when done with the storage object to properly
        close the database connection and release resources.
        """
        if self.connection:
            self.connection.close()
            self.connection = None

    def __del__(self):
        """Destructor to ensure connection is closed.

        Note:
            This is a safety net. Always call disconnect() explicitly
            when possible.
        """
        try:
            self.disconnect()
        except:
            pass
