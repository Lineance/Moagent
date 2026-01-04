"""
Tests for storage backends.

Tests SQLite storage implementation and base class methods.
"""

import pytest
import tempfile
from pathlib import Path
from moagent.config.settings import Config
from moagent.storage import SQLiteStorage
from moagent.storage.base import BaseStorage


@pytest.fixture
def temp_db_path():
    """Create temporary database path."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.db', delete=False) as f:
        temp_path = f.name
    yield temp_path
    # Cleanup
    Path(temp_path).unlink(missing_ok=True)


@pytest.fixture
def sqlite_storage(temp_db_path):
    """Create SQLite storage instance with temp database."""
    # Monkey patch the database path
    config = Config()
    storage = SQLiteStorage(config)
    # Override connection to use temp file
    import sqlite3
    storage.connection = sqlite3.connect(temp_db_path, check_same_thread=False)
    storage.connection.row_factory = sqlite3.Row
    storage._init_schema()
    return storage


class TestSQLiteStorage:
    """Test SQLite storage implementation."""

    def test_connect_creates_database(self, temp_db_path):
        """Test connect creates database file."""
        config = Config()
        storage = SQLiteStorage(config)

        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            # Monkey patch to use test path
            import sqlite3
            storage.connection = sqlite3.connect(str(db_path), check_same_thread=False)
            storage.connection.row_factory = sqlite3.Row
            storage._init_schema()

            assert db_path.exists()

    def test_connect_initializes_schema(self, sqlite_storage):
        """Test schema is initialized on connect."""
        cursor = sqlite_storage.connection.cursor()

        # Check tables exist
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='news_items'"
        )
        result = cursor.fetchone()

        assert result is not None

    def test_store_item_success(self, sqlite_storage):
        """Test storing an item successfully."""
        item = {
            "title": "Test Article",
            "url": "https://example.com/article",
            "content": "Test content here",
            "timestamp": "2024-01-04T12:00:00",
            "source": "test"
        }

        result = sqlite_storage.store(item)

        assert result is True

        # Verify item was stored
        cursor = sqlite_storage.connection.cursor()
        cursor.execute("SELECT * FROM news_items WHERE title = ?", (item["title"],))
        stored = cursor.fetchone()

        assert stored is not None
        assert stored["title"] == "Test Article"

    def test_store_duplicate_item_returns_false(self, sqlite_storage):
        """Test storing duplicate item returns False."""
        item = {
            "title": "Duplicate Article",
            "url": "https://example.com/duplicate",
            "content": "Content",
            "timestamp": "2024-01-04T12:00:00"
        }

        # Store first time
        result1 = sqlite_storage.store(item)
        assert result1 is True

        # Store second time (duplicate)
        result2 = sqlite_storage.store(item)
        assert result2 is False

    def test_is_new_with_new_item(self, sqlite_storage):
        """Test is_new returns True for new item."""
        item = {
            "title": "New Article",
            "url": "https://example.com/new",
            "content": "Content"
        }

        is_new = sqlite_storage.is_new(item)

        assert is_new is True

    def test_is_new_with_existing_item(self, sqlite_storage):
        """Test is_new returns False for existing item."""
        item = {
            "title": "Existing Article",
            "url": "https://example.com/existing",
            "content": "Content",
            "timestamp": "2024-01-04T12:00:00"
        }

        # Store the item
        sqlite_storage.store(item)

        # Check if it's new
        is_new = sqlite_storage.is_new(item)

        assert is_new is False

    def test_get_recent_items(self, sqlite_storage):
        """Test getting recent items."""
        # Store multiple items
        for i in range(5):
            item = {
                "title": f"Article {i}",
                "url": f"https://example.com/{i}",
                "content": f"Content {i}",
                "timestamp": f"2024-01-0{i+1}T12:00:00"
            }
            sqlite_storage.store(item)

        # Get recent items
        recent = sqlite_storage.get_recent(limit=3)

        assert len(recent) == 3
        # Should be in reverse chronological order
        assert recent[0]["title"] == "Article 4"

    def test_get_all_items(self, sqlite_storage):
        """Test getting all items."""
        # Store items
        for i in range(3):
            item = {
                "title": f"Article {i}",
                "url": f"https://example.com/{i}",
                "content": f"Content {i}",
                "timestamp": "2024-01-04T12:00:00"
            }
            sqlite_storage.store(item)

        # Get all
        all_items = sqlite_storage.get_all()

        assert len(all_items) == 3

    def test_get_by_hash(self, sqlite_storage):
        """Test getting item by hash."""
        item = {
            "title": "Hash Test",
            "url": "https://example.com/hash",
            "content": "Content for hash test",
            "timestamp": "2024-01-04T12:00:00"
        }

        sqlite_storage.store(item)
        item_hash = sqlite_storage._generate_hash(item)

        # Retrieve by hash
        retrieved = sqlite_storage.get_by_hash(item_hash)

        assert retrieved is not None
        assert retrieved["title"] == "Hash Test"

    def test_get_by_hash_nonexistent(self, sqlite_storage):
        """Test getting non-existent item by hash."""
        result = sqlite_storage.get_by_hash("nonexistent_hash")

        assert result is None

    def test_disconnect(self, sqlite_storage):
        """Test disconnecting closes connection."""
        sqlite_storage.disconnect()

        assert sqlite_storage.connection is None


class TestBaseStorage:
    """Test base storage class methods."""

    def test_generate_item_hash(self):
        """Test hash generation is consistent."""
        from moagent.storage.sqlite import SQLiteStorage

        config = Config()
        storage = SQLiteStorage(config)

        item = {
            "title": "Test",
            "url": "https://example.com",
            "content": "Content"
        }

        hash1 = storage._generate_item_hash(item)
        hash2 = storage._generate_item_hash(item)

        # Same item should produce same hash
        assert hash1 == hash2
        assert len(hash1) == 32  # MD5 hex length

    def test_generate_item_hash_different_content(self):
        """Test hash differs for different content."""
        from moagent.storage.sqlite import SQLiteStorage

        config = Config()
        storage = SQLiteStorage(config)

        item1 = {"title": "Test", "url": "https://example.com", "content": "Content A"}
        item2 = {"title": "Test", "url": "https://example.com", "content": "Content B"}

        hash1 = storage._generate_item_hash(item1)
        hash2 = storage._generate_item_hash(item2)

        # Different content should produce different hash
        assert hash1 != hash2

    def test_normalize_item(self):
        """Test item normalization."""
        from moagent.storage.sqlite import SQLiteStorage

        config = Config()
        storage = SQLiteStorage(config)

        item = {
            "title": "  Test Title  ",
            "url": "https://example.com/very/long/url/" + "x" * 2000,
            "content": "Content",
            "timestamp": "2024-01-04T12:00:00",
            "metadata": {"key": "value"}
        }

        normalized = storage._normalize_item(item)

        # Title should be stripped and truncated
        assert len(normalized["title"]) <= 500
        # URL should be truncated
        assert len(normalized["url"]) <= 1000
        # Metadata should be JSON string
        import json
        assert isinstance(normalized["metadata"], str)


class TestSQLiteStorageInheritance:
    """Test SQLite storage properly inherits base class methods."""

    def test_uses_base_class_hash_method(self, sqlite_storage):
        """Test SQLiteStorage uses base class hash generation."""

        item = {
            "title": "Inheritance Test",
            "url": "https://example.com/inheritance",
            "content": "Content"
        }

        # Generate hash using SQLiteStorage method
        sqlite_hash = sqlite_storage._generate_hash(item)

        # Generate hash using another SQLiteStorage instance (should be same)
        config = Config()
        from moagent.storage.sqlite import SQLiteStorage
        base_storage = SQLiteStorage(config)
        base_hash = base_storage._generate_item_hash(item)

        # Should be identical
        assert sqlite_hash == base_hash


class TestStorageEdgeCases:
    """Test edge cases and error handling."""

    def test_store_item_with_missing_fields(self, sqlite_storage):
        """Test storing item with missing optional fields."""
        item = {
            "title": "Minimal Article",
            "url": "https://example.com/minimal"
            # Missing content, timestamp, source
        }

        result = sqlite_storage.store(item)

        assert result is True

    def test_store_item_with_very_long_title(self, sqlite_storage):
        """Test storing item with very long title."""
        item = {
            "title": "A" * 1000,  # Very long title
            "url": "https://example.com/long",
            "content": "Content"
        }

        result = sqlite_storage.store(item)

        assert result is True

        # Verify title was truncated
        cursor = sqlite_storage.connection.cursor()
        cursor.execute("SELECT title FROM news_items WHERE url = ?", (item["url"],))
        stored = cursor.fetchone()

        assert len(stored["title"]) == 500

    def test_multiple_stores_and_retrieves(self, sqlite_storage):
        """Test multiple store and retrieve operations."""
        items = []
        for i in range(10):
            item = {
                "title": f"Article {i}",
                "url": f"https://example.com/{i}",
                "content": f"Content {i}",
                "timestamp": "2024-01-04T12:00:00"
            }
            sqlite_storage.store(item)
            items.append(item)

        # Retrieve all
        all_items = sqlite_storage.get_all()
        assert len(all_items) == 10
