"""
LLM Pattern Refinement - Pattern refinement with feedback.

Refines LLM pattern analyses based on user feedback with contextual examples.
Supports iterative refinement, pattern comparison, and validation.
"""

import logging
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass

from .llm_pattern_generator import LLMPatternAnalysis, LLMPatternGeneratorAgent
from ...llm import ops_pattern

logger = logging.getLogger(__name__)


@dataclass
class RefinementResult:
    """Result of pattern refinement with comparison data."""
    original: LLMPatternAnalysis
    refined: LLMPatternAnalysis
    changes: Dict[str, Any]
    improvement_score: float  # 0.0 to 1.0
    validation_passed: bool = False
    validation_errors: List[str] = None

    def __post_init__(self):
        if self.validation_errors is None:
            self.validation_errors = []


class LLMPatternRefinerAgent(LLMPatternGeneratorAgent):
    """
    Extends LLMPatternGeneratorAgent with refinement capabilities.

    Allows refining patterns based on user feedback with contextual correction examples.
    """

    def refine_pattern(
        self,
        analysis: LLMPatternAnalysis,
        feedback: str,
        html_content: str,
        use_examples: bool = True,
    ) -> LLMPatternAnalysis:
        """
        Refine pattern based on feedback with examples.

        Args:
            analysis: Current pattern analysis
            feedback: User feedback on what needs to be fixed
            html_content: HTML content to analyze
            use_examples: Whether to include contextual examples in the prompt

        Returns:
            Refined pattern analysis
        """
        sample = self._extract_optimized_sample(html_content)

        # Enhance feedback with contextual examples if requested
        enhanced_feedback = feedback
        if use_examples:
            examples = self._build_refinement_examples(feedback)
            enhanced_feedback = f"{feedback}\n\n{examples}"

        # Delegate to shared ops_pattern helper
        new_data = ops_pattern.refine_pattern_with_feedback(
            self.llm,
            analysis.llm_response,
            enhanced_feedback,
            sample,
            model=self.config.llm_model,
        )

        return LLMPatternAnalysis(
            list_container=new_data.get("list_container", analysis.list_container),
            item_selector=new_data.get("item_selector", analysis.item_selector),
            title_selector=new_data.get("title_selector", analysis.title_selector),
            url_selector=new_data.get("url_selector", analysis.url_selector),
            date_selector=new_data.get("date_selector", analysis.date_selector),
            content_selector=new_data.get("content_selector", analysis.content_selector),
            post_process=new_data.get("post_process", analysis.post_process),
            confidence=new_data.get("confidence", analysis.confidence),
            reasoning=new_data.get("reasoning", analysis.reasoning),
            sample_html=analysis.sample_html,
            llm_response=new_data,
            llm_metadata=new_data.get("llm_metadata", analysis.llm_metadata),
        )

    def refine_with_comparison(
        self,
        analysis: LLMPatternAnalysis,
        feedback: str,
        html_content: str,
    ) -> RefinementResult:
        """
        Refine pattern and return comparison result.

        Args:
            analysis: Current pattern analysis
            feedback: User feedback on what needs to be fixed
            html_content: HTML content to analyze

        Returns:
            RefinementResult with original, refined, and comparison data
        """
        refined = self.refine_pattern(analysis, feedback, html_content)
        changes = self._compare_patterns(analysis, refined)
        improvement_score = self._calculate_improvement_score(analysis, refined, changes)
        validation_result = self._validate_pattern(refined, html_content)

        return RefinementResult(
            original=analysis,
            refined=refined,
            changes=changes,
            improvement_score=improvement_score,
            validation_passed=validation_result[0],
            validation_errors=validation_result[1],
        )

    def refine_iterative(
        self,
        analysis: LLMPatternAnalysis,
        feedback_list: List[str],
        html_content: str,
        max_iterations: int = 5,
    ) -> LLMPatternAnalysis:
        """
        Iteratively refine pattern with multiple feedback rounds.

        Args:
            analysis: Initial pattern analysis
            feedback_list: List of feedback strings for each iteration
            html_content: HTML content to analyze
            max_iterations: Maximum number of refinement iterations

        Returns:
            Final refined pattern analysis
        """
        current = analysis
        iterations = min(len(feedback_list), max_iterations)

        for i, feedback in enumerate(feedback_list[:iterations], 1):
            logger.info(f"Iteration {i}/{iterations}: Refining pattern...")
            current = self.refine_pattern(current, feedback, html_content, use_examples=(i == 1))
            logger.info(f"Iteration {i} complete: Confidence = {current.confidence:.2f}")

        return current

    def _compare_patterns(
        self,
        original: LLMPatternAnalysis,
        refined: LLMPatternAnalysis,
    ) -> Dict[str, Any]:
        """Compare original and refined patterns to identify changes."""
        changes = {}

        # Compare each field
        for field in [
            "list_container", "item_selector", "title_selector", "url_selector",
            "date_selector", "content_selector", "post_process"
        ]:
            orig_val = getattr(original, field, None)
            ref_val = getattr(refined, field, None)
            if orig_val != ref_val:
                changes[field] = {
                    "original": orig_val,
                    "refined": ref_val,
                }

        # Compare confidence
        if abs(original.confidence - refined.confidence) > 0.01:
            changes["confidence"] = {
                "original": original.confidence,
                "refined": refined.confidence,
                "delta": refined.confidence - original.confidence,
            }

        return changes

    def _calculate_improvement_score(
        self,
        original: LLMPatternAnalysis,
        refined: LLMPatternAnalysis,
        changes: Dict[str, Any],
    ) -> float:
        """Calculate improvement score (0.0 to 1.0) based on changes."""
        score = 0.0

        # Confidence improvement (0.5 weight)
        confidence_delta = refined.confidence - original.confidence
        score += max(0, min(1, confidence_delta + 0.5)) * 0.5

        # Post-process improvements (0.3 weight)
        if "post_process" in changes:
            post_changes = changes["post_process"]
            orig_post = post_changes.get("original", {})
            ref_post = post_changes.get("refined", {})
            # More filters = better (up to a point)
            orig_filter_count = sum(1 for v in orig_post.values() if v)
            ref_filter_count = sum(1 for v in ref_post.values() if v)
            if ref_filter_count > orig_filter_count:
                score += min(0.3, (ref_filter_count - orig_filter_count) * 0.1)

        # Selector improvements (0.2 weight)
        selector_fields = ["list_container", "item_selector", "title_selector", "url_selector"]
        improved_selectors = sum(1 for field in selector_fields if field in changes)
        score += min(0.2, improved_selectors * 0.05)

        return min(1.0, score)

    def _validate_pattern(
        self,
        analysis: LLMPatternAnalysis,
        html_content: str,
    ) -> Tuple[bool, List[str]]:
        """
        Validate pattern by attempting to extract items from HTML.

        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        errors = []

        # Check required fields
        if not analysis.list_container:
            errors.append("Missing list_container")
        if not analysis.item_selector:
            errors.append("Missing item_selector")
        if not analysis.title_selector:
            errors.append("Missing title_selector")
        if not analysis.url_selector:
            errors.append("Missing url_selector")

        # Try to extract items (basic validation)
        try:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html_content, 'lxml')

            # Try to find list container
            list_tag = analysis.list_container.get("tag")
            list_class = analysis.list_container.get("class")
            if list_tag:
                if list_class:
                    container = soup.find(list_tag, class_=list_class)
                else:
                    container = soup.find(list_tag)
                if not container:
                    errors.append(f"List container not found: {list_tag}.{list_class}")
                else:
                    # Try to find items
                    item_tag = analysis.item_selector.get("tag")
                    item_class = analysis.item_selector.get("class")
                    if item_tag:
                        if item_class:
                            items = container.find_all(item_tag, class_=item_class)
                        else:
                            items = container.find_all(item_tag)
                        if not items:
                            errors.append(f"No items found with selector: {item_tag}.{item_class}")
        except Exception as e:
            errors.append(f"Validation error: {str(e)}")

        return len(errors) == 0, errors

    def _build_refinement_examples(self, feedback: str) -> str:
        """
        Build correction examples based on feedback type.

        Args:
            feedback: User feedback text

        Returns:
            Contextual examples for the LLM
        """
        feedback_lower = feedback.lower()

        if "navigation" in feedback_lower or "nav" in feedback_lower or "menu" in feedback_lower:
            return """
CORRECTION EXAMPLES - Navigation Exclusion:

WRONG (includes navigation):
- list_container: div.header-nav (WRONG - navigation!)
- item_selector: li.nav-item (WRONG - menu items!)
- title_selector: a (WRONG - includes "Home", "About")

CORRECT (article only):
- list_container: div.article-list or ul.news-list
- item_selector: li.article-item or div.news-item
- title_selector: h3.title or h2.headline
- Add post_process filters

FILTER TO ADD:
"post_process": {{
  "exclude_url_patterns": ["/menu", "/nav", "/footer", "/header", "/sidebar"],
  "exclude_url_regex": ["/menu/", "/nav/", "/footer/", "/header/", "/sidebar/"],
  "exclude_titles": ["Home", "About", "Contact", "More", "Next", "Previous"],
  "exclude_title_regex": ["^首页$", "^关于", "^联系我们"],
  "min_title_length": 5
}}
"""
        elif "miss" in feedback_lower or "not found" in feedback_lower:
            return """
CORRECTION EXAMPLES - Finding More Articles:

WRONG (too narrow):
- list_container: div.news-list (only found 2 items)

CORRECT (broader search):
- list_container: div.content or div.main or body
- item_selector: div.item or li or article
- Look for: h1, h2, h3, h4, a tags with href

Try these selectors:
- list_container: div[class*="list"], div[class*="news"], div[class*="article"]
- item_selector: div[class*="item"], li, article
- title_selector: h1, h2, h3, h4, a
"""
        elif "false positive" in feedback_lower or "wrong links" in feedback_lower:
            return """
CORRECTION EXAMPLES - False Positives:

WRONG (includes non-articles):
- item_selector: a (includes ALL links)

CORRECT (article-specific):
- item_selector: div.article-item or li.news-item
- title_selector: h3.title (not just any text)
- Add validation filters:
"post_process": {{
  "require_title": true,
  "min_title_length": 8,
  "exclude_url_patterns": ["/category/", "/tag/", "/author/"],
  "exclude_url_regex": ["\\.pdf$", "\\.jpg$", "\\.png$", "/category/", "/tag/", "/author/"],
  "exclude_titles_like": ["Home", "About", "Contact", "Login", "Register"],
  "exclude_title_regex": ["^广告", "^通知", "^公告", "^首页$", "^关于"]
}}
"""
        else:
            return """
CORRECTION GUIDELINES:

If navigation is included:
- Change list_container to div.article-list or ul.news-list
- Add post_process filters for navigation URLs:
  * exclude_url_patterns: ["/menu", "/nav", "/footer"]
  * exclude_url_regex: ["/menu/", "/nav/", "/footer/"]
  * exclude_title_regex: ["^首页$", "^关于"]

If articles are missed:
- Try broader selectors: div.content, div.main
- Use partial class matching: div[class*="list"]

If false positives:
- Add post_process with exclude patterns:
  * exclude_url_regex: ["\\.pdf$", "\\.jpg$", "/category/"]
  * exclude_title_regex: ["^广告", "^通知", "^公告"]
  * require_title: true
  * min_title_length: 8
- Exclude common non-article titles
"""

    def test_pattern_extraction(
        self,
        analysis: LLMPatternAnalysis,
        html_content: str,
        base_url: str = "",
    ) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """
        Test pattern extraction on HTML content.

        Args:
            analysis: Pattern analysis to test
            html_content: HTML content to extract from
            base_url: Base URL for resolving relative links

        Returns:
            Tuple of (extracted_items, statistics)
        """
        from bs4 import BeautifulSoup
        from urllib.parse import urljoin

        soup = BeautifulSoup(html_content, 'lxml')
        items = []
        stats = {
            "items_found": 0,
            "items_with_title": 0,
            "items_with_url": 0,
            "items_filtered": 0,
        }

        try:
            # Find list container
            list_tag = analysis.list_container.get("tag")
            list_class = analysis.list_container.get("class")
            if not list_tag:
                return items, stats

            if list_class:
                container = soup.find(list_tag, class_=list_class)
            else:
                container = soup.find(list_tag)

            if not container:
                return items, stats

            # Find items
            item_tag = analysis.item_selector.get("tag")
            item_class = analysis.item_selector.get("class")
            if item_class:
                list_items = container.find_all(item_tag, class_=item_class)
            else:
                list_items = container.find_all(item_tag)

            stats["items_found"] = len(list_items)

            # Extract data from each item
            for item in list_items:
                item_data = self._extract_item_data_for_test(
                    item, analysis, base_url
                )
                if item_data:
                    items.append(item_data)
                    if item_data.get("title"):
                        stats["items_with_title"] += 1
                    if item_data.get("url"):
                        stats["items_with_url"] += 1

            # Apply post-processing filters
            if analysis.post_process:
                original_count = len(items)
                items = self.apply_post_processing(items, analysis.post_process)
                stats["items_filtered"] = original_count - len(items)

        except Exception as e:
            logger.error(f"Pattern extraction test failed: {e}")
            stats["error"] = str(e)

        return items, stats

    def _extract_item_data_for_test(
        self,
        item,
        analysis: LLMPatternAnalysis,
        base_url: str,
    ) -> Optional[Dict[str, Any]]:
        """Extract data from a single item for testing."""
        from urllib.parse import urljoin
        from datetime import datetime

        try:
            # Extract title
            title = ""
            title_selector = analysis.title_selector
            if title_selector:
                title_type = title_selector.get("type")
                title_class = title_selector.get("class")
                has_link = title_selector.get("link", False)

                if title_type == "direct":
                    title = item.get_text(strip=True)
                else:
                    if title_class:
                        elem = item.find(title_type, class_=title_class)
                    else:
                        elem = item.find(title_type)
                    if elem:
                        if has_link:
                            link_elem = elem.find("a", href=True) if elem.name != "a" else elem
                            if link_elem:
                                title = link_elem.get_text(strip=True)
                        else:
                            title = elem.get_text(strip=True)

            # Extract URL
            url = ""
            url_selector = analysis.url_selector
            if url_selector:
                url_type = url_selector.get("type")
                url_class = url_selector.get("class")
                has_link = url_selector.get("link", False)

                if url_type == "direct" and item.name == "a":
                    url = item.get("href", "")
                elif has_link:
                    if title_class:
                        elem = item.find(url_type, class_=url_class)
                    else:
                        elem = item.find(url_type)
                    if elem:
                        link_elem = elem.find("a", href=True) if elem.name != "a" else elem
                        if link_elem:
                            url = link_elem.get("href", "")
                else:
                    if url_class:
                        elem = item.find(url_type, class_=url_class)
                    else:
                        elem = item.find(url_type)
                    if elem:
                        link_elem = elem.find("a", href=True)
                        if link_elem:
                            url = link_elem.get("href", "")

                if url and base_url:
                    url = urljoin(base_url, url)

            if not title and not url:
                return None

            return {
                "title": title,
                "url": url,
                "content": "",
                "timestamp": datetime.now().isoformat(),
                "source": base_url,
                "type": "html",
            }
        except Exception as e:
            logger.debug(f"Failed to extract item data: {e}")
            return None

    def generate_refinement_report(
        self,
        result: RefinementResult,
        verbose: bool = False,
    ) -> str:
        """
        Generate a human-readable refinement report.

        Args:
            result: RefinementResult to report on
            verbose: Whether to include detailed information

        Returns:
            Formatted report string
        """
        lines = []
        lines.append("=" * 60)
        lines.append("Pattern Refinement Report")
        lines.append("=" * 60)
        lines.append("")

        # Confidence comparison
        orig_conf = result.original.confidence
        ref_conf = result.refined.confidence
        conf_delta = ref_conf - orig_conf
        lines.append(f"Confidence: {orig_conf:.2f} → {ref_conf:.2f} ({conf_delta:+.2f})")
        lines.append(f"Improvement Score: {result.improvement_score:.2f}")
        lines.append("")

        # Changes summary
        if result.changes:
            lines.append("Changes Made:")
            for field, change_data in result.changes.items():
                if field == "confidence":
                    continue
                lines.append(f"  • {field}:")
                if verbose:
                    lines.append(f"    Original: {change_data.get('original')}")
                    lines.append(f"    Refined:  {change_data.get('refined')}")
                else:
                    lines.append(f"    Updated")
            lines.append("")

        # Validation results
        if result.validation_passed:
            lines.append("✅ Validation: PASSED")
        else:
            lines.append("❌ Validation: FAILED")
            if result.validation_errors:
                lines.append("  Errors:")
                for error in result.validation_errors:
                    lines.append(f"    - {error}")
        lines.append("")

        # Reasoning
        if verbose and result.refined.reasoning:
            lines.append("Refinement Reasoning:")
            lines.append(f"  {result.refined.reasoning}")
            lines.append("")

        return "\n".join(lines)

    def apply_post_processing(self, items: List[Dict[str, Any]], post_process: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Apply post-processing filters to clean up results.

        Args:
            items: List of extracted items
            post_process: Filter configuration
                Supported filters:
                - exclude_url_patterns: List of URL substrings to exclude (case-insensitive)
                - exclude_url_regex: List of regex patterns to match against URL
                - exclude_titles: List of exact title strings to exclude
                - exclude_titles_like: List of substrings to match in title
                - exclude_title_regex: List of regex patterns to match against title
                - min_title_length: Minimum title length (0 = no minimum)
                - require_title: Whether title is required

        Returns:
            Filtered list of items
        """
        if not post_process:
            return items

        filtered = []
        import re

        # URL pattern exclusions (substring match)
        exclude_url_patterns = post_process.get("exclude_url_patterns", [])
        # URL regex exclusions
        exclude_url_regex = post_process.get("exclude_url_regex", [])
        # Compile regex patterns for URL
        url_regex_patterns = []
        for pattern_str in exclude_url_regex:
            try:
                url_regex_patterns.append(re.compile(pattern_str, re.IGNORECASE))
            except re.error as e:
                logger.warning(f"Invalid URL regex pattern '{pattern_str}': {e}")
        
        # Title exclusions
        exclude_titles = post_process.get("exclude_titles", [])
        exclude_titles_like = post_process.get("exclude_titles_like", [])
        # Title regex exclusions
        exclude_title_regex = post_process.get("exclude_title_regex", [])
        # Compile regex patterns for title
        title_regex_patterns = []
        for pattern_str in exclude_title_regex:
            try:
                title_regex_patterns.append(re.compile(pattern_str, re.IGNORECASE))
            except re.error as e:
                logger.warning(f"Invalid title regex pattern '{pattern_str}': {e}")
        
        min_title_length = post_process.get("min_title_length", 0)
        require_title = post_process.get("require_title", False)

        for item in items:
            url = item.get("url", "")
            title = item.get("title", "").strip()
            url_lower = url.lower()
            title_lower = title.lower()

            skip = False

            # Check URL substring patterns
            for pattern in exclude_url_patterns:
                if pattern.lower() in url_lower:
                    skip = True
                    break
            if skip:
                continue

            # Check URL regex patterns
            for pattern in url_regex_patterns:
                if pattern.search(url):
                    skip = True
                    break
            if skip:
                continue

            # Check exact title exclusions
            if title in exclude_titles:
                continue

            # Check title-like exclusions (partial match)
            for exclude in exclude_titles_like:
                if exclude.lower() in title_lower:
                    skip = True
                    break
            if skip:
                continue

            # Check title regex patterns
            for pattern in title_regex_patterns:
                if pattern.search(title):
                    skip = True
                    break
            if skip:
                continue

            # Check minimum title length
            if min_title_length and len(title) < min_title_length:
                continue

            # Check require title
            if require_title and not title:
                continue

            filtered.append(item)

        return filtered

    def batch_refine(
        self,
        analyses: List[Tuple[LLMPatternAnalysis, str, str]],
        max_iterations: int = 3,
    ) -> List[RefinementResult]:
        """
        Batch refine multiple patterns.

        Args:
            analyses: List of tuples (analysis, feedback, html_content)
            max_iterations: Maximum iterations per pattern

        Returns:
            List of RefinementResult objects
        """
        results = []
        total = len(analyses)

        for i, (analysis, feedback, html_content) in enumerate(analyses, 1):
            logger.info(f"Processing {i}/{total}...")
            try:
                result = self.refine_with_comparison(analysis, feedback, html_content)
                results.append(result)
                logger.info(f"  ✓ Confidence: {result.original.confidence:.2f} → {result.refined.confidence:.2f}")
            except Exception as e:
                logger.error(f"  ✗ Failed: {e}")
                # Create a failed result
                results.append(RefinementResult(
                    original=analysis,
                    refined=analysis,
                    changes={},
                    improvement_score=0.0,
                    validation_passed=False,
                    validation_errors=[str(e)],
                ))

        return results

    def refine_with_extraction_test(
        self,
        analysis: LLMPatternAnalysis,
        feedback: str,
        html_content: str,
        base_url: str = "",
    ) -> Tuple[RefinementResult, List[Dict[str, Any]], Dict[str, Any]]:
        """
        Refine pattern and test extraction on the same HTML.

        Args:
            analysis: Current pattern analysis
            feedback: User feedback
            html_content: HTML content
            base_url: Base URL for link resolution

        Returns:
            Tuple of (RefinementResult, extracted_items, extraction_stats)
        """
        # Refine pattern
        result = self.refine_with_comparison(analysis, feedback, html_content)

        # Test extraction with refined pattern
        items, stats = self.test_pattern_extraction(result.refined, html_content, base_url)

        return result, items, stats