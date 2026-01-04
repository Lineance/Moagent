"""Notification module for MoAgent - supports multiple channels.

This module provides a factory function to get the appropriate notification
backend based on configuration. Currently supports:
- Console (default, simplified)
- Webhook (can be restored from archive/)
- Email (can be restored from archive/)
- Telegram (can be restored from archive/)

Usage:
    from moagent.notify import get_notifier
    from moagent.config.settings import Config

    config = Config(notify_console=True)
    notifier = get_notifier(config)
    notifier.send(items)
"""

from typing import List, Dict, Any, Union
from .simple import ConsoleNotifier

# Import additional notification channels if available (currently in archive/)
try:
    from .webhook import WebhookNotifier
    WEBHOOK_AVAILABLE = True
except ImportError:
    WEBHOOK_AVAILABLE = False

try:
    from .email import EmailNotifier
    EMAIL_AVAILABLE = True
except ImportError:
    EMAIL_AVAILABLE = False

try:
    from .telegram import TelegramNotifier
    TELEGRAM_AVAILABLE = True
except ImportError:
    TELEGRAM_AVAILABLE = False


class BaseNotifier:
    """Base class for all notifiers."""

    def send(self, items: List[Dict[str, Any]]) -> None:
        """Send notification for items."""
        raise NotImplementedError("Subclasses must implement send()")


def get_notifier(config) -> BaseNotifier:
    """
    Factory function to get the appropriate notification backend(s) based on configuration.

    This function inspects the config and returns the appropriate notifier instance.
    Multiple notification channels can be enabled simultaneously.

    Args:
        config: Configuration object with notification settings

    Returns:
        BaseNotifier instance (ConsoleNotifier, WebhookNotifier, etc.)

    Supported Channels:
        - Console: Always available, enabled by notify_console=True
        - Webhook: HTTP webhook notifications (if available)
        - Email: Email notifications (if available)
        - Telegram: Telegram bot notifications (if available)

    Examples:
        >>> config = Config(notify_console=True)
        >>> notifier = get_notifier(config)
        >>> isinstance(notifier, ConsoleNotifier)
        True

        Multiple channels (requires restoration from archive/):
        >>> config = Config(notify_console=True, notify_webhook=True, webhook_url="...")
        >>> notifier = get_notifier(config)  # Returns MultiNotifier
    """
    notifiers = []

    # Console is always available
    if getattr(config, 'notify_console', True):
        notifiers.append(ConsoleNotifier(config))

    # Webhook notifications
    if WEBHOOK_AVAILABLE and getattr(config, 'notify_webhook', False):
        notifiers.append(WebhookNotifier(config))

    # Email notifications
    if EMAIL_AVAILABLE and getattr(config, 'notify_email', False):
        notifiers.append(EmailNotifier(config))

    # Telegram notifications
    if TELEGRAM_AVAILABLE and getattr(config, 'notify_telegram', False):
        notifiers.append(TelegramNotifier(config))

    # Return single notifier or multi-notifier
    if not notifiers:
        # Fallback to console if nothing is configured
        return ConsoleNotifier(config)
    elif len(notifiers) == 1:
        return notifiers[0]
    else:
        # Return a multi-notifier that dispatches to all channels
        return MultiNotifier(notifiers)


class MultiNotifier(BaseNotifier):
    """Composite notifier that sends to multiple channels."""

    def __init__(self, notifiers: List[BaseNotifier]):
        """
        Initialize multi-notifier.

        Args:
            notifiers: List of notifier instances to dispatch to
        """
        self.notifiers = notifiers

    def send(self, items: List[Dict[str, Any]]) -> None:
        """
        Send notification to all configured channels.

        Args:
            items: List of items to notify about
        """
        for notifier in self.notifiers:
            try:
                notifier.send(items)
            except Exception as e:
                # Log error but continue with other notifiers
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f"Notification failed for {notifier.__class__.__name__}: {e}")


__all__ = [
    "BaseNotifier",
    "ConsoleNotifier",
    "MultiNotifier",
    "get_notifier",
]

# Conditionally export additional notifiers if available
if WEBHOOK_AVAILABLE:
    __all__.append("WebhookNotifier")
if EMAIL_AVAILABLE:
    __all__.append("EmailNotifier")
if TELEGRAM_AVAILABLE:
    __all__.append("TelegramNotifier")
