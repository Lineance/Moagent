"""
Tests for rate limiting.
"""

import pytest
import asyncio
import time
from moagent.rate_limiter import (
    RateLimiter,
    SlidingWindowRateLimiter,
    FixedWindowRateLimiter,
    RateLimiterRegistry,
    get_rate_limiter_registry,
)


class TestRateLimiter:
    """Test RateLimiter (token bucket) class."""

    @pytest.fixture
    def limiter(self):
        """Create rate limiter for testing."""
        return RateLimiter(rate=10, burst=20)

    @pytest.mark.asyncio
    async def test_acquire_success(self, limiter):
        """Test successful token acquisition."""
        assert await limiter.acquire(1) is True
        assert await limiter.acquire(5) is True

    @pytest.mark.asyncio
    async def test_acquire_exceeds_burst(self, limiter):
        """Test acquiring more tokens than burst size."""
        assert await limiter.acquire(20) is True
        assert await limiter.acquire(1) is False  # No tokens left

    @pytest.mark.asyncio
    async def test_token_refill(self, limiter):
        """Test tokens refill over time."""
        # Use all tokens
        limiter.tokens = 0
        assert await limiter.acquire(1) is False

        # Wait for refill
        await asyncio.sleep(0.2)  # Should refill 2 tokens (10 * 0.2)

        assert await limiter.acquire(1) is True

    @pytest.mark.asyncio
    async def test_acquire_with_wait(self, limiter):
        """Test acquire_with_wait blocks until tokens available."""
        limiter.tokens = 0

        start = time.time()
        await limiter.acquire_with_wait(1)
        elapsed = time.time() - start

        # Should have waited for tokens to refill
        assert elapsed >= 0.1  # At least some wait time

    def test_get_available_tokens(self, limiter):
        """Test getting available token count."""
        tokens = limiter.get_available_tokens()
        assert 0 <= tokens <= limiter.burst

    def test_reset(self, limiter):
        """Test resetting limiter."""
        # Use some tokens
        limiter.tokens = 10

        limiter.reset()
        assert limiter.tokens == limiter.burst


class TestSlidingWindowRateLimiter:
    """Test SlidingWindowRateLimiter class."""

    @pytest.fixture
    def limiter(self):
        """Create sliding window limiter."""
        return SlidingWindowRateLimiter(rate=5, window=1)

    @pytest.mark.asyncio
    async def test_acquire_within_limit(self, limiter):
        """Test acquiring within rate limit."""
        for _ in range(5):
            assert await limiter.acquire() is True

    @pytest.mark.asyncio
    async def test_acquire_exceeds_limit(self, limiter):
        """Test acquiring exceeds rate limit."""
        for _ in range(5):
            await limiter.acquire()

        # 6th request should be denied
        assert await limiter.acquire() is False

    @pytest.mark.asyncio
    async def test_window_slides(self, limiter):
        """Test window slides over time."""
        # Fill window
        for _ in range(5):
            await limiter.acquire()

        assert await limiter.acquire() is False

        # Wait for window to slide
        await asyncio.sleep(1.1)

        # Should allow new requests
        assert await limiter.acquire() is True


class TestFixedWindowRateLimiter:
    """Test FixedWindowRateLimiter class."""

    @pytest.fixture
    def limiter(self):
        """Create fixed window limiter."""
        return FixedWindowRateLimiter(rate=5, window=1)

    @pytest.mark.asyncio
    async def test_acquire_within_limit(self, limiter):
        """Test acquiring within limit."""
        for _ in range(5):
            assert await limiter.acquire() is True

    @pytest.mark.asyncio
    async def test_acquire_exceeds_limit(self, limiter):
        """Test acquiring exceeds limit."""
        for _ in range(5):
            await limiter.acquire()

        # 6th request denied
        assert await limiter.acquire() is False

    @pytest.mark.asyncio
    async def test_window_resets(self, limiter):
        """Test window resets after timeout."""
        # Fill window
        for _ in range(5):
            await limiter.acquire()

        assert await limiter.acquire() is False

        # Wait for window reset
        await asyncio.sleep(1.1)

        # New window should allow requests
        assert await limiter.acquire() is True
        assert await limiter.acquire() is True


class TestRateLimiterRegistry:
    """Test RateLimiterRegistry class."""

    @pytest.fixture
    def registry(self):
        """Create registry for testing."""
        return RateLimiterRegistry()

    def test_register_limiter(self, registry):
        """Test registering new limiter."""
        registry.register("test", rate=10, burst=20)
        assert "test" in registry.limiters

    def test_register_overwrites(self, registry):
        """Test registering overwrites existing."""
        registry.register("test", rate=5, burst=10)
        registry.register("test", rate=20, burst=30)

        stats = registry.get_stats("test")
        assert stats["rate"] == 20

    @pytest.mark.asyncio
    async def test_acquire_from_registry(self, registry):
        """Test acquiring from registered limiter."""
        registry.register("api", rate=10, burst=20)

        assert await registry.acquire("api") is True

    @pytest.mark.asyncio
    async def test_acquire_auto_creates(self, registry):
        """Test acquire creates default limiter if missing."""
        assert "missing" not in registry.limiters
        assert await registry.acquire("missing") is True
        assert "missing" in registry.limiters

    def test_get_stats(self, registry):
        """Test getting limiter stats."""
        registry.register("test", rate=10, burst=20)
        stats = registry.get_stats("test")

        assert stats["rate"] == 10
        assert stats["burst"] == 20

    def test_reset_specific_limiter(self, registry):
        """Test resetting specific limiter."""
        registry.register("test", rate=10, burst=20)
        limiter = registry.limiters["test"]
        limiter.tokens = 5

        registry.reset("test")
        assert limiter.tokens == limiter.burst

    def test_reset_all_limiters(self, registry):
        """Test resetting all limiters."""
        registry.register("test1", rate=10, burst=20)
        registry.register("test2", rate=5, burst=10)

        registry.limiters["test1"].tokens = 5
        registry.limiters["test2"].tokens = 3

        registry.reset()

        assert registry.limiters["test1"].tokens == 20
        assert registry.limiters["test2"].tokens == 10


class TestGlobalRegistry:
    """Test global rate limiter registry."""

    def test_get_global_registry(self):
        """Test getting global registry returns singleton."""
        registry1 = get_rate_limiter_registry()
        registry2 = get_rate_limiter_registry()
        assert registry1 is registry2

    def test_global_registry_has_defaults(self):
        """Test global registry has default limiters."""
        registry = get_rate_limiter_registry()

        # Should have OpenAI and Anthropic registered
        assert "openai" in registry.limiters
        assert "anthropic" in registry.limiters
