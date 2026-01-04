from __future__ import annotations

"""
Lightweight template utilities for LLM prompts.

Currently supports simple {{var}} replacement using a dict context.
"""

import re
from typing import Dict, Any

_VAR_PATTERN = re.compile(r"{{\s*([a-zA-Z0-9_]+)\s*}}")


def render_template(template: str, context: Dict[str, Any]) -> str:
    """Very small template renderer replacing {{var}} with context[var]."""

    def repl(match: re.Match[str]) -> str:
        key = match.group(1)
        value = context.get(key, "")
        if value is None:
            return ""
        return str(value)

    return _VAR_PATTERN.sub(repl, template)


