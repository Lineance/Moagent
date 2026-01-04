"""
LLM-Powered Pattern Generator - Core analysis functionality.

Analyzes HTML to generate crawler patterns for list pages (news/article listings).
Optimized to reduce token usage while maintaining accuracy.
"""

import json
import logging
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from bs4 import BeautifulSoup

from ...config.settings import Config
from ...llm import ops_pattern
from ...llm.client import LLMClient, get_llm_client

logger = logging.getLogger(__name__)


@dataclass
class LLMPatternAnalysis:
    """Results from LLM-based pattern analysis."""
    list_container: Dict[str, Any]
    item_selector: Dict[str, Any]
    title_selector: Dict[str, Any]
    url_selector: Dict[str, Any]
    date_selector: Optional[Dict[str, Any]]
    content_selector: Optional[Dict[str, Any]]
    post_process: Dict[str, Any]
    confidence: float
    reasoning: str
    sample_html: str
    llm_response: Dict[str, Any]
    raw_response: str = ""
    llm_metadata: Optional[Dict[str, Any]] = None  # Response time, token usage, etc.

    def __repr__(self):
        return f"LLMPatternAnalysis(confidence={self.confidence:.2f}, reasoning='{self.reasoning[:50]}...')"

    def __getstate__(self):
        """Support for pickle serialization."""
        # Create a copy without potentially problematic llm_response
        state = self.__dict__.copy()
        # Remove or sanitize llm_response if it contains unpicklable objects
        if 'llm_response' in state:
            # Keep only serializable parts of llm_response
            sanitized_response = {}
            for key, value in state['llm_response'].items():
                try:
                    # Try to pickle the value to check if it's serializable
                    import pickle
                    pickle.dumps(value)
                    sanitized_response[key] = value
                except (TypeError, AttributeError, pickle.PicklingError):
                    # If not serializable, store a placeholder
                    sanitized_response[key] = f"<unserializable: {type(value).__name__}>"
            state['llm_response'] = sanitized_response
        return state


class LLMPatternGeneratorAgent:
    """LLM-powered generator for list page patterns with token optimization."""

    def __init__(
        self,
        config: Optional[Config] = None,
        llm: Optional[LLMClient] = None,
        provider: Optional[str] = None,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        base_url: Optional[str] = None,
    ):
        """
        Initialize optimized LLM pattern generator.

        Args:
            config: Global configuration (for provider/model/api keys)
            llm: Optional pre-initialized LLM client (for testing or custom usage)
            provider: Override LLM provider
            api_key: Override API key
            model: Override model name
            base_url: Override base URL
        """
        self.config = config or Config()
        self.llm: LLMClient = llm or get_llm_client(
            config=self.config,
            provider=provider,
            api_key=api_key,
            model=model,
            base_url=base_url,
        )
        self.max_html_chars = 4000  # Reduced from 8000 for list patterns

    def analyze_html_file(self, file_path: str) -> LLMPatternAnalysis:
        """Analyze HTML file using LLM."""
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"HTML file not found: {file_path}")

        with open(path, 'r', encoding='utf-8', errors='ignore') as f:
            html_content = f.read()

        return self.analyze_html_content(html_content)

    def analyze_html_content(self, html_content: str) -> LLMPatternAnalysis:
        """Analyze HTML content using LLM with optimized token usage."""
        # Extract optimized sample
        sample_html = self._extract_optimized_sample(html_content)

        # Delegate to shared LLM ops
        pattern_data = ops_pattern.analyze_list_html(
            self.llm,
            sample_html,
            model=self.config.llm_model,
        )

        return LLMPatternAnalysis(
            list_container=pattern_data.get("list_container", {}),
            item_selector=pattern_data.get("item_selector", {}),
            title_selector=pattern_data.get("title_selector", {}),
            url_selector=pattern_data.get("url_selector", {}),
            date_selector=pattern_data.get("date_selector"),
            content_selector=pattern_data.get("content_selector"),
            post_process=pattern_data.get("post_process", {}),
            confidence=pattern_data.get("confidence", 0.5),
            reasoning=pattern_data.get("reasoning", ""),
            sample_html=sample_html,
            llm_response=pattern_data,
            llm_metadata=pattern_data.get("llm_metadata"),
        )

    def _extract_optimized_sample(self, html_content: str) -> str:
        """Extract representative HTML sample with context."""
        soup = BeautifulSoup(html_content, 'lxml')

        # Find list-like containers - prioritize those with multiple items
        for selector in [
            'ul.wp_article_list', 'div.article-list', 'div.news-list',
            'ul.news-list', 'div.list', 'ul.list', 'article',
        ]:
            elem = soup.select_one(selector)
            if elem:
                # Get container with surrounding context
                html_str = str(elem)
                if 500 < len(html_str) < self.max_html_chars:
                    # Try to include parent context (header/footer exclusion)
                    parent = elem.parent
                    if parent and parent.name not in ['header', 'footer', 'nav']:
                        combined = str(parent)
                        if len(combined) < self.max_html_chars:
                            return combined
                    return html_str

        # Try generic list elements with multiple children
        for tag in ['ul', 'ol']:
            elements = soup.find_all(tag)
            for elem in elements:
                # Skip navigation lists
                if 'nav' in elem.get('class', []) or elem.find_parent(['nav', 'header', 'footer']):
                    continue
                # Only use if has multiple list items
                items = elem.find_all(['li', 'div'], recursive=False)
                if len(items) >= 3:
                    html_str = str(elem)
                    if 500 < len(html_str) < self.max_html_chars:
                        return html_str

        # Fallback: body with context, excluding nav/header/footer
        body = soup.find('body')
        if body:
            # Remove navigation elements before sampling
            for nav in body.find_all(['nav', 'header', 'footer']):
                nav.decompose()
            result = str(body)[:self.max_html_chars * 2]  # More context for fallback
            if len(result) > 500:
                return result

        return html_content[:self.max_html_chars]

    def _parse_llm_response(self, response: Dict[str, Any]) -> Dict[str, Any]:
        """Parse LLM response with robust error handling (kept for backward compatibility)."""
        data = dict(response)
        required = ["list_container", "item_selector", "title_selector", "url_selector"]
        for field in required:
            if field not in data:
                data[field] = {}
        return data

    def generate_config_yaml(self, analysis: LLMPatternAnalysis, name: str, target_url : str,description: Optional[str] = None) -> Dict[str, Any]:
        """Generate configuration dictionary."""
        config = {
            "target_url": target_url,
            "crawl_mode": "static",
            "crawler_patterns": {
                "list_container": analysis.list_container,
                "item_selector": analysis.item_selector,
                "title_selector": analysis.title_selector,
                "url_selector": analysis.url_selector,
            },
            "check_interval": 3600,
            "timeout": 30,
            "max_retries": 3,
        }

        # Optional fields
        for key, value in [
            ("date_selector", analysis.date_selector),
            ("content_selector", analysis.content_selector),
            ("post_process", analysis.post_process),
        ]:
            if value:
                config["crawler_patterns"][key] = value

        # LLM metadata (without unserializable LLM client)
        llm_metadata = {
            "name": name,
            "description": description or f"LLM-generated pattern for {name}",
            "confidence": analysis.confidence,
            "llm_provider": getattr(self.llm, '_provider', 'unknown'),
            "llm_model": getattr(self.llm, '_model', 'unknown'),
            "reasoning": analysis.reasoning,
            "generated_at": datetime.now().isoformat(),
        }
        
        # Add response metadata if available (response time, token usage, etc.)
        if analysis.llm_metadata:
            llm_metadata.update({
                "response_time_seconds": analysis.llm_metadata.get("response_time"),
                "prompt_tokens": analysis.llm_metadata.get("prompt_tokens"),
                "completion_tokens": analysis.llm_metadata.get("completion_tokens"),
                "total_tokens": analysis.llm_metadata.get("total_tokens"),
                "finish_reason": analysis.llm_metadata.get("finish_reason"),
                "model_used": analysis.llm_metadata.get("model"),
                "provider_used": analysis.llm_metadata.get("provider"),
            })
        
        config["crawler_patterns"]["_llm_metadata"] = llm_metadata

        return config

    def generate_pattern_code(self, analysis: LLMPatternAnalysis, name: str, description: Optional[str] = None) -> str:
        """Generate Python code for pattern."""
        desc = description or f"LLM-generated pattern for {name}"

        code = f'''    "{name}": CrawlerPattern(
        name="{name.title()}",
        description="{desc}",
        list_container={analysis.list_container},
        item_selector={analysis.item_selector},
        title_selector={analysis.title_selector},
        url_selector={analysis.url_selector}'''

        if analysis.date_selector:
            code += f",\\n        date_selector={analysis.date_selector}"
        if analysis.content_selector:
            code += f",\\n        content_selector={analysis.content_selector}"
        if analysis.post_process:
            code += f",\\n        post_process={analysis.post_process}"

        code += "\\n    ),"
        return code

    def explain_analysis(self, analysis: LLMPatternAnalysis) -> str:
        """Generate human-readable explanation."""
        return f"""🤖 LLM Pattern Analysis Report

📊 Confidence: {analysis.confidence:.2f}

🎯 Pattern:
   List: {analysis.list_container}
   Item: {analysis.item_selector}
   Title: {analysis.title_selector}
   URL: {analysis.url_selector}{f"\\n   Date: {analysis.date_selector}" if analysis.date_selector else ""}{f"\\n   Content: {analysis.content_selector}" if analysis.content_selector else ""}{f"\\n   Post: {analysis.post_process}" if analysis.post_process else ""}

💡 Reasoning:
   {analysis.reasoning}

📝 Sample:
   {analysis.sample_html[:150]}..."""

    def batch_analyze(self, html_files: List[str], api_key: Optional[str] = None) -> List[LLMPatternAnalysis]:
        """Analyze multiple files."""
        analyses = []
        for file_path in html_files:
            try:
                analysis = self.analyze_html_file(file_path)
                analyses.append(analysis)
                logger.info(f"✓ {file_path}: confidence={analysis.confidence:.2f}")
            except Exception as e:
                logger.error(f"✗ {file_path}: {e}")
        return analyses