"""
Constants and configuration defaults for MoAgent.

Centralized location for magic numbers and configuration constants.
"""

from typing import Dict, Any
from datetime import timedelta

# ============================================================================
# Performance and Concurrency Constants
# ============================================================================

MIN_CHECK_INTERVAL = 60  # Minimum seconds between checks
MIN_TIMEOUT = 5  # Minimum seconds for HTTP timeout
DEFAULT_MAX_RETRIES = 3
DEFAULT_BATCH_SIZE = 10
DEFAULT_MAX_CONCURRENT = 5

# Error thresholds
MAX_ERRORS_THRESHOLD = 10  # Maximum errors before workflow aborts

# ============================================================================
# Cache Configuration
# ============================================================================

# Cache TTL values
HTTP_CACHE_TTL = timedelta(hours=1)
LLM_CACHE_TTL = timedelta(days=7)  # LLM responses rarely change
QUERY_CACHE_TTL = timedelta(minutes=5)

# Cache sizes (LRU cache max entries)
HTTP_CACHE_SIZE = 1000
LLM_CACHE_SIZE = 500
QUERY_CACHE_SIZE = 2000

# ============================================================================
# Rate Limiting Configuration
# ============================================================================

# Default rate limits (requests per minute)
DEFAULT_RATE_LIMIT = 60  # requests per minute
DEFAULT_RATE_LIMIT_BURST = 10  # burst size

# LLM API rate limits (conservative defaults)
OPENAI_RATE_LIMIT = 3000  # requests per minute (tier 1)
ANTHROPIC_RATE_LIMIT = 50  # requests per minute

# ============================================================================
# Retry Configuration
# ============================================================================

# Retry backoff configuration
RETRY_BASE_DELAY = 1  # seconds
RETRY_MAX_DELAY = 60  # seconds
RETRY_MULTIPLIER = 2  # exponential backoff multiplier
RETRY_JITTER = True  # Add random jitter to prevent thundering herd

# Circuit breaker configuration
CIRCUIT_BREAKER_THRESHOLD = 5  # failures before opening
CIRCUIT_BREAKER_TIMEOUT = 60  # seconds before attempting recovery
CIRCUIT_BREAKER_HALF_OPEN_REQUESTS = 3  # requests to test in half-open state

# ============================================================================
# Database Configuration
# ============================================================================

# Database connection pool
DB_POOL_SIZE = 5
DB_MAX_OVERFLOW = 10
DB_POOL_TIMEOUT = 30
DB_POOL_RECYCLE = 3600  # seconds

# Batch operation sizes
DB_BATCH_INSERT_SIZE = 100
DB_BATCH_QUERY_SIZE = 500

# Hash configuration
HASH_ALGORITHM = "sha256"  # Better than MD5, less collision prone
HASH_LENGTH = 32  # Full hex length for SHA-256

# Field length limits (matching database schema)
MAX_TITLE_LENGTH = 500
MAX_URL_LENGTH = 1000
MAX_CONTENT_LENGTH = 10000

# ============================================================================
# Parser Configuration
# ============================================================================

# Content extraction limits
MAX_CONTENT_LENGTH_EXTRACT = 50000  # characters
MIN_CONTENT_LENGTH = 50  # characters

# LLM parsing limits
LLM_MAX_INPUT_LENGTH = 100000  # tokens (rough estimate)
LLM_MAX_OUTPUT_LENGTH = 8000  # tokens

# ============================================================================
# Monitoring and Metrics
# ============================================================================

# Metrics bucket configuration (for histograms)
METRICS_BUCKETS = [0.1, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0, 120.0]

# Monitoring intervals
HEALTH_CHECK_INTERVAL = 30  # seconds
METRICS_COLLECTION_INTERVAL = 60  # seconds

# ============================================================================
# Validation Rules
# ============================================================================

# Valid crawl modes
VALID_CRAWL_MODES = ["list", "static", "dynamic", "auto", "article", "full"]

# Valid LLM providers
VALID_LLM_PROVIDERS = ["openai", "anthropic", "local"]

# Valid parser modes
VALID_PARSER_MODES = ["generic", "llm", "hybrid"]

# Valid log levels
VALID_LOG_LEVELS = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]

# ============================================================================
# Plugin Configuration
# ============================================================================

# Entry point groups
PLUGIN_GROUP_CRAWLERS = "moagent.crawlers"
PLUGIN_GROUP_PARSERS = "moagent.parsers"
PLUGIN_GROUP_NOTIFIERS = "moagent.notifiers"
PLUGIN_GROUP_STORAGE = "moagent.storage"

# ============================================================================
# HTTP Defaults
# ============================================================================

DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)

DEFAULT_HTTP_HEADERS = {
    "User-Agent": DEFAULT_USER_AGENT,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
    "Accept-Encoding": "gzip, deflate",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
}

# ============================================================================
# File System Configuration
# ============================================================================

DEFAULT_CONFIG_DIR = "configs"
DEFAULT_DATA_DIR = "data"
DEFAULT_LOG_DIR = "logs"
DEFAULT_CACHE_DIR = "cache"

# ============================================================================
# Async Configuration
# ============================================================================

DEFAULT_ASYNC_TIMEOUT = 300  # seconds
ASYNC_SEMAPHORE_PERMITS = 10  # max concurrent async operations

# ============================================================================
# Deprecation Warnings
# ============================================================================

DEPRECATED_CRAWL_MODES = ["static"]  # Use 'list' instead
DEPRECATED_CONFIG_FLAGS = ["use_llm_parsing"]  # Use 'parser_mode' instead

# ============================================================================
# Feature Flags
# ============================================================================

# Enable experimental features
ENABLE_ASYNC_PROCESSING = True
ENABLE_CACHING = True
ENABLE_MONITORING = True
ENABLE_PLUGINS = True

# ============================================================================
# Helper Functions
# ============================================================================


def get_rate_limit_for_provider(provider: str) -> int:
    """Get rate limit for specific LLM provider."""
    rate_limits = {
        "openai": OPENAI_RATE_LIMIT,
        "anthropic": ANTHROPIC_RATE_LIMIT,
        "local": 100,  # Conservative default for local models
    }
    return rate_limits.get(provider.lower(), DEFAULT_RATE_LIMIT)


def is_valid_mode(mode: str, valid_modes: list) -> bool:
    """Check if mode is valid."""
    return mode.lower() in [m.lower() for m in valid_modes]


def get_cache_ttl_for_type(cache_type: str) -> timedelta:
    """Get cache TTL for specific cache type."""
    ttls = {
        "http": HTTP_CACHE_TTL,
        "llm": LLM_CACHE_TTL,
        "query": QUERY_CACHE_TTL,
    }
    return ttls.get(cache_type.lower(), HTTP_CACHE_TTL)
