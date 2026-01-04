"""
Tests for caching layer.
"""

import pytest
import time
from datetime import timedelta
from moagent.cache import CacheManager, CacheEntry, cached, get_cache_manager


class TestCacheEntry:
    """Test CacheEntry class."""

    def test_cache_entry_creation(self):
        """Test creating cache entry."""
        entry = CacheEntry("value", timedelta(hours=1))
        assert entry.value == "value"
        assert not entry.is_expired()

    def test_cache_entry_expiration(self):
        """Test cache entry expiration."""
        entry = CacheEntry("value", timedelta(milliseconds=10))
        time.sleep(0.05)
        assert entry.is_expired()

    def test_cache_entry_age(self):
        """Test cache entry age calculation."""
        entry = CacheEntry("value", timedelta(hours=1))
        age = entry.age()
        assert age.total_seconds() >= 0
        assert age.total_seconds() < 1  # Should be very recent


class TestCacheManager:
    """Test CacheManager class."""

    @pytest.fixture
    def cache_manager(self):
        """Create cache manager for testing."""
        manager = CacheManager()
        manager.clear()
        return manager

    def test_cache_set_and_get(self, cache_manager):
        """Test setting and getting cache values."""
        cache_manager.set("key1", "value1", "http")
        assert cache_manager.get("key1", "http") == "value1"

    def test_cache_miss(self, cache_manager):
        """Test cache miss returns None."""
        assert cache_manager.get("nonexistent", "http") is None

    def test_cache_expiration(self, cache_manager):
        """Test cache expiration."""
        cache_manager.set("key1", "value1", "http", ttl=timedelta(milliseconds=50))
        assert cache_manager.get("key1", "http") == "value1"
        time.sleep(0.1)
        assert cache_manager.get("key1", "http") is None

    def test_cache_clear_by_type(self, cache_manager):
        """Test clearing cache by type."""
        cache_manager.set("key1", "value1", "http")
        cache_manager.set("key2", "value2", "llm")

        cache_manager.clear("http")
        assert cache_manager.get("key1", "http") is None
        assert cache_manager.get("key2", "llm") == "value2"

    def test_cache_clear_all(self, cache_manager):
        """Test clearing all caches."""
        cache_manager.set("key1", "value1", "http")
        cache_manager.set("key2", "value2", "llm")
        cache_manager.set("key3", "value3", "query")

        cache_manager.clear()
        assert cache_manager.get("key1", "http") is None
        assert cache_manager.get("key2", "llm") is None
        assert cache_manager.get("key3", "query") is None

    def test_cache_stats(self, cache_manager):
        """Test cache statistics."""
        cache_manager.set("key1", "value1", "http")
        cache_manager.get("key1", "http")  # Hit
        cache_manager.get("key2", "http")  # Miss

        stats = cache_manager.get_stats()
        assert stats["hits"] == 1
        assert stats["misses"] == 1
        assert stats["http_cache_size"] == 1

    def test_cache_cleanup_expired(self, cache_manager):
        """Test cleanup of expired entries."""
        cache_manager.set("key1", "value1", "http", ttl=timedelta(milliseconds=50))
        cache_manager.set("key2", "value2", "http", ttl=timedelta(hours=1))

        time.sleep(0.1)
        removed = cache_manager.cleanup_expired()

        assert removed == 1
        assert cache_manager.get("key1", "http") is None
        assert cache_manager.get("key2", "http") == "value2"


class TestCachedDecorator:
    """Test @cached decorator."""

    def test_cached_decorator(self):
        """Test that decorator caches results."""
        call_count = [0]

        @cached(cache_type="llm")
        def expensive_function(x, y):
            call_count[0] += 1
            return x + y

        # First call
        result1 = expensive_function(2, 3)
        assert result1 == 5
        assert call_count[0] == 1

        # Second call with same args - should use cache
        result2 = expensive_function(2, 3)
        assert result2 == 5
        assert call_count[0] == 1  # Should not increment

        # Different args - should call function
        result3 = expensive_function(3, 4)
        assert result3 == 7
        assert call_count[0] == 2


class TestGlobalCacheManager:
    """Test global cache manager instance."""

    def test_get_cache_manager_singleton(self):
        """Test that get_cache_manager returns singleton."""
        manager1 = get_cache_manager()
        manager2 = get_cache_manager()
        assert manager1 is manager2
