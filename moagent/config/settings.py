"""
Configuration management for MoAgent.

Handles loading, validation, and management of configuration settings
from YAML files, environment variables, and CLI arguments.
"""

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, Dict, Any, List

import yaml
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


@dataclass
class Config:
    """Configuration class for MoAgent settings."""

    # Target settings
    target_url: str = field(default_factory=lambda: os.getenv("TARGET_URL", "https://wjx.seu.edu.cn/zhxw/list.htm"))
    crawl_mode: str = field(default_factory=lambda: os.getenv("CRAWL_MODE", "auto"))

    # LLM settings
    llm_provider: str = field(default_factory=lambda: os.getenv("LLM_PROVIDER", "openai"))
    llm_model: str = field(default_factory=lambda: os.getenv("LLM_MODEL", "gpt-4o-mini"))
    openai_api_key: Optional[str] = field(default_factory=lambda: os.getenv("OPENAI_API_KEY"))
    anthropic_api_key: Optional[str] = field(default_factory=lambda: os.getenv("ANTHROPIC_API_KEY"))
    llm_api_base_url: Optional[str] = field(default_factory=lambda: os.getenv("LLM_API_BASE_URL"))
    llm_temperature: float = field(default_factory=lambda: float(os.getenv("LLM_TEMPERATURE", "0.3")))
    llm_max_tokens: int = field(default_factory=lambda: int(os.getenv("LLM_MAX_TOKENS", "800")))

    # Database settings (SQLite only)
    database_url: str = field(default_factory=lambda: os.getenv("DATABASE_URL", "sqlite:///./data/moagent.db"))

    # Crawling settings
    check_interval: int = field(default_factory=lambda: int(os.getenv("CHECK_INTERVAL", "3600")))
    timeout: int = field(default_factory=lambda: int(os.getenv("TIMEOUT", "30")))
    max_retries: int = field(default_factory=lambda: int(os.getenv("MAX_RETRIES", "3")))

    # Parser settings
    parser_mode: str = field(default_factory=lambda: os.getenv("PARSER_MODE", "generic"))
    use_llm_parsing: bool = field(default_factory=lambda: os.getenv("USE_LLM_PARSING", "false").lower() == "true")

    # Notification settings (console only)
    notify_console: bool = field(default_factory=lambda: os.getenv("NOTIFY_CONSOLE", "true").lower() == "true")

    # Logging settings
    log_level: str = field(default_factory=lambda: os.getenv("LOG_LEVEL", "INFO"))
    log_file: str = field(default_factory=lambda: os.getenv("LOG_FILE", "logs/moagent.log"))

    # Performance settings
    max_concurrent: int = field(default_factory=lambda: int(os.getenv("MAX_CONCURRENT", "5")))
    batch_size: int = field(default_factory=lambda: int(os.getenv("BATCH_SIZE", "10")))

    # Custom headers
    headers: Dict[str, str] = field(default_factory=dict)

    # Crawler pattern configuration
    # Allows adapting to different website structures without code changes
    crawler_patterns: Dict[str, Any] = field(default_factory=dict)

    # Article crawler specific settings
    article_link_patterns: List[Dict[str, Any]] = field(default_factory=list)
    max_articles: int = field(default_factory=lambda: int(os.getenv("MAX_ARTICLES", "10")))
    fetch_full_content: bool = field(default_factory=lambda: os.getenv("FETCH_FULL_CONTENT", "true").lower() == "true")
    content_timeout: int = field(default_factory=lambda: int(os.getenv("CONTENT_TIMEOUT", "60")))

    def __post_init__(self):
        """Validate configuration after initialization."""
        self._validate()
        self._setup_headers()

    def _validate(self) -> None:
        """Validate configuration values."""
        if self.crawl_mode not in ["list", "static", "dynamic", "auto", "article", "full"]:
            raise ValueError(f"Invalid crawl_mode: {self.crawl_mode}")

        if self.llm_provider not in ["openai", "anthropic", "local"]:
            raise ValueError(f"Invalid llm_provider: {self.llm_provider}")

        if self.parser_mode not in ["generic", "llm", "hybrid"]:
            raise ValueError(f"Invalid parser_mode: {self.parser_mode}")

        if self.check_interval < 60:
            raise ValueError("check_interval must be at least 60 seconds")

        if self.timeout < 5:
            raise ValueError("timeout must be at least 5 seconds")

        # Validate crawler patterns if provided
        self._validate_crawler_patterns()

    def _validate_crawler_patterns(self) -> None:
        """Validate crawler_patterns configuration."""
        if not self.crawler_patterns:
            return

        # Check if using pattern_name (reference to predefined pattern)
        if "pattern_name" in self.crawler_patterns:
            # Pattern name validation happens at runtime
            return

        # Validate inline pattern structure
        if isinstance(self.crawler_patterns, dict):
            # Required keys for inline patterns
            selector_keys = ["list_container", "item_selector", "title_selector", "url_selector"]
            missing_keys = [k for k in selector_keys if k not in self.crawler_patterns]

            if missing_keys:
                raise ValueError(
                    f"crawler_patterns missing required keys: {missing_keys}. "
                    f"Required: {selector_keys}"
                )

            # Validate selector structures
            for key in selector_keys:
                selector = self.crawler_patterns[key]
                if not isinstance(selector, dict) or not selector:
                    raise ValueError(
                        f"crawler_patterns.{key} must be a non-empty dict with 'tag' and/or 'class'"
                    )

    def _setup_headers(self) -> None:
        """Setup default HTTP headers."""
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Accept-Encoding": "gzip, deflate",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
        }

    @classmethod
    def from_file(cls, config_path: str | Path) -> "Config":
        """
        Load configuration from YAML file.

        Args:
            config_path: Path to YAML configuration file

        Returns:
            Config instance
        """
        path = Path(config_path)
        if not path.exists():
            raise FileNotFoundError(f"Configuration file not found: {config_path}")

        with open(path, "r") as f:
            data = yaml.safe_load(f)

        # Convert flat dict to nested structure if needed
        return cls(**data)

    def save_to_file(self, config_path: str | Path) -> None:
        """
        Save configuration to YAML file.

        Args:
            config_path: Path to save YAML configuration file
        """
        path = Path(config_path)
        path.parent.mkdir(parents=True, exist_ok=True)

        # Convert to dict, excluding private attributes
        data = {
            "target_url": self.target_url,
            "crawl_mode": self.crawl_mode,
            "llm_provider": self.llm_provider,
            "llm_model": self.llm_model,
            "llm_api_base_url": self.llm_api_base_url,
            "llm_temperature": self.llm_temperature,
            "llm_max_tokens": self.llm_max_tokens,
            "database_url": self.database_url,
            "check_interval": self.check_interval,
            "timeout": self.timeout,
            "max_retries": self.max_retries,
            "parser_mode": self.parser_mode,
            "use_llm_parsing": self.use_llm_parsing,
            "notify_console": self.notify_console,
            "log_level": self.log_level,
            "log_file": self.log_file,
            "max_concurrent": self.max_concurrent,
            "batch_size": self.batch_size,
            "crawler_patterns": self.crawler_patterns,
            "article_link_patterns": self.article_link_patterns,
            "max_articles": self.max_articles,
            "fetch_full_content": self.fetch_full_content,
            "content_timeout": self.content_timeout,
        }

        with open(path, "w") as f:
            yaml.dump(data, f, default_flow_style=False, sort_keys=False)

    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary."""
        return {
            "target_url": self.target_url,
            "crawl_mode": self.crawl_mode,
            "llm_provider": self.llm_provider,
            "llm_model": self.llm_model,
            "llm_api_base_url": self.llm_api_base_url,
            "llm_temperature": self.llm_temperature,
            "llm_max_tokens": self.llm_max_tokens,
            "database_url": self.database_url,
            "check_interval": self.check_interval,
            "timeout": self.timeout,
            "max_retries": self.max_retries,
            "parser_mode": self.parser_mode,
            "use_llm_parsing": self.use_llm_parsing,
            "notify_console": self.notify_console,
            "log_level": self.log_level,
            "log_file": self.log_file,
            "max_concurrent": self.max_concurrent,
            "batch_size": self.batch_size,
            "crawler_patterns": self.crawler_patterns,
            "article_link_patterns": self.article_link_patterns,
            "max_articles": self.max_articles,
            "fetch_full_content": self.fetch_full_content,
            "content_timeout": self.content_timeout,
        }

    def __repr__(self) -> str:
        """String representation of configuration."""
        return f"Config(target_url={self.target_url}, crawl_mode={self.crawl_mode})"
