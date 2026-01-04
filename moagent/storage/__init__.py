"""Storage module for MoAgent - supports multiple backends.

This module provides a factory function to get the appropriate storage backend
based on configuration. Currently supports:
- SQLite (default, simplified)
- PostgreSQL (can be restored from archive/)

Usage:
    from moagent.storage import get_storage
    from moagent.config.settings import Config

    config = Config(database_url="sqlite:///./data/moagent.db")
    storage = get_storage(config)
"""

from typing import Union
from .base import BaseStorage
from .sqlite import SQLiteStorage

# Import PostgreSQL storage if available (currently in archive/)
try:
    from .postgresql import PostgreSQLStorage
    POSTGRESQL_AVAILABLE = True
except ImportError:
    POSTGRESQL_AVAILABLE = False


def get_storage(config) -> BaseStorage:
    """
    Factory function to get the appropriate storage backend based on configuration.

    This function inspects the database_url in the config and returns
    the appropriate storage backend instance.

    Args:
        config: Configuration object with database_url setting

    Returns:
        BaseStorage instance (SQLiteStorage, PostgreSQLStorage, etc.)

    Raises:
        ValueError: If database_url protocol is not supported

    Supported Protocols:
        - "sqlite:///": SQLite storage (default)
        - "postgresql://": PostgreSQL storage (if available)
        - "postgres://": Alias for postgresql://

    Examples:
        >>> config = Config(database_url="sqlite:///./data/moagent.db")
        >>> storage = get_storage(config)
        >>> isinstance(storage, SQLiteStorage)
        True

        >>> config = Config(database_url="postgresql://user:pass@localhost/db")
        >>> storage = get_storage(config)  # Returns PostgreSQLStorage if available
    """
    database_url = config.database_url.lower() if config.database_url else ""

    if not database_url:
        # Default to SQLite if not specified
        return SQLiteStorage(config)

    if database_url.startswith("sqlite:///") or database_url.startswith("sqlite://"):
        return SQLiteStorage(config)

    if database_url.startswith("postgresql://") or database_url.startswith("postgres://"):
        if POSTGRESQL_AVAILABLE:
            return PostgreSQLStorage(config)
        else:
            raise ValueError(
                "PostgreSQL storage requested but not available. "
                "Either install PostgreSQL dependencies or use SQLite. "
                "See archive/storage/postgres.py for restoration instructions."
            )

    # Unknown protocol
    raise ValueError(
        f"Unsupported database protocol in: {config.database_url}. "
        f"Supported protocols: sqlite:///, postgresql://"
    )


__all__ = [
    "BaseStorage",
    "SQLiteStorage",
    "get_storage",
]

# Conditionally export PostgreSQLStorage if available
if POSTGRESQL_AVAILABLE:
    __all__.append("PostgreSQLStorage")
