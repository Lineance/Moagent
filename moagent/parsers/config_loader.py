from __future__ import annotations

"""
Loader for YAML-based parser configurations.
"""

import logging
import os
from pathlib import Path
from typing import Dict, Any, List

import yaml

from ..config.settings import Config
from .rules import ParserRuleSet

logger = logging.getLogger(__name__)

# Simple in-memory cache keyed by config directory path
_PARSER_CONFIG_CACHE: Dict[str, Dict[str, ParserRuleSet]] = {}


def _get_config_dir(config: Config) -> Path:
    """
    Resolve parser config directory.

    Priority:
    1) env PARSER_CONFIG_DIR
    2) ./configs/parsers under current working directory
    """
    env_dir = os.getenv("PARSER_CONFIG_DIR")
    if env_dir:
        return Path(env_dir).expanduser().resolve()
    return (Path.cwd() / "configs" / "parsers").resolve()


def discover_parser_config_files(config: Config) -> List[Path]:
    """Find all YAML config files for parsers."""
    basedir = _get_config_dir(config)
    if not basedir.exists():
        logger.warning("Parser config dir not found: %s", basedir)
        return []
    return sorted(basedir.glob("*.yaml"))


def _load_single_yaml(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    if not isinstance(data, dict):
        raise ValueError(f"Parser config must be a YAML mapping: {path}")
    return data


def load_parser_configs(config: Config, use_cache: bool = True) -> Dict[str, ParserRuleSet]:
    """
    Load all parser rule sets from YAML.

    Returns:
        Mapping from rule name to ParserRuleSet.
    """
    config_dir = _get_config_dir(config)
    cache_key = str(config_dir)
    if use_cache and cache_key in _PARSER_CONFIG_CACHE:
        return _PARSER_CONFIG_CACHE[cache_key]

    rule_sets: Dict[str, ParserRuleSet] = {}
    files = discover_parser_config_files(config)
    if not files:
        logger.warning("No parser YAML configs found in %s", config_dir)

    for path in files:
        try:
            raw_cfg = _load_single_yaml(path)
            rule = ParserRuleSet.from_dict(raw_cfg)
            rule_sets[rule.name] = rule
            logger.info("Loaded parser rule '%s' from %s", rule.name, path)
        except Exception as exc:  # noqa: BLE001
            logger.error("Failed to load parser config %s: %s", path, exc)

    if use_cache:
        _PARSER_CONFIG_CACHE[cache_key] = rule_sets
    return rule_sets


