from __future__ import annotations

"""
Unified LLM client wrapper for MoAgent.

This module provides a provider-agnostic LLM interface with flexible
configuration options. It can be initialized from Config objects or
with explicit parameters, making it suitable for both programmatic
and CLI usage.

Key Features:
- Provider-agnostic chat interface
- Automatic API key detection (Config → Environment)
- Support for custom base URLs
- Unified error handling
"""

import logging
import os
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Union

from ..config.settings import Config

logger = logging.getLogger(__name__)


@dataclass
class LLMResponse:
    """LLM response with metadata."""
    content: str
    model: str
    provider: str
    response_time: float  # seconds
    prompt_tokens: Optional[int] = None
    completion_tokens: Optional[int] = None
    total_tokens: Optional[int] = None
    finish_reason: Optional[str] = None
    raw_response: Any = None  # Store raw API response for debugging

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "content": self.content,
            "model": self.model,
            "provider": self.provider,
            "response_time": self.response_time,
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "total_tokens": self.total_tokens,
            "finish_reason": self.finish_reason,
        }


def get_llm_client(
    config: Optional[Config] = None,
    provider: Optional[str] = None,
    api_key: Optional[str] = None,
    model: Optional[str] = None,
    base_url: Optional[str] = None,
) -> LLMClient:
    """
    Unified factory function to get an LLM client with flexible configuration.

    This function provides a single entry point for creating LLM clients,
    automatically handling API key detection and configuration merging.

    Args:
        config: Optional Config object for default settings
        provider: Override provider ("openai", "anthropic")
        api_key: Override API key
        model: Override model name
        base_url: Override base URL for API calls

    Returns:
        Configured LLMClient instance

    Raises:
        ValueError: If required configuration is missing

    Priority order for each setting:
    1. Explicit parameter (highest priority)
    2. Config object
    3. Environment variables
    4. Default values (lowest priority)
    """
    # Start with config defaults
    final_config = config or Config()

    # Override provider FIRST (before API key check)
    # This is critical: provider must be set before checking which API key to use
    if provider is not None:
        final_config.llm_provider = provider

    # Override model
    if model is not None:
        final_config.llm_model = model

    # Handle API key with priority: explicit > config > environment
    # IMPORTANT: This check must come AFTER provider override
    if api_key is not None:
        if final_config.llm_provider == "openai":
            final_config.openai_api_key = api_key
        elif final_config.llm_provider == "anthropic":
            final_config.anthropic_api_key = api_key
        else:
            # If provider is neither, store in both for flexibility
            final_config.openai_api_key = api_key
            final_config.anthropic_api_key = api_key
    else:
        # Auto-detect from config or environment
        _ensure_api_key(final_config)

    # Use explicit base_url if provided, otherwise use config's llm_api_base_url
    effective_base_url = base_url
    if effective_base_url is None and final_config.llm_api_base_url:
        effective_base_url = final_config.llm_api_base_url

    return OpenAILikeClient(final_config, base_url=effective_base_url)


def _ensure_api_key(config: Config) -> None:
    """Ensure API key is available for the configured provider."""
    provider = config.llm_provider

    if provider == "openai":
        if not config.openai_api_key:
            config.openai_api_key = os.getenv("OPENAI_API_KEY")
        if not config.openai_api_key:
            raise ValueError("OpenAI API key not found. Set OPENAI_API_KEY or configure openai_api_key")
    elif provider == "anthropic":
        if not config.anthropic_api_key:
            config.anthropic_api_key = os.getenv("ANTHROPIC_API_KEY")
        if not config.anthropic_api_key:
            raise ValueError("Anthropic API key not found. Set ANTHROPIC_API_KEY or configure anthropic_api_key")
    else:
        raise ValueError(f"Unsupported LLM provider: {provider}")


class LLMClient(ABC):
    """Abstract chat-style LLM client."""

    @abstractmethod
    def chat(
        self,
        messages: List[Dict[str, str]],
        *,
        model: Optional[str] = None,
        temperature: float = 0.1,
        max_tokens: int = 1024,
    ) -> str:
        """
        Send chat messages and return assistant text.

        messages: list of {"role": "system"|"user"|"assistant", "content": str}
        """
        raise NotImplementedError

    @abstractmethod
    def chat_with_metadata(
        self,
        messages: List[Dict[str, str]],
        *,
        model: Optional[str] = None,
        temperature: float = 0.1,
        max_tokens: int = 1024,
    ) -> LLMResponse:
        """
        Send chat messages and return response with metadata.

        messages: list of {"role": "system"|"user"|"assistant", "content": str}
        """
        raise NotImplementedError


class OpenAILikeClient(LLMClient):
    """
    Thin wrapper over OpenAI / Anthropic style APIs.

    Supports custom base URLs and flexible configuration.
    """

    def __init__(self, config: Config, base_url: Optional[str] = None):
        self.config = config
        self._provider = config.llm_provider
        self._model = config.llm_model
        self._base_url = base_url
        self._client: Any | None = None  # type: ignore[assignment]
        self._init_client()

    def _init_client(self) -> None:
        try:
            if self._provider == "openai":
                from openai import OpenAI

                if not self.config.openai_api_key:
                    raise ValueError("OpenAI API key not configured")

                kwargs = {"api_key": self.config.openai_api_key}
                if self._base_url:
                    kwargs["base_url"] = self._base_url
                    logger.warning(f"Using custom base_url for OpenAI: {self._base_url}")
                self._client = OpenAI(**kwargs)

            elif self._provider == "anthropic":
                from anthropic import Anthropic

                if not self.config.anthropic_api_key:
                    raise ValueError("Anthropic API key not configured")

                kwargs = {"api_key": self.config.anthropic_api_key}
                if self._base_url:
                    # Validate base_url for Anthropic
                    base_url_str = str(self._base_url)
                    if not base_url_str.startswith(('http://', 'https://')):
                        raise ValueError(f"Invalid base_url format: {self._base_url}. Must start with http:// or https://")

                    # Warn about custom base_url
                    logger.warning(f"Using custom base_url for Anthropic: {self._base_url}")
                    logger.warning("Note: Custom base_url should point to Anthropic API compatible endpoint (e.g., https://api.anthropic.com)")

                    kwargs["base_url"] = self._base_url
                self._client = Anthropic(**kwargs)

            else:
                raise ValueError(f"Unsupported LLM provider: {self._provider}")
        except Exception as exc:  # noqa: BLE001
            logger.error("Failed to initialize LLM client: %s", exc)
            raise

    def chat(
        self,
        messages: List[Dict[str, str]],
        *,
        model: Optional[str] = None,
        temperature: float = 0.1,
        max_tokens: int = 102400,
    ) -> str:
        """Backward-compatible method that returns only content."""
        response = self.chat_with_metadata(
            messages, model=model, temperature=temperature, max_tokens=max_tokens
        )
        return response.content

    def chat_with_metadata(
        self,
        messages: List[Dict[str, str]],
        *,
        model: Optional[str] = None,
        temperature: float = 0.1,
        max_tokens: int = 102400,
    ) -> LLMResponse:
        """Send chat messages and return response with metadata."""
        model_name = model or self.config.llm_model
        start_time = time.time()

        if self._provider == "openai":
            response = self._client.chat.completions.create(  # type: ignore[union-attr]
                model=model_name,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            response_time = time.time() - start_time
            
            # Extract token usage from OpenAI response
            usage = getattr(response, 'usage', None)
            prompt_tokens = usage.prompt_tokens if usage else None
            completion_tokens = usage.completion_tokens if usage else None
            total_tokens = usage.total_tokens if usage else None
            
            # Extract finish reason
            finish_reason = response.choices[0].finish_reason if response.choices else None
            
            return LLMResponse(
                content=response.choices[0].message.content or "",
                model=model_name,
                provider=self._provider,
                response_time=response_time,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=total_tokens,
                finish_reason=finish_reason,
                raw_response=response,
            )

        if self._provider == "anthropic":
            response = self._client.messages.create(  # type: ignore[union-attr]
                model=model_name,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            response_time = time.time() - start_time
            
            # Extract token usage from Anthropic response
            usage = getattr(response, 'usage', None)
            prompt_tokens = usage.input_tokens if usage else None
            completion_tokens = usage.output_tokens if usage else None
            total_tokens = (prompt_tokens + completion_tokens) if (prompt_tokens and completion_tokens) else None
            
            # Extract finish reason
            finish_reason = getattr(response, 'stop_reason', None)
            
            # Assume first content block contains plain text
            content = response.content[0].text if response.content else ""
            
            return LLMResponse(
                content=content,
                model=model_name,
                provider=self._provider,
                response_time=response_time,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=total_tokens,
                finish_reason=finish_reason,
                raw_response=response,
            )

        raise ValueError(f"Unsupported provider: {self._provider}")


