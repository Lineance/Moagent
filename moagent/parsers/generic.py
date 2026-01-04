"""
Generic parsers.

1) Legacy GenericParser: rule-based HTML/content extraction.
2) YamlLLMGenericParser: YAML + LLM powered normalization and summarization.
"""

import logging
import re
from datetime import datetime
from typing import Dict, Any, Optional, List

from bs4 import BeautifulSoup

from .base import BaseParser
from ..config.settings import Config
from .config_loader import load_parser_configs
from ..llm.client import get_llm_client
from .llm_ops import llm_data_wash, llm_detect_metadata, llm_summarize
from .rules import ParserRuleSet
from .schema import Metadata, ParsedDocument

logger = logging.getLogger(__name__)


class GenericParser(BaseParser):
    """Generic parser using simple pattern and HTML structure."""

    def parse(self, raw_item: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Parse raw item using generic patterns only (no YAML/LLM).
        """
        try:
            title = self._extract_title(raw_item)
            url = self._extract_url(raw_item)
            content = self._extract_content(raw_item)
            timestamp = self._extract_timestamp(raw_item)

            if not title and not url:
                logger.debug("Skipping item without title or URL")
                return None

            parsed = {
                "title": self._clean_text(title),
                "url": url,
                "content": self._clean_text(content),
                "timestamp": self._normalize_timestamp(timestamp),
                "source": raw_item.get("source", "generic"),
                "hash": self._extract_hash({"title": title, "url": url, "content": content}),
            }

            if "raw" in raw_item:
                parsed["raw"] = raw_item["raw"]

            return parsed

        except Exception as exc:  # noqa: BLE001
            logger.error("Generic parsing failed: %s", exc)
            return None

    def _extract_title(self, item: Dict[str, Any]) -> str:
        """Extract title from raw item."""
        if "title" in item:
            return str(item["title"])

        if "html" in item:
            soup = BeautifulSoup(item["html"], "lxml")
            for tag in ["h1", "h2", "h3", "h4", "title"]:
                elem = soup.find(tag)
                if elem:
                    return elem.get_text(strip=True)

        if "content" in item:
            content = str(item["content"])
            match = re.match(r"[^.!?]*[.!?]", content)
            if match:
                return match.group(0).strip()
            return content[:100].strip()

        return ""

    def _extract_url(self, item: Dict[str, Any]) -> str:
        """Extract URL from raw item."""
        if "url" in item:
            return str(item["url"])
        if "link" in item:
            return str(item["link"])
        return ""

    def _extract_content(self, item: Dict[str, Any]) -> str:
        """Extract content from raw item."""
        if "content" in item:
            return str(item["content"])

        if "html" in item:
            soup = BeautifulSoup(item["html"], "lxml")
            for tag in soup(["script", "style", "nav", "header", "footer"]):
                tag.decompose()
            main_content = soup.find(["article", "main", "div"], class_=re.compile(r"content|main|article"))
            if main_content:
                return main_content.get_text(separator=" ", strip=True)
            return soup.get_text(separator=" ", strip=True)

        if "summary" in item:
            return str(item["summary"])
        if "description" in item:
            return str(item["description"])

        return ""

    def _extract_timestamp(self, item: Dict[str, Any]) -> str:
        """Extract timestamp from raw item."""
        if "timestamp" in item:
            return str(item["timestamp"])
        if "date" in item:
            return str(item["date"])
        if "published" in item:
            return str(item["published"])

        if "html" in item:
            soup = BeautifulSoup(item["html"], "lxml")
            time_elem = soup.find(["time", "span"], class_=re.compile(r"date|time|published"))
            if time_elem:
                return time_elem.get_text(strip=True)

        return datetime.now().isoformat()


class YamlLLMGenericParser(BaseParser):
    """
    Generic parser powered by YAML configs and LLM:
    - basic field extraction based on YAML FieldRule
    - LLM data wash
    - metadata detection
    - summarization
    """

    def __init__(self, config: Config):
        super().__init__(config)
        self._llm = get_llm_client(config=config)
        self._rules = load_parser_configs(config)

    def parse(self, raw_item: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        try:
            rule = self._select_rule(raw_item)
            if not rule:
                logger.debug("No matching parser rule, falling back to GenericParser")
                return GenericParser(self.config).parse(raw_item)

            base_fields = self._extract_base_fields(raw_item, rule)
            content_raw = base_fields.get("content_raw") or base_fields.get("content") or ""
            if not content_raw:
                logger.debug("No content found in raw item for YAML+LLM parser")
                return None

            # 1) LLM data wash
            clean_tmpl = rule.llm_prompts.get("data_wash")
            if clean_tmpl:
                content_clean = llm_data_wash(
                    self._llm,
                    content_raw,
                    clean_tmpl,
                    extra_ctx={"raw_item": raw_item},
                )
            else:
                content_clean = self._clean_text(content_raw)

            # 2) basic + LLM metadata
            meta = self._build_basic_metadata(raw_item, base_fields)
            meta_tmpl = rule.llm_prompts.get("metadata_detect")
            if meta_tmpl:
                llm_meta = llm_detect_metadata(
                    self._llm,
                    content_clean,
                    meta_tmpl,
                    extra_ctx={"raw_item": raw_item},
                )
                self._merge_llm_metadata(meta, llm_meta)

            # 3) summarization
            summary = ""
            summary_tmpl = rule.llm_prompts.get("summarization")
            if summary_tmpl:
                summary = llm_summarize(
                    self._llm,
                    content_clean,
                    summary_tmpl,
                    extra_ctx={"raw_item": raw_item},
                )

            # 4) build output (ParsedDocument + storage-friendly flat fields)
            parsed_doc = self._build_parsed_document(raw_item, meta, content_clean, summary)
            doc_dict = parsed_doc.to_dict()

            # Flatten for existing storage/notify pipeline
            flat: Dict[str, Any] = {
                "title": meta.title,
                "url": meta.source_url or raw_item.get("url", ""),
                "content": content_clean,
                "timestamp": meta.published_at or "",
                "author": meta.author or "",
                "category": ", ".join(meta.tags) if meta.tags else "",
                "source": raw_item.get("source", "generic"),
                "metadata": meta.to_dict(),
            }
            # Ensure hash field exists for deduplication
            flat["hash"] = self._extract_hash(
                {"title": flat["title"], "url": flat["url"], "content": flat["content"]}
            )

            # Merge nested structure under keys to keep richer info
            flat["parsed_document"] = doc_dict

            return flat

        except Exception as exc:  # noqa: BLE001
            logger.error("YamlLLMGenericParser failed: %s", exc)
            return None

    # ---------- rule selection & base fields ----------

    def _select_rule(self, raw_item: Dict[str, Any]) -> Optional[ParserRuleSet]:
        if not self._rules:
            return None

        source = str(raw_item.get("source", "")).lower()
        url = str(raw_item.get("url", "")).lower()

        def matches(rule: ParserRuleSet) -> bool:
            cond = rule.match_conditions or {}
            src_match = cond.get("source")
            url_contains = cond.get("url_contains")

            if src_match:
                if isinstance(src_match, str) and src_match.lower() != source:
                    return False
                if isinstance(src_match, list) and source not in [str(x).lower() for x in src_match]:
                    return False

            if url_contains:
                if isinstance(url_contains, str) and url_contains not in url:
                    return False
                if isinstance(url_contains, list) and not any(s in url for s in url_contains):
                    return False

            return True

        for rule in self._rules.values():
            if matches(rule):
                return rule

        # Fallback to first rule
        return next(iter(self._rules.values()))

    def _extract_base_fields(self, item: Dict[str, Any], rule: ParserRuleSet) -> Dict[str, Any]:
        from .rules import FieldRule  # local import to avoid circulars

        result: Dict[str, Any] = {}
        for name, fr in rule.fields.items():
            assert isinstance(fr, FieldRule)  # for type checkers
            value_parts: List[str] = []
            for key in fr.source_keys:
                if key in item and item[key] is not None:
                    value_parts.append(str(item[key]))
            value = " ".join(value_parts).strip()
            if fr.clean:
                value = self._clean_text(value)
            result[name] = value
        return result

    # ---------- metadata helpers ----------

    def _build_basic_metadata(self, raw_item: Dict[str, Any], base: Dict[str, Any]) -> Metadata:
        title = base.get("title") or raw_item.get("title") or ""
        url = raw_item.get("url") or raw_item.get("link") or ""

        ts = (
            base.get("published_at")
            or raw_item.get("timestamp")
            or raw_item.get("date")
            or raw_item.get("published")
            or ""
        )
        published_at = self._normalize_timestamp(str(ts)) if ts else None

        tags: List[str] = []
        for key in ("tags", "keywords"):
            v = raw_item.get(key)
            if isinstance(v, list):
                tags.extend(str(x) for x in v)
            elif isinstance(v, str):
                tags.extend(t.strip() for t in v.split(",") if t.strip())

        meta = Metadata(
            title=self._clean_text(str(title)),
            author=self._clean_text(str(raw_item.get("author", ""))) or None,
            published_at=published_at,
            tags=list(dict.fromkeys(tags)),
            source_url=str(url) if url else None,
            language=None,
            extra={},
        )
        return meta

    def _merge_llm_metadata(self, meta: Metadata, llm_meta: Dict[str, Any]) -> None:
        title = llm_meta.get("title")
        if title:
            meta.title = self._clean_text(str(title))

        author = llm_meta.get("author")
        if author:
            meta.author = self._clean_text(str(author))

        ts = llm_meta.get("published_at") or llm_meta.get("timestamp")
        if ts:
            meta.published_at = self._normalize_timestamp(str(ts))

        tags = llm_meta.get("tags") or llm_meta.get("keywords")
        extra_tags: List[str] = []
        if isinstance(tags, list):
            extra_tags = [str(x) for x in tags]
        elif isinstance(tags, str):
            extra_tags = [t.strip() for t in tags.split(",") if t.strip()]

        if extra_tags:
            meta.tags = list(dict.fromkeys(meta.tags + extra_tags))

        lang = llm_meta.get("language")
        if lang:
            meta.language = str(lang)

        for key, value in llm_meta.items():
            if key in {"title", "author", "published_at", "timestamp", "tags", "keywords", "language"}:
                continue
            meta.extra[key] = value

    def _build_parsed_document(
        self,
        raw_item: Dict[str, Any],
        meta: Metadata,
        content: str,
        summary: str,
    ) -> ParsedDocument:
        item_for_hash = {
            "title": meta.title,
            "url": meta.source_url or raw_item.get("url", ""),
            "content": content,
        }
        doc_id = self._extract_hash(item_for_hash)
        llm_info = {
            "provider": self.config.llm_provider,
            "model": self.config.llm_model,
        }
        return ParsedDocument(
            id=doc_id,
            metadata=meta,
            content=content,
            summary=summary or None,
            raw=raw_item,
            llm_info=llm_info,
        )

