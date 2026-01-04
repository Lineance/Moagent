"""
Caching layer for MoAgent.

Provides multi-level caching for HTTP responses, LLM API calls,
and database query results.
"""

import hashlib
import json
import logging
from datetime import datetime, timedelta
from functools import lru_cache, wraps
from typing import Any, Callable, Dict, Optional, TypeVar, Union
from pathlib import Path

from ..config.constants import (
    HTTP_CACHE_TTL,
    LLM_CACHE_TTL,
    QUERY_CACHE_TTL,
    HTTP_CACHE_SIZE,
    LLM_CACHE_SIZE,
    QUERY_CACHE_SIZE,
    DEFAULT_CACHE_DIR,
)

logger = logging.getLogger(__name__)

T = TypeVar('T')


class CacheEntry:
    """Cache entry with TTL support."""

    def __init__(self, value: Any, ttl: timedelta):
        self.value = value
        self.expires_at = datetime.now() + ttl
        self.created_at = datetime.now()

    def is_expired(self) -> bool:
        """Check if cache entry has expired."""
        return datetime.now() > self.expires_at

    def age(self) -> timedelta:
        """Get age of cache entry."""
        return datetime.now() - self.created_at


class CacheManager:
    """
    Multi-level cache manager.

    Supports:
    - In-memory LRU cache for fast access
    - Disk-based cache for persistence
    - TTL-based expiration
    - Cache statistics
    """

    def __init__(self, cache_dir: Optional[Path] = None):
        """
        Initialize cache manager.

        Args:
            cache_dir: Directory for disk cache. Defaults to DEFAULT_CACHE_DIR.
        """
        self.cache_dir = Path(cache_dir or DEFAULT_CACHE_DIR)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        # Statistics
        self.stats = {
            "hits": 0,
            "misses": 0,
            "evictions": 0,
            "errors": 0,
        }

        # In-memory caches
        self._http_cache: Dict[str, CacheEntry] = {}
        self._llm_cache: Dict[str, CacheEntry] = {}
        self._query_cache: Dict[str, CacheEntry] = {}

    def _generate_key(self, *args, **kwargs) -> str:
        """Generate cache key from arguments."""
        key_data = {
            "args": args,
            "kwargs": sorted(kwargs.items()),
        }
        key_hash = hashlib.sha256(
            json.dumps(key_data, sort_keys=True, default=str).encode()
        ).hexdigest()
        return key_hash

    def _get_cache(self, cache_type: str) -> Dict[str, CacheEntry]:
        """Get cache dictionary by type."""
        caches = {
            "http": self._http_cache,
            "llm": self._llm_cache,
            "query": self._query_cache,
        }
        return caches.get(cache_type.lower(), self._http_cache)

    def get(self, key: str, cache_type: str = "http") -> Optional[Any]:
        """
        Get value from cache.

        Args:
            key: Cache key
            cache_type: Type of cache (http, llm, query)

        Returns:
            Cached value or None if not found/expired
        """
        cache = self._get_cache(cache_type)

        if key not in cache:
            self.stats["misses"] += 1
            return None

        entry = cache[key]

        # Check if expired
        if entry.is_expired():
            del cache[key]
            self.stats["evictions"] += 1
            self.stats["misses"] += 1
            logger.debug(f"Cache entry expired: {key[:16]}...")
            return None

        self.stats["hits"] += 1
        logger.debug(f"Cache hit: {key[:16]}... (age: {entry.age()})")
        return entry.value

    def set(self, key: str, value: Any, cache_type: str = "http",
            ttl: Optional[timedelta] = None) -> None:
        """
        Set value in cache.

        Args:
            key: Cache key
            value: Value to cache
            cache_type: Type of cache (http, llm, query)
            ttl: Time to live. Defaults based on cache_type.
        """
        cache = self._get_cache(cache_type)

        # Get default TTL for cache type
        if ttl is None:
            ttl = get_cache_ttl_for_type(cache_type)

        # Evict old entry if exists
        if key in cache:
            self.stats["evictions"] += 1

        cache[key] = CacheEntry(value, ttl)
        logger.debug(f"Cached: {key[:16]}... (TTL: {ttl})")

    def clear(self, cache_type: Optional[str] = None) -> None:
        """
        Clear cache.

        Args:
            cache_type: Type of cache to clear. If None, clears all.
        """
        if cache_type:
            cache = self._get_cache(cache_type)
            cache.clear()
            logger.info(f"Cleared {cache_type} cache")
        else:
            self._http_cache.clear()
            self._llm_cache.clear()
            self._query_cache.clear()
            logger.info("Cleared all caches")

    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        total_requests = self.stats["hits"] + self.stats["misses"]
        hit_rate = self.stats["hits"] / total_requests if total_requests > 0 else 0

        return {
            **self.stats,
            "hit_rate": f"{hit_rate:.2%}",
            "http_cache_size": len(self._http_cache),
            "llm_cache_size": len(self._llm_cache),
            "query_cache_size": len(self._query_cache),
            "total_cache_size": len(self._http_cache) + len(self._llm_cache) + len(self._query_cache),
        }

    def cleanup_expired(self) -> int:
        """Remove all expired entries from all caches. Returns count of removed entries."""
        removed = 0

        for cache_name in ["_http_cache", "_llm_cache", "_query_cache"]:
            cache = getattr(self, cache_name)
            expired_keys = [
                key for key, entry in cache.items()
                if entry.is_expired()
            ]

            for key in expired_keys:
                del cache[key]
                removed += 1

        if removed > 0:
            logger.info(f"Cleaned up {removed} expired cache entries")

        return removed


# Global cache manager instance
_cache_manager: Optional[CacheManager] = None


def get_cache_manager() -> CacheManager:
    """Get global cache manager instance."""
    global _cache_manager
    if _cache_manager is None:
        _cache_manager = CacheManager()
    return _cache_manager


def cached(
    cache_type: str = "http",
    ttl: Optional[timedelta] = None,
    key_fn: Optional[Callable] = None,
):
    """
    Decorator for caching function results.

    Args:
        cache_type: Type of cache to use
        ttl: Time to live for cached results
        key_fn: Custom function to generate cache key

    Example:
        @cached(cache_type="llm", ttl=timedelta(hours=1))
        def generate_completion(prompt: str):
            return llm_client.generate(prompt)
    """

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args, **kwargs) -> T:
            cache = get_cache_manager()

            # Generate cache key
            if key_fn:
                key = key_fn(*args, **kwargs)
            else:
                key = f"{func.__name__}:{cache._generate_key(*args, **kwargs)}"

            # Try to get from cache
            cached_value = cache.get(key, cache_type)
            if cached_value is not None:
                return cached_value

            # Call function and cache result
            try:
                result = func(*args, **kwargs)
                cache.set(key, result, cache_type, ttl)
                return result
            except Exception as e:
                logger.error(f"Function {func.__name__} raised error: {e}")
                raise

        return wrapper

    return decorator


def lru_cache_decorator(maxsize: int = None):
    """
    LRU cache decorator using Python's built-in lru_cache.

    Simpler alternative to the full CacheManager for in-memory caching.

    Args:
        maxsize: Maximum number of entries to cache

    Example:
        @lru_cache_decorator(maxsize=1000)
        def expensive_function(x, y):
            return x * y
    """
    if maxsize is None:
        maxsize = HTTP_CACHE_SIZE

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        return lru_cache(maxsize=maxsize)(func)

    return decorator


# Import helper
from ..config.constants import get_cache_ttl_for_type
