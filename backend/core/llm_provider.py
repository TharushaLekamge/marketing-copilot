"""LLM provider abstraction for language model interactions."""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, AsyncIterator, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class LLMResponse:
    """Response from an LLM provider."""

    text: str
    model: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    metadata: Optional[Dict[str, Any]] = None

    @property
    def token_count(self) -> int:
        """Total token count (alias for total_tokens)."""
        return self.total_tokens


@dataclass
class LLMConfig:
    """Configuration for LLM generation."""

    temperature: float = 0.7
    max_tokens: Optional[int] = None
    top_p: Optional[float] = None
    frequency_penalty: Optional[float] = None
    presence_penalty: Optional[float] = None
    stop: Optional[List[str]] = None
    extra_params: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert config to dictionary, excluding None values."""
        result: Dict[str, Any] = {
            "temperature": self.temperature,
        }
        if self.max_tokens is not None:
            result["max_tokens"] = self.max_tokens
        if self.top_p is not None:
            result["top_p"] = self.top_p
        if self.frequency_penalty is not None:
            result["frequency_penalty"] = self.frequency_penalty
        if self.presence_penalty is not None:
            result["presence_penalty"] = self.presence_penalty
        if self.stop is not None:
            result["stop"] = self.stop
        if self.extra_params:
            result.update(self.extra_params)
        return result


class LLMProviderError(Exception):
    """Base exception for LLM provider operations."""

    pass


class LLMProvider(ABC):
    """Abstract interface for LLM providers.

    This interface allows the application to work with different LLM providers
    (OpenAI, Ollama, etc.) through a unified interface. Concrete implementations
    should handle provider-specific details like API calls, authentication, and
    response formatting.
    """

    @abstractmethod
    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        config: Optional[LLMConfig] = None,
    ) -> LLMResponse:
        """Generate text from a prompt.

        Args:
            prompt: The user prompt/message to send to the model
            system_prompt: Optional system prompt to set model behavior
            config: Optional configuration for generation parameters

        Returns:
            LLMResponse: Response containing generated text and metadata

        Raises:
            LLMProviderError: If generation fails
        """
        raise NotImplementedError

    @abstractmethod
    async def generate_async(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        config: Optional[LLMConfig] = None,
    ) -> LLMResponse:
        """Generate text from a prompt asynchronously.

        Args:
            prompt: The user prompt/message to send to the model
            system_prompt: Optional system prompt to set model behavior
            config: Optional configuration for generation parameters

        Returns:
            LLMResponse: Response containing generated text and metadata

        Raises:
            LLMProviderError: If generation fails
        """
        raise NotImplementedError

    @abstractmethod
    async def generate_stream(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        config: Optional[LLMConfig] = None,
    ) -> AsyncIterator[str]:
        """Generate text from a prompt with streaming response.

        Args:
            prompt: The user prompt/message to send to the model
            system_prompt: Optional system prompt to set model behavior
            config: Optional configuration for generation parameters

        Yields:
            str: Text chunks as they are generated

        Raises:
            LLMProviderError: If generation fails
        """
        raise NotImplementedError

    @abstractmethod
    def count_tokens(self, text: str) -> int:
        """Count the number of tokens in a text string.

        Args:
            text: Text to count tokens for

        Returns:
            int: Number of tokens in the text

        Raises:
            LLMProviderError: If token counting fails
        """
        raise NotImplementedError

    @abstractmethod
    def get_model_name(self) -> str:
        """Get the name of the model being used.

        Returns:
            str: Model name/identifier
        """
        raise NotImplementedError

    @abstractmethod
    def get_model_info(self) -> Dict[str, Any]:
        """Get information about the model.

        Returns:
            Dict[str, Any]: Model information (name, context length, etc.)
        """
        raise NotImplementedError

    def validate_config(self, config: Optional[LLMConfig]) -> None:
        """Validate LLM configuration parameters.

        Args:
            config: Configuration to validate

        Raises:
            ValueError: If configuration is invalid
        """
        if config is None:
            return

        if config.temperature < 0 or config.temperature > 2:
            raise ValueError("Temperature must be between 0 and 2")

        if config.max_tokens is not None and config.max_tokens < 1:
            raise ValueError("max_tokens must be at least 1")

        if config.top_p is not None and (config.top_p < 0 or config.top_p > 1):
            raise ValueError("top_p must be between 0 and 1")

        if config.frequency_penalty is not None and (config.frequency_penalty < -2 or config.frequency_penalty > 2):
            raise ValueError("frequency_penalty must be between -2 and 2")

        if config.presence_penalty is not None and (config.presence_penalty < -2 or config.presence_penalty > 2):
            raise ValueError("presence_penalty must be between -2 and 2")
