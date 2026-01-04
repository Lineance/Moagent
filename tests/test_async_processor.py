"""
Tests for async processing framework.
"""

import pytest
import asyncio
from moagent.async_processor import (
    AsyncProcessor,
    to_async,
    run_async,
    gather_with_errors,
    AsyncBatchProcessor,
)


class TestAsyncProcessor:
    """Test AsyncProcessor class."""

    @pytest.fixture
    def processor(self):
        """Create async processor for testing."""
        return AsyncProcessor(max_concurrent=3, timeout=5)

    @pytest.mark.asyncio
    async def test_map_basic(self, processor):
        """Test basic map operation."""

        async def double(x):
            return x * 2

        results = await processor.map(double, [1, 2, 3, 4, 5])
        assert results == [2, 4, 6, 8, 10]

    @pytest.mark.asyncio
    async def test_map_with_timeout(self, processor):
        """Test map with timeout."""

        async def slow_task(x):
            await asyncio.sleep(0.1)
            return x

        results = await processor.map(slow_task, [1, 2, 3], timeout=1)
        assert results == [1, 2, 3]

    @pytest.mark.asyncio
    async def test_map_with_errors(self, processor):
        """Test map handles errors gracefully."""

        async def failing_task(x):
            if x == 2:
                raise ValueError("Error!")
            return x * 2

        results = await processor.map(failing_task, [1, 2, 3, 4, 5])
        assert results[0] == 2
        assert results[1] is None  # Failed task
        assert results[2] == 6
        assert results[3] is None  # Failed task
        assert results[4] == 10

    @pytest.mark.asyncio
    async def test_map_parallel_batches(self, processor):
        """Test parallel batch processing."""

        async def process_batch(items):
            await asyncio.sleep(0.01)
            return [x * 2 for x in items]

        items = list(range(10))
        results = await processor.map_parallel(process_batch, items, batch_size=3)
        assert results == [x * 2 for x in items]

    def test_get_stats(self, processor):
        """Test statistics tracking."""
        # Initial stats
        stats = processor.get_stats()
        assert stats["total"] == 0
        assert stats["successful"] == 0

    def test_reset_stats(self, processor):
        """Test resetting statistics."""
        # We'll test this with actual operations in integration tests
        processor.reset_stats()
        stats = processor.get_stats()
        assert stats["total"] == 0


class TestToAsync:
    """Test to_async decorator."""

    @pytest.mark.asyncio
    async def test_to_async_decorator(self):
        """Test converting sync function to async."""

        @to_async
        def sync_function(x, y):
            return x + y

        result = await sync_function(2, 3)
        assert result == 5

    @pytest.mark.asyncio
    async def test_to_async_with_io(self):
        """Test to_async with I/O operation."""

        @to_async
        def sync_read_file():
            return "file content"

        result = await sync_read_file()
        assert result == "file content"


class TestRunAsync:
    """Test run_async function."""

    def test_run_async_from_sync(self):
        """Test running async from sync context."""

        async def async_function():
            await asyncio.sleep(0.01)
            return 42

        result = run_async(async_function())
        assert result == 42


class TestGatherWithErrors:
    """Test gather_with_errors function."""

    @pytest.mark.asyncio
    async def test_gather_with_errors_all_success(self):
        """Test gathering all successful coroutines."""

        async def task1():
            return 1

        async def task2():
            return 2

        async def task3():
            return 3

        results = await gather_with_errors(task1(), task2(), task3())
        assert results == [1, 2, 3]

    @pytest.mark.asyncio
    async def test_gather_with_errors_some_fail(self):
        """Test gathering with some failures."""

        async def task1():
            return 1

        async def task2():
            raise ValueError("Error!")

        async def task3():
            return 3

        results = await gather_with_errors(task1(), task2(), task3())
        assert results[0] == 1
        assert isinstance(results[1], ValueError)
        assert results[2] == 3


class TestAsyncBatchProcessor:
    """Test AsyncBatchProcessor class."""

    @pytest.fixture
    def batch_processor(self):
        """Create batch processor for testing."""
        return AsyncBatchProcessor(batch_size=3, max_concurrent=2)

    @pytest.mark.asyncio
    async def test_process_batches(self, batch_processor):
        """Test processing items in batches."""

        async def process_batch(batch):
            return [x * 2 for x in batch]

        items = list(range(10))
        results = await batch_processor.process(process_batch, items)

        assert results == [x * 2 for x in items]

    @pytest.mark.asyncio
    async def test_process_empty_list(self, batch_processor):
        """Test processing empty list."""

        async def process_batch(batch):
            return [x * 2 for x in batch]

        results = await batch_processor.process(process_batch, [])
        assert results == []
