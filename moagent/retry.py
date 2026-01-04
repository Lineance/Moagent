"""
Enhanced retry logic with circuit breakers and jitter.

Provides sophisticated retry mechanisms:
- Exponential backoff with jitter
- Circuit breaker pattern
- Retry policies by error type
- Deadlines and timeout handling
"""

import asyncio
import logging
import random
import time
from typing import Any, Callable, Dict, List, Optional, Type, Tuple
from functools import wraps
from datetime import datetime, timedelta

from ..config.constants import (
    RETRY_BASE_DELAY,
    RETRY_MAX_DELAY,
    RETRY_MULTIPLIER,
    RETRY_JITTER,
    CIRCUIT_BREAKER_THRESHOLD,
    CIRCUIT_BREAKER_TIMEOUT,
    CIRCUIT_BREAKER_HALF_OPEN_REQUESTS,
)

logger = logging.getLogger(__name__)


class CircuitBreakerError(Exception):
    """Raised when circuit breaker is open."""
    pass


class CircuitState:
    """Circuit breaker states."""
    CLOSED = "closed"  # Normal operation
    OPEN = "open"  # Failing, reject requests
    HALF_OPEN = "half_open"  # Testing if recovered


class CircuitBreaker:
    """
    Circuit breaker for preventing cascading failures.

    Tracks failures and opens circuit when threshold is reached.
    Allows single requests through in half-open state to test recovery.

    Example:
        breaker = CircuitBreaker(
            name="api",
            failure_threshold=5,
            timeout=60
        )

        @breaker
        def call_api():
            return requests.get("https://api.example.com")

        try:
            result = call_api()
        except CircuitBreakerError:
            logger.error("Circuit is open, using fallback")
    """

    def __init__(
        self,
        name: str,
        failure_threshold: int = CIRCUIT_BREAKER_THRESHOLD,
        timeout: int = CIRCUIT_BREAKER_TIMEOUT,
        half_open_requests: int = CIRCUIT_BREAKER_HALF_OPEN_REQUESTS
    ):
        """
        Initialize circuit breaker.

        Args:
            name: Name of the circuit breaker
            failure_threshold: Failures before opening circuit
            timeout: Seconds before attempting recovery
            half_open_requests: Requests allowed in half-open state
        """
        self.name = name
        self.failure_threshold = failure_threshold
        self.timeout = timedelta(seconds=timeout)
        self.half_open_requests = half_open_requests

        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time: Optional[datetime] = None
        self.half_open_count = 0

    def __call__(self, func: Callable) -> Callable:
        """Decorator to apply circuit breaker to function."""
        @wraps(func)
        def wrapper(*args, **kwargs):
            return self.call(func, *args, **kwargs)
        return wrapper

    def call(self, func: Callable, *args, **kwargs) -> Any:
        """
        Execute function with circuit breaker protection.

        Args:
            func: Function to execute
            *args: Function arguments
            **kwargs: Function keyword arguments

        Returns:
            Function result

        Raises:
            CircuitBreakerError: If circuit is open
        """
        if not self.allow_request():
            logger.warning(f"Circuit breaker '{self.name}' is OPEN, rejecting request")
            raise CircuitBreakerError(f"Circuit breaker '{self.name}' is open")

        try:
            result = func(*args, **kwargs)
            self.on_success()
            return result
        except Exception as e:
            self.on_failure()
            raise

    def allow_request(self) -> bool:
        """
        Check if request should be allowed.

        Returns:
            True if request allowed, False if circuit open
        """
        if self.state == CircuitState.CLOSED:
            return True

        if self.state == CircuitState.OPEN:
            # Check if timeout has passed
            if self.last_failure_time and datetime.now() - self.last_failure_time > self.timeout:
                logger.info(f"Circuit breaker '{self.name}' timeout elapsed, entering HALF_OPEN state")
                self.state = CircuitState.HALF_OPEN
                self.half_open_count = 0
                return True
            return False

        if self.state == CircuitState.HALF_OPEN:
            # Allow limited requests in half-open state
            return self.half_open_count < self.half_open_requests

        return False

    def on_success(self) -> None:
        """Handle successful request."""
        if self.state == CircuitState.HALF_OPEN:
            self.half_open_count += 1
            if self.half_open_count >= self.half_open_requests:
                logger.info(f"Circuit breaker '{self.name}' recovered, closing circuit")
                self.reset()
        else:
            self.failure_count = 0

    def on_failure(self) -> None:
        """Handle failed request."""
        self.failure_count += 1
        self.last_failure_time = datetime.now()

        if self.failure_count >= self.failure_threshold:
            logger.error(
                f"Circuit breaker '{self.name}' failure threshold reached, "
                f"opening circuit (failures: {self.failure_count})"
            )
            self.state = CircuitState.OPEN

    def reset(self) -> None:
        """Reset circuit breaker to closed state."""
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time = None
        self.half_open_count = 0

    def get_state(self) -> Dict[str, Any]:
        """Get circuit breaker state."""
        return {
            "name": self.name,
            "state": self.state,
            "failure_count": self.failure_count,
            "last_failure_time": self.last_failure_time.isoformat() if self.last_failure_time else None,
        }


class RetryPolicy:
    """
    Retry policy configuration.

    Defines how retries should be performed based on error type.
    """

    def __init__(
        self,
        max_attempts: int = 3,
        base_delay: float = RETRY_BASE_DELAY,
        max_delay: float = RETRY_MAX_DELAY,
        multiplier: float = RETRY_MULTIPLIER,
        jitter: bool = RETRY_JITTER,
        retriable_errors: Optional[List[Type[Exception]]] = None,
    ):
        """
        Initialize retry policy.

        Args:
            max_attempts: Maximum number of retry attempts
            base_delay: Initial delay between retries (seconds)
            max_delay: Maximum delay between retries (seconds)
            multiplier: Exponential backoff multiplier
            jitter: Add random jitter to delays
            retriable_errors: List of error types to retry
        """
        self.max_attempts = max_attempts
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.multiplier = multiplier
        self.jitter = jitter
        self.retriable_errors = retriable_errors or [
            ConnectionError,
            TimeoutError,
            OSError,
        ]

    def should_retry(self, error: Exception) -> bool:
        """Check if error should be retried."""
        return any(isinstance(error, error_type) for error_type in self.retriable_errors)

    def calculate_delay(self, attempt: int) -> float:
        """
        Calculate delay before next retry.

        Args:
            attempt: Attempt number (0-indexed)

        Returns:
            Delay in seconds
        """
        delay = min(self.base_delay * (self.multiplier ** attempt), self.max_delay)

        if self.jitter:
            # Add ±25% jitter
            jitter_range = delay * 0.25
            delay += random.uniform(-jitter_range, jitter_range)

        return max(0, delay)


def retry(
    max_attempts: int = 3,
    base_delay: float = RETRY_BASE_DELAY,
    max_delay: float = RETRY_MAX_DELAY,
    multiplier: float = RETRY_MULTIPLIER,
    jitter: bool = RETRY_JITTER,
    retriable_errors: Optional[List[Type[Exception]]] = None,
):
    """
    Decorator for retrying functions with exponential backoff.

    Args:
        max_attempts: Maximum number of attempts
        base_delay: Initial delay between retries
        max_delay: Maximum delay between retries
        multiplier: Exponential backoff multiplier
        jitter: Add random jitter to delays
        retriable_errors: List of error types to retry

    Example:
        @retry(max_attempts=5, base_delay=1, jitter=True)
        def fetch_api():
            return requests.get("https://api.example.com")

        # Will retry up to 5 times with exponential backoff and jitter
        result = fetch_api()
    """
    policy = RetryPolicy(
        max_attempts=max_attempts,
        base_delay=base_delay,
        max_delay=max_delay,
        multiplier=multiplier,
        jitter=jitter,
        retriable_errors=retriable_errors,
    )

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_error = None

            for attempt in range(policy.max_attempts):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_error = e

                    # Check if should retry
                    if attempt == policy.max_attempts - 1:
                        logger.error(f"Max retries ({policy.max_attempts}) reached for {func.__name__}")
                        raise

                    if not policy.should_retry(e):
                        logger.warning(f"Non-retriable error in {func.__name__}: {e}")
                        raise

                    # Calculate delay
                    delay = policy.calculate_delay(attempt)
                    logger.warning(
                        f"Attempt {attempt + 1}/{policy.max_attempts} failed for {func.__name__}: {e}. "
                        f"Retrying in {delay:.2f}s..."
                    )

                    time.sleep(delay)

            # Should not reach here, but just in case
            raise last_error

        return wrapper

    return decorator


def async_retry(
    max_attempts: int = 3,
    base_delay: float = RETRY_BASE_DELAY,
    max_delay: float = RETRY_MAX_DELAY,
    multiplier: float = RETRY_MULTIPLIER,
    jitter: bool = RETRY_JITTER,
    retriable_errors: Optional[List[Type[Exception]]] = None,
):
    """
    Async decorator for retrying async functions.

    Same as @retry but for async functions.

    Example:
        @async_retry(max_attempts=3)
        async def fetch_async():
            return await aiohttp.get("https://api.example.com")
    """
    policy = RetryPolicy(
        max_attempts=max_attempts,
        base_delay=base_delay,
        max_delay=max_delay,
        multiplier=multiplier,
        jitter=jitter,
        retriable_errors=retriable_errors,
    )

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            last_error = None

            for attempt in range(policy.max_attempts):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    last_error = e

                    if attempt == policy.max_attempts - 1:
                        logger.error(f"Max retries ({policy.max_attempts}) reached for {func.__name__}")
                        raise

                    if not policy.should_retry(e):
                        logger.warning(f"Non-retriable error in {func.__name__}: {e}")
                        raise

                    delay = policy.calculate_delay(attempt)
                    logger.warning(
                        f"Attempt {attempt + 1}/{policy.max_attempts} failed for {func.__name__}: {e}. "
                        f"Retrying in {delay:.2f}s..."
                    )

                    await asyncio.sleep(delay)

            raise last_error

        return wrapper

    return decorator


def retry_with_circuit_breaker(
    circuit_breaker: CircuitBreaker,
    max_attempts: int = 3,
    base_delay: float = RETRY_BASE_DELAY,
):
    """
    Combine circuit breaker with retry logic.

    Args:
        circuit_breaker: Circuit breaker instance
        max_attempts: Retry attempts
        base_delay: Delay between retries

    Example:
        api_breaker = CircuitBreaker("api", failure_threshold=5)

        @retry_with_circuit_breaker(api_breaker, max_attempts=3)
        def call_api():
            return requests.get("https://api.example.com")
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Circuit breaker check
            def attempt_call():
                return circuit_breaker.call(func, *args, **kwargs)

            # Retry logic
            last_error = None
            for attempt in range(max_attempts):
                try:
                    return attempt_call()
                except CircuitBreakerError:
                    raise  # Don't retry if circuit is open
                except Exception as e:
                    last_error = e
                    if attempt < max_attempts - 1:
                        delay = base_delay * (2 ** attempt)
                        time.sleep(delay)

            raise last_error

        return wrapper

    return decorator
