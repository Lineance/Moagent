"""
Async processing framework for MoAgent.

Provides async/await support for concurrent processing of crawl, parse,
and storage operations.
"""

import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Callable, Dict, List, Optional, TypeVar
from functools import wraps

from ..config.constants import (
    DEFAULT_ASYNC_TIMEOUT,
    ASYNC_SEMAPHORE_PERMITS,
    DEFAULT_MAX_CONCURRENT,
)

logger = logging.getLogger(__name__)

T = TypeVar('T')


class AsyncProcessor:
    """
    Async processor for concurrent operations.

    Provides:
    - Concurrent execution with semaphore control
    - Timeout handling
    - Error aggregation
    - Progress tracking

    Example:
        processor = AsyncProcessor(max_concurrent=5)

        async def fetch_item(item):
            return await fetch_url(item['url'])

        results = await processor.map(fetch_item, items_list)
    """

    def __init__(
        self,
        max_concurrent: int = DEFAULT_MAX_CONCURRENT,
        timeout: int = DEFAULT_ASYNC_TIMEOUT
    ):
        """
        Initialize async processor.

        Args:
            max_concurrent: Maximum concurrent operations
            timeout: Default timeout for operations (seconds)
        """
        self.max_concurrent = max_concurrent
        self.timeout = timeout
        self.semaphore = asyncio.Semaphore(max_concurrent)
        self.stats = {
            "total": 0,
            "successful": 0,
            "failed": 0,
            "timeout": 0,
        }

    async def _run_with_semaphore(
        self,
        coro,
        timeout: Optional[int] = None
    ) -> Any:
        """
        Run coroutine with semaphore and timeout.

        Args:
            coro: Coroutine to run
            timeout: Timeout in seconds (uses default if None)

        Returns:
            Result of coroutine

        Raises:
            asyncio.TimeoutError: If operation times out
            Exception: If coroutine raises exception
        """
        timeout = timeout or self.timeout

        async with self.semaphore:
            try:
                result = await asyncio.wait_for(coro, timeout=timeout)
                self.stats["successful"] += 1
                return result
            except asyncio.TimeoutError:
                self.stats["timeout"] += 1
                logger.warning(f"Operation timed out after {timeout}s")
                raise
            except Exception as e:
                self.stats["failed"] += 1
                logger.error(f"Operation failed: {e}")
                raise

    async def map(
        self,
        func: Callable[[T], Any],
        items: List[T],
        timeout: Optional[int] = None
    ) -> List[Any]:
        """
        Apply async function to list of items concurrently.

        Args:
            func: Async function to apply
            items: List of items to process
            timeout: Timeout per operation

        Returns:
            List of results in same order as items

        Example:
            >>> async def process(item):
            ...     return await fetch(item['url'])
            >>> results = await processor.map(process, items)
        """
        if not items:
            return []

        self.stats["total"] += len(items)

        # Create tasks for all items
        tasks = [
            self._run_with_semaphore(func(item), timeout)
            for item in items
        ]

        # Wait for all tasks to complete
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Separate successful results from exceptions
        successful_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Item {i} failed: {result}")
                successful_results.append(None)
            else:
                successful_results.append(result)

        return successful_results

    async def map_parallel(
        self,
        func: Callable[[T], Any],
        items: List[T],
        batch_size: Optional[int] = None,
        timeout: Optional[int] = None
    ) -> List[Any]:
        """
        Apply function in batches with progress tracking.

        Args:
            func: Async function to apply
            items: List of items to process
            batch_size: Process in batches (default: max_concurrent)
            timeout: Timeout per operation

        Returns:
            List of results

        Example:
            >>> # Process in batches of 10
            >>> results = await processor.map_parallel(
            ...     process, items, batch_size=10
            ... )
        """
        batch_size = batch_size or self.max_concurrent
        all_results = []

        for i in range(0, len(items), batch_size):
            batch = items[i:i + batch_size]
            logger.info(f"Processing batch {i // batch_size + 1}/{(len(items) + batch_size - 1) // batch_size}")

            batch_results = await self.map(func, batch, timeout)
            all_results.extend(batch_results)

        return all_results

    def get_stats(self) -> Dict[str, int]:
        """Get processing statistics."""
        return self.stats.copy()

    def reset_stats(self) -> None:
        """Reset statistics."""
        self.stats = {
            "total": 0,
            "successful": 0,
            "failed": 0,
            "timeout": 0,
        }


def to_async(func: Callable) -> Callable:
    """
    Convert synchronous function to async function.

    Runs the sync function in a thread pool executor.

    Args:
        func: Synchronous function

    Returns:
        Async wrapper function

    Example:
        @to_async
        def sync_fetch(url):
            return requests.get(url).json()

        async def main():
            result = await sync_fetch("https://api.example.com")
    """
    @wraps(func)
    async def wrapper(*args, **kwargs):
        loop = asyncio.get_event_loop()
        with ThreadPoolExecutor() as executor:
            return await loop.run_in_executor(
                executor,
                lambda: func(*args, **kwargs)
            )
    return wrapper


def run_async(coro: Callable) -> Any:
    """
    Run async coroutine from synchronous context.

    Args:
        coro: Async coroutine to run

    Returns:
        Result of coroutine

    Example:
        async def async_main():
            return await processor.map(process, items)

        # Run from sync code
        results = run_async(async_main())
    """
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    return loop.run_until_complete(coro)


async def gather_with_errors(
    *coros,
    return_exceptions: bool = True
) -> List[Any]:
    """
    Gather coroutines with detailed error handling.

    Args:
        *coros: Coroutines to gather
        return_exceptions: Return exceptions instead of raising

    Returns:
        List of results

    Example:
        >>> results = await gather_with_errors(
        ...     fetch_item(item1),
        ...     fetch_item(item2),
        ...     fetch_item(item3),
        ... )
    """
    results = await asyncio.gather(*coros, return_exceptions=return_exceptions)

    # Log errors
    for i, result in enumerate(results):
        if isinstance(result, Exception):
            logger.error(f"Coroutine {i} failed: {result}")

    return results


class AsyncBatchProcessor:
    """
    Batch processor for async operations.

    Processes items in batches with automatic backpressure control.
    """

    def __init__(
        self,
        batch_size: int = 10,
        max_concurrent: int = 5
    ):
        """
        Initialize batch processor.

        Args:
            batch_size: Number of items per batch
            max_concurrent: Maximum concurrent batches
        """
        self.batch_size = batch_size
        self.max_concurrent = max_concurrent
        self.processor = AsyncProcessor(max_concurrent=max_concurrent)

    async def process(
        self,
        func: Callable[[List[T]], List[Any]],
        items: List[T]
    ) -> List[Any]:
        """
        Process items in batches.

        Args:
            func: Function that processes a batch of items
            items: Items to process

        Returns:
            Flattened list of results

        Example:
            >>> async def fetch_batch(urls):
            ...     # Fetch multiple URLs in parallel
            ...     return await asyncio.gather(*[
            ...         fetch_url(url) for url in urls
            ...     ])
            >>>
            >>> results = await processor.process(fetch_batch, url_list)
        """
        if not items:
            return []

        # Split into batches
        batches = [
            items[i:i + self.batch_size]
            for i in range(0, len(items), self.batch_size)
        ]

        logger.info(f"Processing {len(items)} items in {len(batches)} batches")

        # Process batches
        batch_results = await self.processor.map(
            lambda batch: func(batch),
            batches
        )

        # Flatten results
        all_results = []
        for batch_result in batch_results:
            if batch_result:
                all_results.extend(batch_result if isinstance(batch_result, list) else [batch_result])

        return all_results
