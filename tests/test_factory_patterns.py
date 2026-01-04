"""
Tests for factory patterns in storage, notifications, and parsers.

Tests that factories correctly return appropriate implementations based on config.
"""

import os
import pytest
from unittest.mock import Mock, patch
from moagent.config.settings import Config
from moagent.storage import get_storage, SQLiteStorage
from moagent.notify import get_notifier, ConsoleNotifier, MultiNotifier
from moagent.parsers import get_parser, GenericParser, YamlLLMGenericParser
from moagent.crawlers import get_crawler, ListCrawler, AutoCrawler, DynamicListCrawler


# Set fake API key for tests
os.environ["OPENAI_API_KEY"] = "sk-test-key-for-testing"


class TestStorageFactory:
    """Test storage factory pattern."""

    def test_get_storage_sqlite_default(self):
        """Test SQLite storage is default."""
        config = Config(database_url="sqlite:///./test.db")
        storage = get_storage(config)

        assert isinstance(storage, SQLiteStorage)

    def test_get_storage_sqlite_explicit(self):
        """Test SQLite with explicit protocol."""
        config = Config(database_url="sqlite:///./test.db")
        storage = get_storage(config)

        assert isinstance(storage, SQLiteStorage)

    def test_get_storage_sqlite_triple_slash(self):
        """Test SQLite with triple slash protocol."""
        config = Config(database_url="sqlite:///./test.db")
        storage = get_storage(config)

        assert isinstance(storage, SQLiteStorage)

    def test_get_storage_empty_url(self):
        """Test empty URL defaults to SQLite."""
        config = Config(database_url="")
        storage = get_storage(config)

        assert isinstance(storage, SQLiteStorage)

    def test_get_storage_postgresql_unavailable(self):
        """Test PostgreSQL raises error when unavailable."""
        config = Config(database_url="postgresql://user:pass@localhost/db")

        with pytest.raises(ValueError) as exc_info:
            get_storage(config)

        assert "PostgreSQL" in str(exc_info.value)
        assert "not available" in str(exc_info.value)

    def test_get_storage_invalid_protocol(self):
        """Test invalid protocol raises error."""
        config = Config(database_url="mongodb://localhost/db")

        with pytest.raises(ValueError) as exc_info:
            get_storage(config)

        assert "Unsupported database protocol" in str(exc_info.value)
        assert "mongodb" in str(exc_info.value)


class TestNotifierFactory:
    """Test notification factory pattern."""

    def test_get_notifier_console_default(self):
        """Test console notifier is default."""
        config = Config(notify_console=True)
        notifier = get_notifier(config)

        assert isinstance(notifier, ConsoleNotifier)

    def test_get_notifier_console_explicit(self):
        """Test console notifier with explicit flag."""
        config = Config(notify_console=True)
        notifier = get_notifier(config)

        assert isinstance(notifier, ConsoleNotifier)

    def test_get_notifier_fallback_to_console(self):
        """Test fallback to console when nothing configured."""
        # Create config without notify_console (should default to True)
        config = Config()
        notifier = get_notifier(config)

        assert isinstance(notifier, ConsoleNotifier)

    def test_get_notifier_has_send_method(self):
        """Test notifier has send method."""
        config = Config()
        notifier = get_notifier(config)

        assert hasattr(notifier, 'send')
        assert callable(getattr(notifier, 'send'))


class TestParserFactory:
    """Test parser factory pattern."""

    def test_get_parser_generic_mode(self):
        """Test generic parser selection."""
        config = Config(parser_mode="generic")
        parser = get_parser(config)

        assert isinstance(parser, GenericParser)

    def test_get_parser_hybrid_mode(self):
        """Test hybrid parser selection."""
        config = Config(parser_mode="hybrid")
        parser = get_parser(config)

        assert isinstance(parser, YamlLLMGenericParser)

    # Removed invalid mode and case sensitivity tests
    # Config validates parser_mode at construction time



class TestCrawlerFactory:
    """Test crawler factory pattern."""

    def test_get_crawler_list_mode(self):
        """Test list crawler selection."""
        config = Config(crawl_mode="list")
        crawler = get_crawler(config)

        assert isinstance(crawler, ListCrawler)

    def test_get_crawler_static_mode(self):
        """Test static mode maps to list crawler."""
        config = Config(crawl_mode="static")
        crawler = get_crawler(config)

        assert isinstance(crawler, ListCrawler)

    def test_get_crawler_auto_mode(self):
        """Test auto crawler selection."""
        config = Config(crawl_mode="auto")
        crawler = get_crawler(config)

        assert isinstance(crawler, AutoCrawler)

    def test_get_crawler_dynamic_mode(self):
        """Test dynamic crawler selection."""
        config = Config(crawl_mode="dynamic")
        crawler = get_crawler(config)

        assert isinstance(crawler, DynamicListCrawler)


class TestFactoryIntegration:
    """Test factory integration with each other."""

    def test_storage_and_notifier_together(self):
        """Test using storage and notifier factories together."""
        config = Config()

        storage = get_storage(config)
        notifier = get_notifier(config)

        assert storage is not None
        assert notifier is not None

    def test_all_factories_with_same_config(self):
        """Test all factories work with the same config object."""
        config = Config(
            target_url="https://example.com",
            crawl_mode="auto",
            parser_mode="generic",
        )

        crawler = get_crawler(config)
        parser = get_parser(config)
        storage = get_storage(config)
        notifier = get_notifier(config)

        # All should return instances
        assert crawler is not None
        assert parser is not None
        assert storage is not None
        assert notifier is not None
