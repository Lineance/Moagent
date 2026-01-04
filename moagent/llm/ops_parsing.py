from __future__ import annotations

"""
High-level LLM operations for content parsing:
- data wash / cleaning
- metadata detection
- summarization
- rule generation & refinement
"""

import json
import logging
import re
from typing import Dict, Any, List, Tuple, Optional

from .client import LLMClient
from ..parsers.rules import LLMTemplate
from .templating import render_template

logger = logging.getLogger(__name__)


def _build_messages(tmpl: LLMTemplate, context: Dict[str, Any]) -> List[Dict[str, str]]:
    system = render_template(tmpl.system_prompt, context) if tmpl.system_prompt else ""
    user = render_template(tmpl.user_prompt, context)
    messages: List[Dict[str, str]] = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": user})
    return messages


def _call_llm_and_parse_json(
    llm: LLMClient,
    tmpl: LLMTemplate,
    context: Dict[str, Any],
    *,
    fallback_empty: Any,
) -> Any:
    messages = _build_messages(tmpl, context)
    try:
        text = llm.chat(
            messages,
            model=tmpl.model,
            temperature=tmpl.temperature,
            max_tokens=tmpl.max_tokens,
        )
        if not tmpl.expect_json:
            return text

        match = re.search(r"\{[\s\S]*\}", text)
        if not match:
            raise ValueError("No JSON object found in LLM output")
        return json.loads(match.group(0))
    except Exception as exc:  # noqa: BLE001
        logger.error("LLM JSON call failed (%s): %s", tmpl.name, exc)
        return fallback_empty


def llm_data_wash(
    llm: LLMClient,
    raw_text: str,
    tmpl: LLMTemplate,
    extra_ctx: Optional[Dict[str, Any]] = None,
) -> str:
    """Use LLM to deeply clean raw text."""
    context: Dict[str, Any] = {"content_raw": raw_text}
    if extra_ctx:
        context.update(extra_ctx)

    messages = _build_messages(tmpl, context)
    try:
        text = llm.chat(
            messages,
            model=tmpl.model,
            temperature=tmpl.temperature,
            max_tokens=tmpl.max_tokens,
        )
        return text.strip()
    except Exception as exc:  # noqa: BLE001
        logger.error("LLM data wash failed: %s", exc)
        return raw_text


def llm_detect_metadata(
    llm: LLMClient,
    text: str,
    tmpl: LLMTemplate,
    extra_ctx: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Use LLM to detect metadata (title, author, time, tags, language, etc.)."""
    context: Dict[str, Any] = {"content": text}
    if extra_ctx:
        context.update(extra_ctx)
    data = _call_llm_and_parse_json(llm, tmpl, context, fallback_empty={})
    if not isinstance(data, dict):
        return {}
    return data


def llm_summarize(
    llm: LLMClient,
    text: str,
    tmpl: LLMTemplate,
    extra_ctx: Optional[Dict[str, Any]] = None,
) -> str:
    """Use LLM to summarize content."""
    context: Dict[str, Any] = {"content": text}
    if extra_ctx:
        context.update(extra_ctx)

    messages = _build_messages(tmpl, context)
    try:
        text = llm.chat(
            messages,
            model=tmpl.model,
            temperature=tmpl.temperature,
            max_tokens=tmpl.max_tokens,
        )
        return text.strip()
    except Exception as exc:  # noqa: BLE001
        logger.error("LLM summarize failed: %s", exc)
        return ""


def llm_pattern_generate_and_refine(
    llm: LLMClient,
    examples: List[Tuple[Dict[str, Any], Dict[str, Any]]],
    tmpl: LLMTemplate,
) -> Dict[str, Any]:
    """
    Use LLM to suggest or refine YAML rules from labelled examples.

    examples: list of (raw_item, expected_parsed_dict)
    """
    payload = [
        {"raw": raw, "expected": expected}
        for raw, expected in examples
    ]
    context = {"examples": json.dumps(payload, ensure_ascii=False, indent=2)}

    data = _call_llm_and_parse_json(llm, tmpl, context, fallback_empty={})
    if not isinstance(data, dict):
        return {}
    return data


