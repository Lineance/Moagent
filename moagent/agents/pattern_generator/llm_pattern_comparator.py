"""
LLM Pattern Comparator - Pattern comparison functionality.

Compares two LLM pattern analyses to find common patterns and differences.
"""

import logging
from typing import Any, Dict

from .llm_pattern_generator import LLMPatternAnalysis

logger = logging.getLogger(__name__)


class LLMPatternComparatorAgent:
    """Handles comparison of two LLM pattern analyses."""

    def compare_llm_analyses(self, analysis1: LLMPatternAnalysis, analysis2: LLMPatternAnalysis) -> Dict[str, Any]:
        """
        Compare two analyses.

        Args:
            analysis1: First pattern analysis
            analysis2: Second pattern analysis

        Returns:
            Dictionary with comparison results
        """
        return {
            "confidence_diff": abs(analysis1.confidence - analysis2.confidence),
            "patterns_match": (
                analysis1.list_container == analysis2.list_container and
                analysis1.item_selector == analysis2.item_selector
            ),
            "analysis1": {"confidence": analysis1.confidence, "reasoning": analysis1.reasoning},
            "analysis2": {"confidence": analysis2.confidence, "reasoning": analysis2.reasoning},
        }

    def compare_files(self, analysis1: LLMPatternAnalysis, analysis2: LLMPatternAnalysis, file1: str, file2: str) -> Dict[str, Any]:
        """
        Compare two analyses with file context.

        Args:
            analysis1: First pattern analysis
            analysis2: Second pattern analysis
            file1: First file path
            file2: Second file path

        Returns:
            Dictionary with detailed comparison results
        """
        comparison = self.compare_llm_analyses(analysis1, analysis2)

        # Add file context
        comparison["file1"] = file1
        comparison["file2"] = file2

        # Determine best pattern
        if analysis1.confidence > analysis2.confidence:
            comparison["recommendation"] = {
                "use": file1,
                "confidence": analysis1.confidence,
                "reasoning": analysis1.reasoning
            }
        else:
            comparison["recommendation"] = {
                "use": file2,
                "confidence": analysis2.confidence,
                "reasoning": analysis2.reasoning
            }

        return comparison