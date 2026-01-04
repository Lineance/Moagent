"""
Rate limiting protection for MoAgent.

Provides multiple rate limiting strategies:
- Token bucket algorithm
- Sliding window log
- Fixed window counter
- Leaky bucket
"""

import asyncio
import logging
import time
from collections import deque
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

from ..config.constants import (
    DEFAULT_RATE_LIMIT,
    DEFAULT_RATE_LIMIT_BURST,
    OPENAI_RATE_LIMIT,
    ANTHROPIC_RATE_LIMIT,
    get_rate_limit_for_provider,
)

logger = logging.getLogger(__name__)


class RateLimiter:
    """
    Token bucket rate limiter.

    Allows bursts up to burst_size, then limits to rate per second.

    Example:
        limiter = RateLimiter(rate=10, burst=20)

        if limiter.acquire():
            make_request()
        else:
            wait_for_slot()
    """

    def __init__(
        self,
        rate: float = DEFAULT_RATE_LIMIT,
        burst: int = DEFAULT_RATE_LIMIT_BURST,
    ):
        """
        Initialize rate limiter.

        Args:
            rate: Requests per second
            burst: Maximum burst size (tokens in bucket)
        """
        self.rate = rate
        self.burst = burst
        self.tokens = burst
        self.last_update = time.time()
        self.lock = asyncio.Lock()

    async def acquire(self, tokens: int = 1) -> bool:
        """
        Acquire tokens from bucket.

        Args:
            tokens: Number of tokens to acquire

        Returns:
            True if tokens acquired, False if not enough tokens

        Example:
            >>> if await limiter.acquire():
            ...     make_request()
        """
        async with self.lock:
            now = time.time()
            elapsed = now - self.last_update

            # Refill tokens based on elapsed time
            self.tokens = min(
                self.burst,
                self.tokens + elapsed * self.rate
            )
            self.last_update = now

            if self.tokens >= tokens:
                self.tokens -= tokens
                return True

            return False

    async def acquire_with_wait(self, tokens: int = 1) -> None:
        """
        Acquire tokens, waiting if necessary.

        Args:
            tokens: Number of tokens to acquire

        Example:
            >>> await limiter.acquire_with_wait()
            >>> make_request()  # Guaranteed to be within rate limit
        """
        while not await self.acquire(tokens):
            # Calculate wait time
            wait_time = (tokens - self.tokens) / self.rate
            logger.debug(f"Rate limit reached, waiting {wait_time:.2f}s")
            await asyncio.sleep(wait_time)

    def get_available_tokens(self) -> float:
        """Get current number of available tokens."""
        now = time.time()
        elapsed = now - self.last_update
        available = min(self.burst, self.tokens + elapsed * self.rate)
        return available

    def reset(self) -> None:
        """Reset token bucket to full capacity."""
        self.tokens = self.burst
        self.last_update = time.time()


class SlidingWindowRateLimiter:
    """
    Sliding window rate limiter.

    Tracks request timestamps in a sliding window.
    More accurate than fixed window but uses more memory.

    Example:
        limiter = SlidingWindowRateLimiter(rate=60, window=60)

        if await limiter.acquire():
            make_request()
    """

    def __init__(self, rate: int, window: int = 60):
        """
        Initialize sliding window rate limiter.

        Args:
            rate: Maximum requests allowed
            window: Time window in seconds
        """
        self.rate = rate
        self.window = timedelta(seconds=window)
        self.requests: deque = deque()
        self.lock = asyncio.Lock()

    async def acquire(self) -> bool:
        """
        Check if request is within rate limit.

        Returns:
            True if within limit, False otherwise
        """
        async with self.lock:
            now = datetime.now()

            # Remove old requests outside window
            while self.requests and now - self.requests[0] > self.window:
                self.requests.popleft()

            # Check if under limit
            if len(self.requests) < self.rate:
                self.requests.append(now)
                return True

            return False

    async def acquire_with_wait(self) -> None:
        """Acquire permission, waiting if necessary."""
        while not await self.acquire():
            # Wait until oldest request expires
            if self.requests:
                oldest = self.requests[0]
                wait_time = (oldest + self.window - datetime.now()).total_seconds()
                if wait_time > 0:
                    await asyncio.sleep(wait_time)


class FixedWindowRateLimiter:
    """
    Fixed window rate limiter.

    Resets counter at fixed intervals. Simple but can allow
    bursts at window boundaries.

    Example:
        limiter = FixedWindowRateLimiter(rate=100, window=60)

        if await limiter.acquire():
            make_request()
    """

    def __init__(self, rate: int, window: int = 60):
        """
        Initialize fixed window rate limiter.

        Args:
            rate: Maximum requests per window
            window: Window size in seconds
        """
        self.rate = rate
        self.window = window
        self.count = 0
        self.window_start = time.time()
        self.lock = asyncio.Lock()

    async def acquire(self) -> bool:
        """Check if request is within rate limit."""
        async with self.lock:
            now = time.time()

            # Reset window if expired
            if now - self.window_start >= self.window:
                self.count = 0
                self.window_start = now

            # Check if under limit
            if self.count < self.rate:
                self.count += 1
                return True

            return False

    async def acquire_with_wait(self) -> None:
        """Acquire permission, waiting if necessary."""
        while not await self.acquire():
            # Wait for next window
            wait_time = self.window - (time.time() - self.window_start)
            await asyncio.sleep(max(0, wait_time))


class RateLimiterRegistry:
    """
    Registry for managing multiple rate limiters.

    Useful for managing different rate limits for different
    services or API endpoints.

    Example:
        registry = RateLimiterRegistry()

        # Register limiters
        registry.register("openai", rate=3000, burst=10)
        registry.register("anthropic", rate=50, burst=5)

        # Use limiters
        if await registry.acquire("openai"):
            call_openai_api()
    """

    def __init__(self):
        """Initialize rate limiter registry."""
        self.limiters: Dict[str, RateLimiter] = {}

    def register(
        self,
        name: str,
        rate: Optional[float] = None,
        burst: Optional[int] = None,
        limiter_type: str = "token_bucket"
    ) -> None:
        """
        Register a new rate limiter.

        Args:
            name: Unique name for the limiter
            rate: Requests per second (or per minute for some types)
            burst: Burst size
            limiter_type: Type of limiter ('token_bucket', 'sliding_window', 'fixed_window')
        """
        if name in self.limiters:
            logger.warning(f"Rate limiter '{name}' already registered, overwriting")

        if limiter_type == "token_bucket":
            self.limiters[name] = RateLimiter(rate or DEFAULT_RATE_LIMIT, burst or DEFAULT_RATE_LIMIT_BURST)
        elif limiter_type == "sliding_window":
            self.limiters[name] = SlidingWindowRateLimiter(int(rate or DEFAULT_RATE_LIMIT))
        elif limiter_type == "fixed_window":
            self.limiters[name] = FixedWindowRateLimiter(int(rate or DEFAULT_RATE_LIMIT))
        else:
            raise ValueError(f"Unknown limiter type: {limiter_type}")

        logger.info(f"Registered rate limiter '{name}' ({limiter_type}, rate={rate})")

    async def acquire(self, name: str, tokens: int = 1) -> bool:
        """
        Acquire from named rate limiter.

        Args:
            name: Name of registered limiter
            tokens: Tokens to acquire

        Returns:
            True if acquired, False if would exceed limit
        """
        if name not in self.limiters:
            logger.warning(f"Rate limiter '{name}' not found, creating default")
            self.register(name)

        limiter = self.limiters[name]
        return await limiter.acquire(tokens)

    async def acquire_with_wait(self, name: str, tokens: int = 1) -> None:
        """
        Acquire from named rate limiter, waiting if necessary.

        Args:
            name: Name of registered limiter
            tokens: Tokens to acquire
        """
        if name not in self.limiters:
            self.register(name)

        limiter = self.limiters[name]
        await limiter.acquire_with_wait(tokens)

    def get_stats(self, name: str) -> Dict[str, Any]:
        """Get statistics for named limiter."""
        if name not in self.limiters:
            return {}

        limiter = self.limiters[name]
        if isinstance(limiter, RateLimiter):
            return {
                "type": "token_bucket",
                "rate": limiter.rate,
                "burst": limiter.burst,
                "available_tokens": limiter.get_available_tokens(),
            }
        else:
            return {
                "type": limiter.__class__.__name__,
            }

    def reset(self, name: Optional[str] = None) -> None:
        """
        Reset rate limiter(s).

        Args:
            name: Name of limiter to reset, or None to reset all
        """
        if name:
            if name in self.limiters and isinstance(self.limiters[name], RateLimiter):
                self.limiters[name].reset()
        else:
            for limiter in self.limiters.values():
                if isinstance(limiter, RateLimiter):
                    limiter.reset()


# Global rate limiter registry
_global_registry: Optional[RateLimiterRegistry] = None


def get_rate_limiter_registry() -> RateLimiterRegistry:
    """Get global rate limiter registry."""
    global _global_registry
    if _global_registry is None:
        _global_registry = RateLimiterRegistry()

        # Register default limiters for LLM providers
        _global_registry.register("openai", rate=OPENAI_RATE_LIMIT / 60, burst=10)
        _global_registry.register("anthropic", rate=ANTHROPIC_RATE_LIMIT / 60, burst=5)

    return _global_registry


def rate_limiter(name: str):
    """
    Decorator to apply rate limiting to function.

    Args:
        name: Name of rate limiter to use

    Example:
        @rate_limiter("openai")
        def call_openai_api(prompt):
            return openai.Completion.create(prompt=prompt)
    """
    registry = get_rate_limiter_registry()

    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            await registry.acquire_with_wait(name)
            return await func(*args, **kwargs)

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            # For sync functions, we need to run async code
            async def _acquire_and_call():
                await registry.acquire_with_wait(name)
                return func(*args, **kwargs)

            return asyncio.run(_acquire_and_call())

        import inspect
        if inspect.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator
