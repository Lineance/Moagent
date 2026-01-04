"""
Utility helper functions.
"""

import hashlib
import json
import re
import asyncio
import logging
from typing import Any, Callable, Optional, TypeVar
from datetime import datetime
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

T = TypeVar('T')


def calculate_hash(data: dict[str, Any]) -> str:
    """
    Calculate MD5 hash for dictionary data.

    Args:
        data: Dictionary to hash

    Returns:
        MD5 hash string
    """
    normalized = json.dumps(data, sort_keys=True, ensure_ascii=False)
    return hashlib.md5(normalized.encode('utf-8')).hexdigest()


def format_timestamp(timestamp: str) -> str:
    """
    Format timestamp to readable format.

    Args:
        timestamp: Timestamp string

    Returns:
        Formatted timestamp
    """
    try:
        dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
        return dt.strftime('%Y-%m-%d %H:%M:%S')
    except:
        return timestamp


def sanitize_filename(filename: str) -> str:
    """
    Sanitize filename to be filesystem-safe.

    Args:
        filename: Original filename

    Returns:
        Sanitized filename
    """
    # Remove invalid characters
    sanitized = re.sub(r'[<>:"/\\|?*]', '_', filename)
    # Limit length
    if len(sanitized) > 200:
        sanitized = sanitized[:200]
    return sanitized.strip()


def validate_url(url: str) -> bool:
    """
    Validate URL format.

    Args:
        url: URL to validate

    Returns:
        True if valid, False otherwise
    """
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except:
        return False


async def retry_async(
    func: Callable[..., T],
    max_retries: int = 3,
    initial_delay: float = 1.0,
    max_delay: float = 30.0,
    exceptions: tuple[type[Exception], ...] = (Exception,)
) -> T:
    """
    Retry async function with exponential backoff.

    Args:
        func: Async function to retry
        max_retries: Maximum number of retries
        initial_delay: Initial delay in seconds
        max_delay: Maximum delay in seconds
        exceptions: Exceptions to catch

    Returns:
        Function result

    Raises:
        Last exception if all retries fail
    """
    delay = initial_delay
    last_exception = None

    for attempt in range(max_retries):
        try:
            result = await func()
            return result
        except exceptions as e:
            last_exception = e
            if attempt == max_retries - 1:
                raise

            logger.warning(
                f"Attempt {attempt + 1}/{max_retries} failed: {e}. "
                f"Retrying in {delay:.2f}s..."
            )
            await asyncio.sleep(delay)
            delay = min(delay * 2, max_delay)

    raise last_exception


def chunk_list(items: list[T], chunk_size: int) -> list[list[T]]:
    """
    Split list into chunks.

    Args:
        items: List to chunk
        chunk_size: Size of each chunk

    Returns:
        List of chunks
    """
    return [items[i:i + chunk_size] for i in range(0, len(items), chunk_size)]


def extract_domain(url: str) -> str:
    """
    Extract domain from URL.

    Args:
        url: URL string

    Returns:
        Domain name
    """
    try:
        return urlparse(url).netloc
    except:
        return ""


def parse_bool(value: Any) -> bool:
    """
    Parse boolean from various string formats.

    Args:
        value: Value to parse

    Returns:
        Boolean value
    """
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.lower() in ('true', '1', 'yes', 'on')
    return bool(value)
