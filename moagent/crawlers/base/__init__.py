"""
Base classes for the crawler system.

This module provides abstract base classes that define the interfaces
for all crawlers and extractors in the system.
"""

from .crawler import BaseCrawler
from .extractor import BaseExtractor

__all__ = ["BaseCrawler", "BaseExtractor"]