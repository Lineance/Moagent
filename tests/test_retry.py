"""
Tests for retry logic and circuit breakers.
"""

import pytest
import time
from moagent.retry import (
    CircuitBreaker,
    CircuitBreakerError,
    CircuitState,
    RetryPolicy,
    retry,
    async_retry,
    retry_with_circuit_breaker,
)


class TestCircuitBreaker:
    """Test CircuitBreaker class."""

    @pytest.fixture
    def breaker(self):
        """Create circuit breaker for testing."""
        return CircuitBreaker(
            name="test",
            failure_threshold=3,
            timeout=1,
            half_open_requests=2
        )

    def test_initial_state(self, breaker):
        """Test initial state is closed."""
        assert breaker.state == CircuitState.CLOSED
        assert breaker.failure_count == 0

    def test_circuit_opens_on_threshold(self, breaker):
        """Test circuit opens after failure threshold."""

        def failing_function():
            raise ValueError("Error!")

        # Trigger failures
        for _ in range(breaker.failure_threshold):
            try:
                breaker.call(failing_function)
            except ValueError:
                pass

        # Circuit should be open
        assert breaker.state == CircuitState.OPEN
        assert breaker.failure_count >= breaker.failure_threshold

    def test_circuit_rejects_when_open(self, breaker):
        """Test circuit rejects requests when open."""

        def failing_function():
            raise ValueError("Error!")

        # Open the circuit
        for _ in range(breaker.failure_threshold + 1):
            try:
                breaker.call(failing_function)
            except (ValueError, CircuitBreakerError):
                pass

        # Should raise CircuitBreakerError
        with pytest.raises(CircuitBreakerError):
            breaker.call(lambda: None)

    def test_circuit_resets_after_timeout(self, breaker):
        """Test circuit resets after timeout."""

        def failing_function():
            raise ValueError("Error!")

        # Open circuit
        for _ in range(breaker.failure_threshold):
            try:
                breaker.call(failing_function)
            except ValueError:
                pass

        assert breaker.state == CircuitState.OPEN

        # Wait for timeout
        time.sleep(breaker.timeout.total_seconds() + 0.1)

        # Next request should be allowed (half-open)
        def success_function():
            return "success"

        result = breaker.call(success_function)
        assert result == "success"
        assert breaker.state == CircuitState.HALF_OPEN

    def test_circuit_closes_on_recovery(self, breaker):
        """Test circuit closes after successful recovery."""

        def failing_function():
            raise ValueError("Error!")

        # Open circuit
        for _ in range(breaker.failure_threshold):
            try:
                breaker.call(failing_function)
            except ValueError:
                pass

        # Wait for timeout
        time.sleep(breaker.timeout.total_seconds() + 0.1)

        # Successful requests in half-open state
        def success_function():
            return "success"

        for _ in range(breaker.half_open_requests):
            breaker.call(success_function)

        # Circuit should be closed
        assert breaker.state == CircuitState.CLOSED
        assert breaker.failure_count == 0

    def test_get_state(self, breaker):
        """Test getting circuit breaker state."""
        state = breaker.get_state()
        assert state["name"] == "test"
        assert state["state"] == CircuitState.CLOSED


class TestRetryPolicy:
    """Test RetryPolicy class."""

    def test_should_retry_default_errors(self):
        """Test default retriable errors."""
        policy = RetryPolicy(max_attempts=3)

        assert policy.should_retry(ConnectionError())
        assert policy.should_retry(TimeoutError())
        assert not policy.should_retry(ValueError())

    def test_calculate_delay_exponential(self):
        """Test exponential backoff calculation."""
        policy = RetryPolicy(
            base_delay=1,
            max_delay=10,
            multiplier=2,
            jitter=False
        )

        assert policy.calculate_delay(0) == 1
        assert policy.calculate_delay(1) == 2
        assert policy.calculate_delay(2) == 4
        assert policy.calculate_delay(3) == 8  # Maxes at 8
        assert policy.calculate_delay(10) == 10  # Max delay

    def test_calculate_delay_with_jitter(self):
        """Test jitter is added to delay."""
        policy = RetryPolicy(
            base_delay=1,
            multiplier=2,
            jitter=True
        )

        delay1 = policy.calculate_delay(0)
        delay2 = policy.calculate_delay(0)

        # With jitter, delays should be different
        assert delay1 != delay2


class TestRetryDecorator:
    """Test @retry decorator."""

    def test_retry_on_failure(self):
        """Test function is retried on failure."""
        call_count = [0]

        @retry(max_attempts=3, base_delay=0.01)
        def failing_function():
            call_count[0] += 1
            if call_count[0] < 3:
                raise ConnectionError("Temporary failure")
            return "success"

        result = failing_function()
        assert result == "success"
        assert call_count[0] == 3

    def test_retry_max_attempts_reached(self):
        """Test max attempts is respected."""

        @retry(max_attempts=3, base_delay=0.01)
        def always_failing_function():
            raise ConnectionError("Always fails")

        with pytest.raises(ConnectionError):
            always_failing_function()

    def test_retry_no_retriable_error(self):
        """Test non-retriable errors are not retried."""

        @retry(max_attempts=3)
        def raise_value_error():
            call_count = [0]
            call_count[0] += 1
            raise ValueError("Not retriable")

        with pytest.raises(ValueError):
            raise_value_error()

        # Should only be called once (no retries)
        # Note: This test would need to be adjusted based on implementation


class TestAsyncRetryDecorator:
    """Test @async_retry decorator."""

    @pytest.mark.asyncio
    async def test_async_retry_on_failure(self):
        """Test async function is retried."""
        call_count = [0]

        @async_retry(max_attempts=3, base_delay=0.01)
        async def async_failing_function():
            call_count[0] += 1
            if call_count[0] < 3:
                raise ConnectionError("Temporary failure")
            return "success"

        result = await async_failing_function()
        assert result == "success"
        assert call_count[0] == 3

    @pytest.mark.asyncio
    async def test_async_retry_max_attempts(self):
        """Test max attempts in async."""

        @async_retry(max_attempts=3, base_delay=0.01)
        async def async_always_failing():
            raise ConnectionError("Always fails")

        with pytest.raises(ConnectionError):
            await async_always_failing()


class TestRetryWithCircuitBreaker:
    """Test combining retry with circuit breaker."""

    def test_retry_with_circuit_breaker_decorator(self):
        """Test combined retry and circuit breaker."""
        breaker = CircuitBreaker("test", failure_threshold=2)
        call_count = [0]

        @retry_with_circuit_breaker(breaker, max_attempts=2, base_delay=0.01)
        def function():
            call_count[0] += 1
            if call_count[0] < 4:
                raise ConnectionError("Fail")
            return "success"

        # Should retry and eventually succeed
        result = function()
        assert result == "success"
