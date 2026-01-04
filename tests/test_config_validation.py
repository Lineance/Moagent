"""
Tests for configuration validation.

Tests that Config properly validates settings and raises appropriate errors.
"""

import pytest
from moagent.config.settings import Config


class TestConfigValidation:
    """Test configuration validation logic."""

    def test_valid_default_config(self):
        """Test default configuration is valid."""
        config = Config()

        assert config.crawl_mode in ["list", "static", "dynamic", "auto", "article", "full"]
        assert config.llm_provider in ["openai", "anthropic", "local"]
        assert config.parser_mode in ["generic", "llm", "hybrid"]
        assert config.check_interval >= 60
        assert config.timeout >= 5

    def test_valid_crawl_modes(self):
        """Test all valid crawl modes."""
        valid_modes = ["list", "static", "dynamic", "auto", "article", "full"]

        for mode in valid_modes:
            config = Config(crawl_mode=mode)
            assert config.crawl_mode == mode

    def test_invalid_crawl_mode_raises_error(self):
        """Test invalid crawl_mode raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            Config(crawl_mode="invalid_mode")

        assert "Invalid crawl_mode" in str(exc_info.value)

    def test_valid_llm_providers(self):
        """Test all valid LLM providers."""
        valid_providers = ["openai", "anthropic", "local"]

        for provider in valid_providers:
            config = Config(llm_provider=provider)
            assert config.llm_provider == provider

    def test_invalid_llm_provider_raises_error(self):
        """Test invalid llm_provider raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            Config(llm_provider="invalid_provider")

        assert "Invalid llm_provider" in str(exc_info.value)

    def test_valid_parser_modes(self):
        """Test all valid parser modes."""
        valid_modes = ["generic", "llm", "hybrid"]

        for mode in valid_modes:
            config = Config(parser_mode=mode)
            assert config.parser_mode == mode

    def test_invalid_parser_mode_raises_error(self):
        """Test invalid parser_mode raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            Config(parser_mode="invalid_mode")

        assert "Invalid parser_mode" in str(exc_info.value)

    def test_check_interval_minimum(self):
        """Test check_interval minimum value."""
        config = Config(check_interval=60)
        assert config.check_interval == 60

        with pytest.raises(ValueError) as exc_info:
            Config(check_interval=59)

        assert "at least 60 seconds" in str(exc_info.value)

    def test_timeout_minimum(self):
        """Test timeout minimum value."""
        config = Config(timeout=5)
        assert config.timeout == 5

        with pytest.raises(ValueError) as exc_info:
            Config(timeout=4)

        assert "at least 5 seconds" in str(exc_info.value)


class TestPatternValidation:
    """Test crawler pattern validation."""

    def test_empty_patterns_valid(self):
        """Test empty crawler_patterns is valid."""
        config = Config(crawler_patterns={})
        # Should not raise any error
        assert config.crawler_patterns == {}

    def test_pattern_name_valid(self):
        """Test pattern_name reference is valid."""
        config = Config(crawler_patterns={"pattern_name": "seu_news"})
        # Should not raise any error
        assert "pattern_name" in config.crawler_patterns

    def test_inline_pattern_complete(self):
        """Test complete inline pattern is valid."""
        patterns = {
            "list_container": {"tag": "ul", "class": "news"},
            "item_selector": {"tag": "li"},
            "title_selector": {"tag": "a"},
            "url_selector": {"tag": "a", "attr": "href"}
        }
        config = Config(crawler_patterns=patterns)
        # Should not raise any error
        assert len(config.crawler_patterns) == 4

    def test_inline_pattern_missing_keys(self):
        """Test inline pattern with missing keys raises error."""
        patterns = {
            "list_container": {"tag": "ul"},
            # Missing item_selector, title_selector, url_selector
        }

        with pytest.raises(ValueError) as exc_info:
            Config(crawler_patterns=patterns)

        assert "missing required keys" in str(exc_info.value)

    def test_inline_pattern_invalid_selector_structure(self):
        """Test inline pattern with invalid selector structure."""
        patterns = {
            "list_container": {"tag": "ul"},
            "item_selector": "",  # Empty selector
            "title_selector": {"tag": "a"},
            "url_selector": {"tag": "a", "attr": "href"}
        }

        with pytest.raises(ValueError) as exc_info:
            Config(crawler_patterns=patterns)

        assert "must be a non-empty dict" in str(exc_info.value)

    def test_inline_pattern_non_dict_selector(self):
        """Test inline pattern with non-dict selector."""
        patterns = {
            "list_container": "invalid",  # Should be dict
            "item_selector": {"tag": "li"},
            "title_selector": {"tag": "a"},
            "url_selector": {"tag": "a"}
        }

        with pytest.raises(ValueError) as exc_info:
            Config(crawler_patterns=patterns)

        assert "must be a non-empty dict" in str(exc_info.value)


class TestConfigFileOperations:
    """Test configuration file save/load operations."""

    import tempfile
    from pathlib import Path

    def test_save_and_load_config(self):
        """Test saving and loading configuration file."""
        import tempfile
        from pathlib import Path

        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            temp_path = Path(f.name)

        try:
            # Create and save config
            original_config = Config(
                target_url="https://example.com",
                crawl_mode="auto",
                llm_model="gpt-4"
            )
            original_config.save_to_file(temp_path)

            # Load config
            loaded_config = Config.from_file(temp_path)

            assert loaded_config.target_url == "https://example.com"
            assert loaded_config.crawl_mode == "auto"
            assert loaded_config.llm_model == "gpt-4"
        finally:
            temp_path.unlink()

    def test_load_nonexistent_file_raises_error(self):
        """Test loading non-existent file raises error."""
        from pathlib import Path

        with pytest.raises(FileNotFoundError):
            Config.from_file(Path("/nonexistent/file.yaml"))

    def test_to_dict_conversion(self):
        """Test converting config to dictionary."""
        config = Config(
            target_url="https://example.com",
            crawl_mode="dynamic"
        )

        config_dict = config.to_dict()

        assert isinstance(config_dict, dict)
        assert config_dict["target_url"] == "https://example.com"
        assert config_dict["crawl_mode"] == "dynamic"
        assert "database_url" in config_dict


class TestConfigHeaders:
    """Test HTTP headers configuration."""

    def test_default_headers_set(self):
        """Test default headers are set."""
        config = Config()

        assert config.headers is not None
        assert "User-Agent" in config.headers
        assert "Accept" in config.headers
        assert "Accept-Language" in config.headers

    def test_custom_headers_merge(self):
        """Test custom headers can be added."""
        config = Config()
        config.headers["X-Custom-Header"] = "CustomValue"

        assert config.headers["X-Custom-Header"] == "CustomValue"
        assert "User-Agent" in config.headers  # Default still present


class TestConfigRepr:
    """Test config string representation."""

    def test_repr_contains_key_info(self):
        """Test __repr__ contains key information."""
        config = Config(
            target_url="https://example.com",
            crawl_mode="auto"
        )

        repr_str = repr(config)

        assert "target_url" in repr_str
        assert "crawl_mode" in repr_str
