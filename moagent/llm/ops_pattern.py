from __future__ import annotations

"""
LLM operations for pattern generation / refinement / comparison.

These helpers encapsulate prompt construction and JSON parsing for
list-page pattern analysis so that agents can stay thin.
"""

import json
import logging
import re
from typing import Any, Dict, List, Optional

from .client import LLMClient

logger = logging.getLogger(__name__)


PATTERN_ANALYSIS_SYSTEM_PROMPT = (
    "You are a web scraping expert. Output ONLY valid JSON describing "
    "news/article list patterns."
)


def _strip_json_from_response(text: str) -> Dict[str, Any]:
    """Extract first JSON object from LLM text output."""
    cleaned = text.strip()
    if cleaned.startswith("```"):
        parts = cleaned.split("```", 2)
        if len(parts) >= 2:
            cleaned = parts[1].strip()
            if cleaned.startswith("json"):
                cleaned = cleaned[4:].strip()
    match = re.search(r"\{[\s\S]*\}", cleaned)
    if not match:
        raise ValueError("No JSON object found in LLM response")
    data = json.loads(match.group(0))
    if not isinstance(data, dict):
        raise ValueError("Top-level JSON must be an object")
    return data


def analyze_list_html(
    llm: LLMClient,
    sample_html: str,
    *,
    model: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Use LLM to analyze list-page HTML and return pattern JSON with metadata.
    
    Returns:
        Dictionary containing pattern data and llm_metadata with:
        - response_time: float (seconds)
        - prompt_tokens: int
        - completion_tokens: int
        - total_tokens: int
        - finish_reason: str
    """
    prompt = f"""Analyze HTML for news/article list pattern. Output JSON only.

HTML:
```html
{sample_html}
```

TASK: Find the article list container and item selectors.

CRITICAL RULES - FOLLOW EXACTLY:
1. EXCLUDE navigation/header/footer/sidebar links
2. EXCLUDE category/filter links and pagination
3. Focus on article links (titles with dates where possible)
4. List container must contain multiple similar items
5. Add post_process filters to exclude non-article items

Required JSON structure:
{{
  "list_container": {{"tag": "ul", "class": "news-list"}},
  "item_selector": {{"tag": "li", "class": "item"}},
  "title_selector": {{"tag": "h3", "class": "title", "link": true}},
  "url_selector": {{"type": "attr", "attr": "href"}},
  "date_selector": {{"tag": "span", "class": "date"}},        // optional
  "content_selector": {{"tag": "p", "class": "summary"}},      // optional
  "post_process": {{                                          // optional, but recommended
    "remove_font_tags": true,                                 // remove <font> tags from titles
    "exclude_url_patterns": ["/menu", "/nav", "/footer" ,"list"],     // exclude URLs containing these substrings
    "exclude_url_regex": ["\\.pdf$", "\\.jpg$", "/category/"], // exclude URLs matching these regex patterns
    "exclude_titles": ["Home", "About", "Contact"],           // exclude exact title matches
    "exclude_titles_like": ["首页", "关于", "联系我们"],        // exclude titles containing these substrings
    "exclude_title_regex": ["^广告" ],         // exclude titles matching these regex patterns
    "min_title_length": 5,                                     // minimum title length (0 = no minimum)
    "require_title": true                                      // require non-empty title
  }},
  "confidence": 0.8,
  "reasoning": "Explain why this pattern is likely correct and what was excluded"
}}

POST_PROCESS GUIDELINES:
- If you see navigation/menu items, add exclude_url_patterns or exclude_url_regex
- If you see non-article titles (like "Home", "About", "广告", "通知"), add exclude_titles or exclude_title_regex
- If you see file links (.pdf, .jpg, etc.), add exclude_url_regex with patterns like ["\\.pdf$", "\\.jpg$"]
- Set min_title_length to filter out very short titles (typically 5-10 characters)
- Set require_title to true to ensure all items have titles

Return ONLY valid JSON, no markdown, no commentary.
"""
    messages: List[Dict[str, str]] = [
        {"role": "system", "content": PATTERN_ANALYSIS_SYSTEM_PROMPT},
        {"role": "user", "content": prompt},
    ]
    try:
        # Use chat_with_metadata to get response with token usage and timing
        response = llm.chat_with_metadata(messages, model=model, temperature=0.3, max_tokens=800)
        data = _strip_json_from_response(response.content)

        # Ensure required fields exist
        for key in ["list_container", "item_selector", "title_selector", "url_selector"]:
            data.setdefault(key, {})

        # Add LLM metadata to the response
        data["llm_metadata"] = {
            "response_time": response.response_time,
            "prompt_tokens": response.prompt_tokens,
            "completion_tokens": response.completion_tokens,
            "total_tokens": response.total_tokens,
            "finish_reason": response.finish_reason,
            "model": response.model,
            "provider": response.provider,
        }

        return data
    except Exception as exc:  # noqa: BLE001
        logger.error("LLM pattern analysis failed: %s", exc)
        raise


def refine_pattern_with_feedback(
    llm: LLMClient,
    current_pattern: Dict[str, Any],
    feedback: str,
    sample_html: str,
    *,
    model: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Refine an existing pattern using user feedback and sample HTML.
    
    Returns:
        Dictionary containing refined pattern data and llm_metadata with:
        - response_time: float (seconds)
        - prompt_tokens: int
        - completion_tokens: int
        - total_tokens: int
        - finish_reason: str
    """
    prompt = f"""Previous pattern analysis:
{json.dumps(current_pattern, indent=2, ensure_ascii=False)}

User Feedback:
{feedback}

HTML Sample:
```html
{sample_html}
```

TASK: Fix the pattern based on the feedback, focusing on article items only.

Return updated JSON with the same structure as the original pattern, including:
- list_container
- item_selector
- title_selector
- url_selector
- date_selector (optional)
- content_selector (optional)
- post_process (optional filters):
  * remove_font_tags: remove <font> tags from titles
  * exclude_url_patterns: exclude URLs containing substrings (e.g., ["/menu", "/nav"])
  * exclude_url_regex: exclude URLs matching regex (e.g., ["\\.pdf$", "/category/"])
  * exclude_titles: exclude exact title matches (e.g., ["Home", "About"])
  * exclude_titles_like: exclude titles containing substrings (e.g., ["首页", "关于"])
  * exclude_title_regex: exclude titles matching regex (e.g., ["^广告", "^通知"])
  * min_title_length: minimum title length (0 = no minimum)
  * require_title: require non-empty title (true/false)
- confidence
- reasoning (describe what changed and why, including what filters were added)

Return ONLY valid JSON, no markdown.
"""
    messages: List[Dict[str, str]] = [
        {"role": "system", "content": PATTERN_ANALYSIS_SYSTEM_PROMPT},
        {"role": "user", "content": prompt},
    ]
    try:
        # Use chat_with_metadata to get response with token usage and timing
        response = llm.chat_with_metadata(messages, model=model, temperature=0.3, max_tokens=800)
        data = _strip_json_from_response(response.content)
        for key in ["list_container", "item_selector", "title_selector", "url_selector"]:
            data.setdefault(key, current_pattern.get(key, {}))

        # Add LLM metadata to the response
        data["llm_metadata"] = {
            "response_time": response.response_time,
            "prompt_tokens": response.prompt_tokens,
            "completion_tokens": response.completion_tokens,
            "total_tokens": response.total_tokens,
            "finish_reason": response.finish_reason,
            "model": response.model,
            "provider": response.provider,
        }

        return data
    except Exception as exc:  # noqa: BLE001
        logger.error("LLM pattern refinement failed: %s", exc)
        raise


