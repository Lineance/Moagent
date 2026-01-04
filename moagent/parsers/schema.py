from __future__ import annotations

"""
Standardized parsed document schema for MoAgent parsers.
"""

from dataclasses import dataclass, field, asdict
from typing import Optional, List, Dict, Any


@dataclass
class Metadata:
    """Article metadata (extensible)."""

    title: str = ""
    author: Optional[str] = None
    published_at: Optional[str] = None  # ISO timestamp string
    tags: List[str] = field(default_factory=list)
    source_url: Optional[str] = None
    language: Optional[str] = None
    extra: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert metadata to dictionary."""
        return asdict(self)


@dataclass
class ParsedDocument:
    """Normalized parsed document."""

    id: Optional[str] = None
    metadata: Metadata = field(default_factory=Metadata)
    content: str = ""
    summary: Optional[str] = None
    raw: Dict[str, Any] = field(default_factory=dict)
    llm_info: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert document to plain dict."""
        return asdict(self)


