"""Simple console notification - simplified version.

This module provides console-based notifications only, replacing the
complex multi-channel notification system (webhooks, email, Telegram).

Features:
- Immediate console output
- Formatted display with separators
- Shows title, URL, timestamp, and content preview
- No external dependencies required

Usage:
    from moagent.notify import get_notifier
    from moagent.config.settings import Config

    config = Config(notify_console=True)
    notifier = get_notifier(config)
    notifier.send(items)
"""

import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)


class ConsoleNotifier:
    """Simple console output for new items.

    This notifier prints discovered items directly to the console in a
    formatted, human-readable way.

    Attributes:
        config: Configuration object

    Output Format:
        ============================================================
        📰 MoAgent Found 3 New Items
        ============================================================

        1. Article Title
           URL: https://example.com/article
           Time: 2024-01-01T12:00:00
           Preview: First 150 characters of content...

        2. Another Article
           URL: https://example.com/article2
           ...

        ============================================================

    Example:
        >>> notifier = ConsoleNotifier(config)
        >>> items = [{"title": "News", "url": "...", ...}]
        >>> notifier.send(items)
    """

    def __init__(self, config):
        """Initialize console notifier.

        Args:
            config: Configuration object
        """
        self.config = config

    def send(self, items: List[Dict[str, Any]]) -> None:
        """Send notification to console.

        Args:
            items: List of item dictionaries to display

        Example:
            >>> items = [
            ...     {"title": "News 1", "url": "https://...", "content": "..."},
            ...     {"title": "News 2", "url": "https://...", "content": "..."}
            ... ]
            >>> notifier.send(items)
        """
        if not items:
            logger.info("No new items to notify")
            return

        print("\n" + "="*60)
        print(f"📰 MoAgent Found {len(items)} New Items")
        print("="*60 + "\n")

        for i, item in enumerate(items, 1):
            title = item.get("title", "Untitled")
            url = item.get("url", "")
            timestamp = item.get("timestamp", "")
            content = item.get("content", "")[:150]

            # Handle encoding issues for console output
            try:
                # Try to encode/decode to handle any encoding problems
                title = title.encode('utf-8').decode('utf-8', errors='replace')
                content = content.encode('utf-8').decode('utf-8', errors='replace')
            except Exception:
                # Fallback: use repr to escape problematic characters
                title = repr(title)[1:-1] if title else ""
                content = repr(content)[1:-1] if content else ""

            print(f"{i}. {title}")
            if url:
                print(f"   URL: {url}")
            if timestamp:
                print(f"   Time: {timestamp}")
            if content:
                print(f"   Preview: {content}...")
            print()

        print("="*60)
        logger.info(f"Console notification sent for {len(items)} items")
