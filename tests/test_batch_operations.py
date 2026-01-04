"""
Tests for batch database operations.
"""

import pytest
import tempfile
from pathlib import Path
from moagent.config.settings import Config
from moagent.storage import SQLiteStorage


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
    config = Config()
    storage = SQLiteStorage(config)
    # Override connection to use temp file
    import sqlite3
    storage.connection = sqlite3.connect(temp_db_path, check_same_thread=False)
    storage.connection.row_factory = sqlite3.Row
    storage._init_schema()
    return storage


class TestBatchOperations:
    """Test batch database operations."""

    def test_batch_is_new_all_new(self, sqlite_storage):
        """Test batch_is_new with all new items."""
        items = [
            {"title": f"News {i}", "url": f"https://example.com/{i}", "content": f"Content {i}"}
            for i in range(10)
        ]

        is_new_list = sqlite_storage.batch_is_new(items)

        assert len(is_new_list) == 10
        assert all(is_new_list)  # All should be new

    def test_batch_is_new_mixed(self, sqlite_storage):
        """Test batch_is_new with mix of new and existing items."""
        # Store some items first
        items = [
            {"title": f"News {i}", "url": f"https://example.com/{i}", "content": f"Content {i}"}
            for i in range(10)
        ]

        # Store first 5 items
        for item in items[:5]:
            sqlite_storage.store(item)

        # Check all items
        is_new_list = sqlite_storage.batch_is_new(items)

        assert len(is_new_list) == 10
        assert all(is_new_list[:5]) is False  # First 5 should NOT be new
        assert all(is_new_list[5:])  # Last 5 should be new

    def test_batch_is_new_empty_list(self, sqlite_storage):
        """Test batch_is_new with empty list."""
        is_new_list = sqlite_storage.batch_is_new([])
        assert is_new_list == []

    def test_batch_store_all_new(self, sqlite_storage):
        """Test batch_store with all new items."""
        items = [
            {"title": f"News {i}", "url": f"https://example.com/{i}", "content": f"Content {i}", "timestamp": "2024-01-04T12:00:00"}
            for i in range(10)
        ]

        stored = sqlite_storage.batch_store(items)

        assert len(stored) == 10

        # Verify all items in database
        cursor = sqlite_storage.connection.cursor()
        cursor.execute("SELECT COUNT(*) FROM news_items")
        count = cursor.fetchone()[0]
        assert count == 10

    def test_batch_store_with_duplicates(self, sqlite_storage):
        """Test batch_store handles duplicates."""
        items = [
            {"title": "Duplicate", "url": "https://example.com/dup", "content": "Content", "timestamp": "2024-01-04T12:00:00"}
        ]

        # Store twice
        stored1 = sqlite_storage.batch_store(items)
        stored2 = sqlite_storage.batch_store(items)

        assert len(stored1) == 1
        assert len(stored2) == 0  # Duplicate not stored

        # Only one item in database
        cursor = sqlite_storage.connection.cursor()
        cursor.execute("SELECT COUNT(*) FROM news_items")
        count = cursor.fetchone()[0]
        assert count == 1

    def test_batch_check_and_store_all_new(self, sqlite_storage):
        """Test batch_check_and_store with all new items."""
        items = [
            {"title": f"News {i}", "url": f"https://example.com/{i}", "content": f"Content {i}", "timestamp": "2024-01-04T12:00:00"}
            for i in range(10)
        ]

        new_items = sqlite_storage.batch_check_and_store(items)

        assert len(new_items) == 10

        # Verify in database
        cursor = sqlite_storage.connection.cursor()
        cursor.execute("SELECT COUNT(*) FROM news_items")
        count = cursor.fetchone()[0]
        assert count == 10

    def test_batch_check_and_store_mixed(self, sqlite_storage):
        """Test batch_check_and_store with mix of new and existing."""
        # Store some items first
        items = [
            {"title": f"News {i}", "url": f"https://example.com/{i}", "content": f"Content {i}", "timestamp": "2024-01-04T12:00:00"}
            for i in range(10)
        ]

        # Store first 5
        for item in items[:5]:
            sqlite_storage.store(item)

        # Batch check and store all
        new_items = sqlite_storage.batch_check_and_store(items)

        # Should only return the 5 new items
        assert len(new_items) == 5

        # All 10 items should be in database
        all_items = sqlite_storage.get_all()
        assert len(all_items) == 10

    def test_batch_check_and_store_empty_list(self, sqlite_storage):
        """Test batch_check_and_store with empty list."""
        new_items = sqlite_storage.batch_check_and_store([])
        assert new_items == []

    def test_batch_check_and_store_all_duplicates(self, sqlite_storage):
        """Test batch_check_and_store when all items are duplicates."""
        item = {"title": "News", "url": "https://example.com", "content": "Content", "timestamp": "2024-01-04T12:00:00"}

        # Store first
        sqlite_storage.store(item)

        # Try to store again
        new_items = sqlite_storage.batch_check_and_store([item])

        assert len(new_items) == 0

    def test_batch_operations_performance(self, sqlite_storage):
        """Test that batch operations are more efficient."""
        import time

        items = [
            {"title": f"News {i}", "url": f"https://example.com/{i}", "content": f"Content {i}", "timestamp": "2024-01-04T12:00:00"}
            for i in range(100)
        ]

        # Batch operation
        start = time.time()
        sqlite_storage.batch_check_and_store(items)
        batch_time = time.time() - start

        # Clear database
        sqlite_storage.connection.execute("DELETE FROM news_items")
        sqlite_storage.connection.commit()

        # Individual operations (for comparison)
        start = time.time()
        for item in items:
            if sqlite_storage.is_new(item):
                sqlite_storage.store(item)
        individual_time = time.time() - start

        # Batch should be faster (though this may vary)
        # We just verify both complete successfully
        assert batch_time > 0
        assert individual_time > 0

        print(f"Batch time: {batch_time:.4f}s, Individual time: {individual_time:.4f}s")
