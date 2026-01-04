"""
Pattern Generator Package - HTML pattern analysis and generation.

Provides both rule-based and LLM-powered pattern generation for list pages.
"""

from .basic_list_pattern_generator import PatternAnalysis, PatternGeneratorAgent
from .llm_pattern_comparator import LLMPatternComparatorAgent
from .llm_pattern_generator import LLMPatternAnalysis, LLMPatternGeneratorAgent
from .llm_pattern_refiner import LLMPatternRefinerAgent, RefinementResult

__all__ = [
    # Basic pattern generator
    "PatternGeneratorAgent",
    "PatternAnalysis",

    # LLM pattern generator
    "LLMPatternGeneratorAgent",
    "LLMPatternAnalysis",

    # LLM pattern comparator
    "LLMPatternComparatorAgent",

    # LLM pattern refinement
    "LLMPatternRefinerAgent",
    "RefinementResult",
]