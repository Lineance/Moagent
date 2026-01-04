"""
MoAgent - LangGraph-based intelligent news crawler system

A modular agent system for crawling, parsing, and processing news content
from Southeast University news portal and other sources.
"""

__version__ = "0.1.0"
__author__ = "MoAgent Team"

from .main import main
from .config.settings import Config

__all__ = ["main", "Config"]
