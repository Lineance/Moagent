from __future__ import annotations

"""
YAML-based parser rule definitions.
"""

from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional


@dataclass
class FieldRule:
    """
    Describe how to extract/clean a field from raw_item.
    """

    source_keys: List[str] = field(default_factory=list)
    clean: bool = True
    required: bool = False

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "FieldRule":
        return cls(
            source_keys=list(data.get("source_keys", []) or []),
            clean=bool(data.get("clean", True)),
            required=bool(data.get("required", False)),
        )


@dataclass
class LLMTemplate:
    """
    LLM prompt template and parameters.
    """

    name: str
    system_prompt: str = ""
    user_prompt: str = ""
    expect_json: bool = False
    model: Optional[str] = None
    temperature: float = 0.1
    max_tokens: int = 1024

    @classmethod
    def from_dict(cls, name: str, data: Dict[str, Any]) -> "LLMTemplate":
        return cls(
            name=name,
            system_prompt=str(data.get("system_prompt", "") or ""),
            user_prompt=str(data.get("user_prompt", "") or ""),
            expect_json=bool(data.get("expect_json", False)),
            model=data.get("model"),
            temperature=float(data.get("temperature", 0.1)),
            max_tokens=int(data.get("max_tokens", 1024)),
        )


@dataclass
class ParserRuleSet:
    """
    One logical rule set for a site/pattern.
    """

    name: str
    match_conditions: Dict[str, Any] = field(default_factory=dict)
    fields: Dict[str, FieldRule] = field(default_factory=dict)
    llm_prompts: Dict[str, LLMTemplate] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ParserRuleSet":
        name = str(data.get("name", "unnamed_rule"))
        match_conditions = dict(data.get("match_conditions", {}) or {})

        fields_cfg = data.get("fields", {}) or {}
        fields: Dict[str, FieldRule] = {
            field_name: FieldRule.from_dict(field_cfg or {})
            for field_name, field_cfg in fields_cfg.items()
        }

        llm_cfg = data.get("llm_prompts", {}) or {}
        llm_prompts: Dict[str, LLMTemplate] = {
            tmpl_name: LLMTemplate.from_dict(tmpl_name, tmpl_cfg or {})
            for tmpl_name, tmpl_cfg in llm_cfg.items()
        }

        return cls(
            name=name,
            match_conditions=match_conditions,
            fields=fields,
            llm_prompts=llm_prompts,
        )


