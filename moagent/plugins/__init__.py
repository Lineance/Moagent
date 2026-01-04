"""
Plugin system for MoAgent.

Provides extensible architecture for custom crawlers, parsers, notifiers, and storage backends.
Uses Python entry points for plugin discovery.
"""

import importlib
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Type, Callable

from ..config.constants import (
    PLUGIN_GROUP_CRAWLERS,
    PLUGIN_GROUP_PARSERS,
    PLUGIN_GROUP_NOTIFIERS,
    PLUGIN_GROUP_STORAGE,
)

logger = logging.getLogger(__name__)


class PluginManager:
    """
    Plugin manager for discovering and loading MoAgent plugins.

    Supports:
    - Entry point-based plugin discovery
    - Dynamic module loading
    - Plugin validation
    - Hot-reloading (development mode)

    Example:
        manager = PluginManager()

        # Discover all plugins
        manager.discover_all()

        # Get a specific crawler plugin
        crawler = manager.get_crawler("custom_crawler")

        # List available plugins
        print(manager.list_plugins())
    """

    def __init__(self):
        """Initialize plugin manager."""
        self.plugins: Dict[str, Dict[str, Type]] = {
            "crawlers": {},
            "parsers": {},
            "notifiers": {},
            "storage": {},
        }
        self._loaded = False

    def discover_all(self) -> None:
        """Discover all plugins from entry points."""
        self.discover_crawlers()
        self.discover_parsers()
        self.discover_notifiers()
        self.discover_storage()
        self._loaded = True
        logger.info(f"Discovered {self.total_count()} plugins")

    def discover_crawlers(self) -> None:
        """Discover crawler plugins."""
        self._discover_entry_points(PLUGIN_GROUP_CRAWLERS, "crawlers")

    def discover_parsers(self) -> None:
        """Discover parser plugins."""
        self._discover_entry_points(PLUGIN_GROUP_PARSERS, "parsers")

    def discover_notifiers(self) -> None:
        """Discover notifier plugins."""
        self._discover_entry_points(PLUGIN_GROUP_NOTIFIERS, "notifiers")

    def discover_storage(self) -> None:
        """Discover storage backend plugins."""
        self._discover_entry_points(PLUGIN_GROUP_STORAGE, "storage")

    def _discover_entry_points(self, group: str, category: str) -> None:
        """
        Discover plugins from entry point group.

        Args:
            group: Entry point group name
            category: Plugin category (crawlers, parsers, etc.)
        """
        try:
            from importlib.metadata import entry_points

            eps = entry_points(group=group)
            for ep in eps:
                try:
                    plugin_class = ep.load()
                    self.plugins[category][ep.name] = plugin_class
                    logger.info(f"Loaded {category} plugin: {ep.name}")
                except Exception as e:
                    logger.error(f"Failed to load plugin {ep.name}: {e}")
        except ImportError:
            logger.warning(f"importlib.metadata not available, skipping entry point discovery for {group}")
        except Exception as e:
            logger.error(f"Failed to discover plugins for {group}: {e}")

    def load_from_module(self, module_path: str, category: str) -> None:
        """
        Load plugin from module path.

        Args:
            module_path: Module path (e.g., "my_package.my_module:MyClass")
            category: Plugin category

        Example:
            manager.load_from_module(
                "my_plugin.crawler:CustomCrawler",
                "crawlers"
            )
        """
        try:
            if ":" in module_path:
                module_name, class_name = module_path.split(":", 1)
                module = importlib.import_module(module_name)
                plugin_class = getattr(module, class_name)
            else:
                plugin_class = importlib.import_module(module_path)

            name = getattr(plugin_class, "__name__", module_path.split(":")[-1])
            self.plugins[category][name] = plugin_class
            logger.info(f"Loaded {category} plugin from module: {name}")
        except Exception as e:
            logger.error(f"Failed to load plugin from {module_path}: {e}")

    def get_crawler(self, name: str) -> Optional[Type]:
        """Get crawler plugin by name."""
        return self.plugins["crawlers"].get(name)

    def get_parser(self, name: str) -> Optional[Type]:
        """Get parser plugin by name."""
        return self.plugins["parsers"].get(name)

    def get_notifier(self, name: str) -> Optional[Type]:
        """Get notifier plugin by name."""
        return self.plugins["notifiers"].get(name)

    def get_storage(self, name: str) -> Optional[Type]:
        """Get storage plugin by name."""
        return self.plugins["storage"].get(name)

    def list_crawlers(self) -> List[str]:
        """List available crawler plugins."""
        return list(self.plugins["crawlers"].keys())

    def list_parsers(self) -> List[str]:
        """List available parser plugins."""
        return list(self.plugins["parsers"].keys())

    def list_notifiers(self) -> List[str]:
        """List available notifier plugins."""
        return list(self.plugins["notifiers"].keys())

    def list_storage(self) -> List[str]:
        """List available storage plugins."""
        return list(self.plugins["storage"].keys())

    def list_plugins(self) -> Dict[str, List[str]]:
        """List all available plugins."""
        return {
            "crawlers": self.list_crawlers(),
            "parsers": self.list_parsers(),
            "notifiers": self.list_notifiers(),
            "storage": self.list_storage(),
        }

    def total_count(self) -> int:
        """Get total number of loaded plugins."""
        return sum(len(plugins) for plugins in self.plugins.values())

    def validate_plugin(self, plugin_class: Type, category: str) -> bool:
        """
        Validate that plugin class has required interface.

        Args:
            plugin_class: Plugin class to validate
            category: Plugin category

        Returns:
            True if valid, False otherwise
        """
        required_methods = {
            "crawlers": ["crawl"],
            "parsers": ["parse"],
            "notifiers": ["send"],
            "storage": ["connect", "store", "is_new", "get_all"],
        }

        if category not in required_methods:
            logger.warning(f"Unknown plugin category: {category}")
            return False

        for method in required_methods[category]:
            if not hasattr(plugin_class, method):
                logger.error(f"Plugin {plugin_class.__name__} missing required method: {method}")
                return False

        return True

    def is_loaded(self) -> bool:
        """Check if plugins have been loaded."""
        return self._loaded


# Global plugin manager instance
_plugin_manager: Optional[PluginManager] = None


def get_plugin_manager() -> PluginManager:
    """Get global plugin manager instance."""
    global _plugin_manager
    if _plugin_manager is None:
        _plugin_manager = PluginManager()
        _plugin_manager.discover_all()
    return _plugin_manager


def register_plugin(
    name: str,
    plugin_class: Type,
    category: str
) -> None:
    """
    Manually register a plugin.

    Useful for plugins that don't use entry points.

    Args:
        name: Plugin name
        plugin_class: Plugin class
        category: Plugin category

    Example:
        class CustomCrawler:
            def crawl(self):
                return items

        register_plugin("custom", CustomCrawler, "crawlers")
    """
    manager = get_plugin_manager()
    manager.plugins[category][name] = plugin_class
    logger.info(f"Registered {category} plugin: {name}")


class PluginDecorator:
    """
    Decorator for registering plugins.

    Example:
        @register_crawler("my_custom_crawler")
        class CustomCrawler:
            def crawl(self):
                return []
    """

    @staticmethod
    def crawler(name: str):
        """Register crawler plugin."""
        def decorator(cls):
            register_plugin(name, cls, "crawlers")
            return cls
        return decorator

    @staticmethod
    def parser(name: str):
        """Register parser plugin."""
        def decorator(cls):
            register_plugin(name, cls, "parsers")
            return cls
        return decorator

    @staticmethod
    def notifier(name: str):
        """Register notifier plugin."""
        def decorator(cls):
            register_plugin(name, cls, "notifiers")
            return cls
        return decorator

    @staticmethod
    def storage(name: str):
        """Register storage plugin."""
        def decorator(cls):
            register_plugin(name, cls, "storage")
            return cls
        return decorator


# Convenience decorators
register_crawler = PluginDecorator.crawler
register_parser = PluginDecorator.parser
register_notifier = PluginDecorator.notifier
register_storage = PluginDecorator.storage


def create_plugin_example():
    """
    Create example plugin file.

    Generates a template file for creating custom plugins.
    """
    example = '''"""
Example MoAgent plugin.

To use this plugin:
1. Install your package: pip install -e .
2. Add entry points in pyproject.toml:
   [project.entry-points."moagent.crawlers"]
   "example_crawler" = "my_plugin:ExampleCrawler"
"""

from moagent.plugins import register_crawler


@register_crawler("example_crawler")
class ExampleCrawler:
    """Example custom crawler plugin."""

    def __init__(self, config):
        """Initialize crawler with config."""
        self.config = config
        self.base_url = config.target_url

    def crawl(self, url: str = None) -> list:
        """
        Crawl URL and return raw data.

        Args:
            url: URL to crawl (uses base_url if None)

        Returns:
            List of raw items
        """
        target_url = url or self.base_url

        # Your crawling logic here
        # For example:
        # import requests
        # response = requests.get(target_url)
        # return [{"title": "...", "url": "..."}]

        return []

    def configure(self, **kwargs):
        """Configure crawler with custom parameters."""
        for key, value in kwargs.items():
            setattr(self, key, value)


# To register other plugin types:
#
# @register_parser("example_parser")
# class ExampleParser:
#     def parse(self, raw_data):
#         return parsed_data
#
# @register_notifier("example_notifier")
# class ExampleNotifier:
#     def send(self, items):
#         pass
#
# @register_storage("example_storage")
# class ExampleStorage:
#     def connect(self):
#         pass
#     def store(self, item):
#         pass
#     def is_new(self, item):
#         pass
#     def get_all(self):
#         pass
'''

    return example
