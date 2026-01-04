"""Parser module for content extraction and cleaning.

This module provides a factory function to get the appropriate parser
based on configuration. Supports multiple parsing strategies:

Parser Modes:
- "generic": Rule-based extraction (XPath, CSS selectors, regex)
- "llm": Pure LLM-powered extraction
- "hybrid": Generic first, LLM fallback for complex cases

Legacy Configuration:
- use_llm_parsing: If True, equivalent to parser_mode="hybrid"

Usage:
    from moagent.parsers import get_parser
    from moagent.config.settings import Config

    config = Config(parser_mode="hybrid")
    parser = get_parser(config)
    parsed = parser.parse(raw_item)
"""

from typing import Dict, Any
from ..config.settings import Config

from .base import BaseParser
from .generic import GenericParser, YamlLLMGenericParser
from .llm import LLMParser


def get_parser(config: Config) -> BaseParser:
    """
    Get appropriate parser based on configuration.

    This function determines which parser to use based on the parser_mode
    configuration setting. For backward compatibility, it also supports
    the legacy use_llm_parsing flag.

    Parser Mode Selection:
        1. "llm" → LLMParser (pure LLM-powered extraction)
        2. "hybrid" → YamlLLMGenericParser (generic + LLM enhancement)
        3. "generic" or None → GenericParser (rule-based only)

    Args:
        config: Configuration object with parser_mode setting

    Returns:
        BaseParser instance configured according to parser_mode

    Examples:
        >>> config = Config(parser_mode="generic")
        >>> parser = get_parser(config)
        >>> isinstance(parser, GenericParser)
        True

        >>> config = Config(parser_mode="hybrid")
        >>> parser = get_parser(config)
        >>> isinstance(parser, YamlLLMGenericParser)
        True

        >>> config = Config(parser_mode="llm")
        >>> parser = get_parser(config)
        >>> isinstance(parser, LLMParser)
        True

    Note:
        For backward compatibility, the use_llm_parsing flag is still supported:
        - use_llm_parsing=True is equivalent to parser_mode="hybrid"
        - parser_mode takes precedence over use_llm_parsing if both are set
    """
    # Get parser_mode from config
    parser_mode = config.parser_mode.lower() if config.parser_mode else "generic"

    # Handle legacy use_llm_parsing flag for backward compatibility
    if parser_mode == "generic" and config.use_llm_parsing:
        parser_mode = "hybrid"
        logger = __import__('logging').getLogger(__name__)
        logger.info(
            "use_llm_parsing=True is deprecated, use parser_mode='hybrid' instead"
        )

    # Select parser based on mode
    if parser_mode == "llm":
        return LLMParser(config)
    elif parser_mode == "hybrid":
        return YamlLLMGenericParser(config)
    elif parser_mode == "generic":
        return GenericParser(config)
    else:
        # Default to generic parser for unknown modes
        logger = __import__('logging').getLogger(__name__)
        logger.warning(
            f"Unknown parser_mode '{config.parser_mode}', defaulting to 'generic'"
        )
        return GenericParser(config)


__all__ = [
    "BaseParser",
    "GenericParser",
    "YamlLLMGenericParser",
    "LLMParser",
    "get_parser",
]
