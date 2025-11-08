"""Unit tests for Ollama LLM provider."""

import json
import logging
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import httpx
import pytest

from backend.core.llm_provider import LLMConfig, LLMProviderError
from backend.core.providers.ollama_provider import OllamaProvider

logger = logging.getLogger(__name__)


@pytest.fixture
def mock_sync_response():
    """Create a mock HTTP response for sync calls."""
    response = MagicMock(spec=httpx.Response)
    response.status_code = 200
    response.json.return_value = {
        "response": "This is a test response from Ollama.",
        "done": True,
        "context": [],
        "total_duration": 1000000000,
        "load_duration": 50000000,
        "prompt_eval_count": 10,
        "prompt_eval_duration": 200000000,
        "eval_count": 15,
        "eval_duration": 700000000,
    }
    response.raise_for_status = Mock()
    return response


@pytest.fixture
def mock_async_response():
    """Create a mock HTTP response for async calls."""
    response = MagicMock(spec=httpx.Response)
    response.status_code = 200
    response.json.return_value = {
        "response": "This is an async test response from Ollama.",
        "done": True,
        "context": [],
        "total_duration": 1000000000,
        "load_duration": 50000000,
        "prompt_eval_count": 10,
        "prompt_eval_duration": 200000000,
        "eval_count": 15,
        "eval_duration": 700000000,
    }
    response.raise_for_status = Mock()
    return response


@pytest.fixture
def mock_stream_lines():
    """Create mock streaming response lines."""
    return [
        json.dumps({"response": "Hello", "done": False}),
        json.dumps({"response": " world", "done": False}),
        json.dumps({"response": "!", "done": True}),
    ]


@pytest.fixture
def mock_tokenizer():
    """Create a mock tiktoken tokenizer."""
    tokenizer = MagicMock()
    tokenizer.encode.return_value = [1, 2, 3, 4, 5]  # 5 tokens
    return tokenizer


class TestOllamaProviderInitialization:
    """Tests for OllamaProvider initialization."""

    def test__init__with_defaults(self):
        """Test initialization with default values."""
        with patch("backend.core.providers.ollama_provider.settings") as mock_settings:
            mock_settings.ollama_model = "qwen3vl:4b"
            mock_settings.llm_base_url = "http://localhost:11434"

            provider = OllamaProvider()

            assert provider.model == "qwen3vl:4b"
            assert provider.base_url == "http://localhost:11434"
            assert provider.timeout == 300
            assert provider.tokenizer_model == "cl100k_base"

    def test__init__with_custom_values(self):
        """Test initialization with custom values."""
        provider = OllamaProvider(
            model="llama2",
            base_url="http://custom:11434",
            timeout=600,
            tokenizer_model="gpt-3.5-turbo",
        )

        assert provider.model == "llama2"
        assert provider.base_url == "http://custom:11434"
        assert provider.timeout == 600
        assert provider.tokenizer_model == "gpt-3.5-turbo"

    def test__init__base_url_strips_trailing_slash(self):
        """Test that base_url has trailing slash removed."""
        provider = OllamaProvider(base_url="http://localhost:11434/")

        assert provider.base_url == "http://localhost:11434"


class TestOllamaProviderGenerate:
    """Tests for synchronous generate method."""

    @patch("backend.core.providers.ollama_provider.tiktoken.get_encoding")
    def test__generate__success(
        self,
        mock_get_encoding: MagicMock,
        mock_tokenizer: MagicMock,
        mock_sync_response: MagicMock,
    ):
        """Test successful text generation."""
        mock_get_encoding.return_value = mock_tokenizer

        provider = OllamaProvider(model="test-model")
        provider._sync_client = MagicMock()
        provider._sync_client.post.return_value = mock_sync_response

        response = provider.generate("Test prompt")

        assert response.text == "This is a test response from Ollama."
        assert response.model == "test-model"
        assert response.prompt_tokens == 5  # Mock tokenizer returns 5 tokens
        assert response.completion_tokens == 5
        assert response.total_tokens == 10
        assert response.metadata is not None
        assert response.metadata["done"] is True

        # Verify API was called correctly
        provider._sync_client.post.assert_called_once()
        call_args = provider._sync_client.post.call_args
        assert call_args[0][0] == "/api/generate"
        assert call_args[1]["json"]["model"] == "test-model"
        assert call_args[1]["json"]["prompt"] == "Test prompt"
        assert call_args[1]["json"]["stream"] is False

    @patch("backend.core.providers.ollama_provider.tiktoken.get_encoding")
    def test__generate__with_system_prompt(
        self,
        mock_get_encoding: MagicMock,
        mock_tokenizer: MagicMock,
        mock_sync_response: MagicMock,
    ):
        """Test generation with system prompt."""
        mock_get_encoding.return_value = mock_tokenizer

        provider = OllamaProvider(model="test-model")
        provider._sync_client = MagicMock()
        provider._sync_client.post.return_value = mock_sync_response

        response = provider.generate("User prompt", system_prompt="System prompt")

        assert response.text == "This is a test response from Ollama."

        # Verify system prompt was included
        call_args = provider._sync_client.post.call_args
        assert call_args[1]["json"]["system"] == "System prompt"

    @patch("backend.core.providers.ollama_provider.tiktoken.get_encoding")
    def test__generate__with_config(
        self,
        mock_get_encoding: MagicMock,
        mock_tokenizer: MagicMock,
        mock_sync_response: MagicMock,
    ):
        """Test generation with configuration."""
        mock_get_encoding.return_value = mock_tokenizer

        provider = OllamaProvider(model="test-model")
        provider._sync_client = MagicMock()
        provider._sync_client.post.return_value = mock_sync_response

        config = LLMConfig(temperature=0.9, max_tokens=100, top_p=0.95, stop=["STOP"])
        response = provider.generate("Test prompt", config=config)

        assert response.text == "This is a test response from Ollama."

        # Verify config was included in request
        call_args = provider._sync_client.post.call_args
        request_data = call_args[1]["json"]
        assert request_data["options"]["temperature"] == 0.9
        assert request_data["options"]["num_predict"] == 100  # Ollama uses num_predict
        assert request_data["options"]["top_p"] == 0.95
        assert request_data["options"]["stop"] == ["STOP"]

    @patch("backend.core.providers.ollama_provider.tiktoken.get_encoding")
    def test__generate__http_error(
        self,
        mock_get_encoding: MagicMock,
        mock_tokenizer: MagicMock,
    ):
        """Test generation with HTTP error."""
        mock_get_encoding.return_value = mock_tokenizer

        provider = OllamaProvider(model="test-model")
        provider._sync_client = MagicMock()
        provider._sync_client.post.side_effect = httpx.HTTPError("Connection error")

        with pytest.raises(LLMProviderError, match="Failed to generate text"):
            provider.generate("Test prompt")

    @patch("backend.core.providers.ollama_provider.tiktoken.get_encoding")
    def test__generate__unexpected_error(
        self,
        mock_get_encoding: MagicMock,
        mock_tokenizer: MagicMock,
    ):
        """Test generation with unexpected error."""
        mock_get_encoding.return_value = mock_tokenizer

        provider = OllamaProvider(model="test-model")
        provider._sync_client = MagicMock()
        provider._sync_client.post.side_effect = ValueError("Unexpected error")

        with pytest.raises(LLMProviderError, match="Unexpected error during generation"):
            provider.generate("Test prompt")


class TestOllamaProviderGenerateAsync:
    """Tests for asynchronous generate method."""

    @pytest.mark.asyncio
    @patch("backend.core.providers.ollama_provider.tiktoken.get_encoding")
    async def test__generate_async__success(
        self,
        mock_get_encoding: MagicMock,
        mock_tokenizer: MagicMock,
        mock_client_factory,
    ):
        """Test successful async text generation."""
        mock_get_encoding.return_value = mock_tokenizer

        # Use MockClient fixture instead of AsyncMock
        mock_client = mock_client_factory(
            post_response={
                "response": "This is an async test response from Ollama.",
                "done": True,
                "context": [],
                "total_duration": 1000000000,
                "load_duration": 50000000,
                "prompt_eval_count": 10,
                "prompt_eval_duration": 200000000,
                "eval_count": 15,
                "eval_duration": 700000000,
            }
        )
        
        provider = OllamaProvider(model="test-model")
        provider._client = mock_client

        response = await provider.generate_async("Test prompt")

        assert response.text == "This is an async test response from Ollama."
        assert response.model == "test-model"
        assert response.prompt_tokens == 5
        assert response.completion_tokens == 5
        assert response.total_tokens == 10

        # Verify API was called correctly
        assert mock_client.last_post_args is not None
        path, kwargs = mock_client.last_post_args
        assert path == "/api/generate"
        assert kwargs["json"]["model"] == "test-model"
        assert kwargs["json"]["prompt"] == "Test prompt"
        assert kwargs["json"]["stream"] is False

    @pytest.mark.asyncio
    @patch("backend.core.providers.ollama_provider.tiktoken.get_encoding")
    async def test__generate_async__http_error(
        self,
        mock_get_encoding: MagicMock,
        mock_tokenizer: MagicMock,
        mock_client_factory,
    ):
        """Test async generation with HTTP error."""
        mock_get_encoding.return_value = mock_tokenizer

        # Use MockClient fixture with post_error to simulate HTTP error
        mock_client = mock_client_factory(post_error=httpx.HTTPError("Connection error"))
        
        provider = OllamaProvider(model="test-model")
        provider._client = mock_client

        with pytest.raises(LLMProviderError, match="Failed to generate text"):
            await provider.generate_async("Test prompt")


class TestOllamaProviderGenerateStream:
    """Tests for streaming generate method."""

    @pytest.mark.asyncio
    @patch("backend.core.providers.ollama_provider.tiktoken.get_encoding")
    async def test__generate_stream__success(
        self,
        mock_get_encoding: MagicMock,
        mock_tokenizer: MagicMock,
        mock_stream_lines: list,
        mock_client_factory,
    ):
        """Test successful streaming generation."""
        mock_get_encoding.return_value = mock_tokenizer

        # Use MockClient fixture to patch provider.client
        mock_client = mock_client_factory(response_lines=mock_stream_lines)

        provider = OllamaProvider(model="test-model")
        provider._client = mock_client

        chunks = []
        async for chunk in provider.generate_stream("Test prompt"):
            chunks.append(chunk)

        assert chunks == ["Hello", " world", "!"]

        # Verify API was called correctly
        assert mock_client.last_stream_args is not None
        method, path, kwargs = mock_client.last_stream_args
        assert method == "POST"
        assert path == "/api/generate"
        assert kwargs["json"]["stream"] is True

    @pytest.mark.asyncio
    @patch("backend.core.providers.ollama_provider.tiktoken.get_encoding")
    async def test__generate_stream__http_error(
        self,
        mock_get_encoding: MagicMock,
        mock_tokenizer: MagicMock,
        mock_client_factory,
    ):
        """Test streaming with HTTP error."""
        mock_get_encoding.return_value = mock_tokenizer

        # Use MockClient fixture with raise_on_enter to simulate HTTP error
        mock_client = mock_client_factory(raise_on_enter=httpx.HTTPError("Connection error"))

        provider = OllamaProvider(model="test-model")
        provider._client = mock_client

        with pytest.raises(LLMProviderError, match="Failed to stream text"):
            async for _ in provider.generate_stream("Test prompt"):
                pass

    @pytest.mark.asyncio
    @patch("backend.core.providers.ollama_provider.tiktoken.get_encoding")
    async def test__generate_stream__skips_invalid_json(
        self,
        mock_get_encoding: MagicMock,
        mock_tokenizer: MagicMock,
        mock_client_factory,
    ):
        """Test streaming skips invalid JSON lines."""
        mock_get_encoding.return_value = mock_tokenizer

        mock_stream_lines = [
            json.dumps({"response": "Hello", "done": False}),
            "invalid json line",
            json.dumps({"response": " world", "done": True}),
        ]

        # Use MockClient fixture to patch provider.client
        mock_client = mock_client_factory(response_lines=mock_stream_lines)

        provider = OllamaProvider(model="test-model")
        provider._client = mock_client

        chunks = []
        async for chunk in provider.generate_stream("Test prompt"):
            chunks.append(chunk)

        assert chunks == ["Hello", " world"]


class TestOllamaProviderCountTokens:
    """Tests for token counting."""

    @patch("backend.core.providers.ollama_provider.tiktoken.get_encoding")
    def test__count_tokens__success(
        self,
        mock_get_encoding: MagicMock,
        mock_tokenizer: MagicMock,
    ):
        """Test successful token counting."""
        mock_get_encoding.return_value = mock_tokenizer
        mock_tokenizer.encode.return_value = [1, 2, 3, 4, 5, 6, 7]  # 7 tokens

        provider = OllamaProvider()

        count = provider.count_tokens("Test text to count")

        assert count == 7
        mock_tokenizer.encode.assert_called_once_with("Test text to count")

    @patch("backend.core.providers.ollama_provider.tiktoken.get_encoding")
    def test__count_tokens__empty_string(
        self,
        mock_get_encoding: MagicMock,
        mock_tokenizer: MagicMock,
    ):
        """Test token counting with empty string."""
        mock_get_encoding.return_value = mock_tokenizer

        provider = OllamaProvider()

        count = provider.count_tokens("")

        assert count == 0
        mock_tokenizer.encode.assert_not_called()

    @patch("backend.core.providers.ollama_provider.tiktoken.get_encoding")
    def test__count_tokens__error(
        self,
        mock_get_encoding: MagicMock,
        mock_tokenizer: MagicMock,
    ):
        """Test token counting with error."""
        mock_get_encoding.return_value = mock_tokenizer
        mock_tokenizer.encode.side_effect = Exception("Tokenization error")

        provider = OllamaProvider()

        with pytest.raises(LLMProviderError, match="Failed to count tokens"):
            provider.count_tokens("Test text")


class TestOllamaProviderModelInfo:
    """Tests for model information methods."""

    def test__get_model_name(self):
        """Test getting model name."""
        provider = OllamaProvider(model="test-model")

        assert provider.get_model_name() == "test-model"

    def test__get_model_info(self):
        """Test getting model information."""
        provider = OllamaProvider(
            model="test-model",
            base_url="http://custom:11434",
            tokenizer_model="custom-tokenizer",
        )

        info = provider.get_model_info()

        assert info["provider"] == "ollama"
        assert info["model"] == "test-model"
        assert info["base_url"] == "http://custom:11434"
        assert info["tokenizer_model"] == "custom-tokenizer"


class TestOllamaProviderConfigValidation:
    """Tests for configuration validation."""

    def test__validate_config__valid(self):
        """Test validation with valid config."""
        provider = OllamaProvider()

        config = LLMConfig(temperature=0.7, max_tokens=100, top_p=0.9)
        # Should not raise
        provider.validate_config(config)

    def test__validate_config__invalid_temperature(self):
        """Test validation with invalid temperature."""
        provider = OllamaProvider()

        config = LLMConfig(temperature=3.0)  # > 2

        with pytest.raises(ValueError, match="Temperature must be between 0 and 2"):
            provider.validate_config(config)

    def test__validate_config__invalid_max_tokens(self):
        """Test validation with invalid max_tokens."""
        provider = OllamaProvider()

        config = LLMConfig(max_tokens=0)  # < 1

        with pytest.raises(ValueError, match="max_tokens must be at least 1"):
            provider.validate_config(config)

    def test__validate_config__invalid_top_p(self):
        """Test validation with invalid top_p."""
        provider = OllamaProvider()

        config = LLMConfig(top_p=1.5)  # > 1

        with pytest.raises(ValueError, match="top_p must be between 0 and 1"):
            provider.validate_config(config)

    def test__validate_config__none(self):
        """Test validation with None config."""
        provider = OllamaProvider()

        # Should not raise
        provider.validate_config(None)


class TestOllamaProviderRequestBuilding:
    """Tests for request data building."""

    @patch("backend.core.providers.ollama_provider.tiktoken.get_encoding")
    def test__build_request_data__basic(
        self,
        mock_get_encoding: MagicMock,
        mock_tokenizer: MagicMock,
    ):
        """Test building basic request data."""
        mock_get_encoding.return_value = mock_tokenizer

        provider = OllamaProvider(model="test-model")

        request_data = provider._build_request_data("Test prompt", stream=False)

        assert request_data["model"] == "test-model"
        assert request_data["prompt"] == "Test prompt"
        assert request_data["stream"] is False
        assert "system" not in request_data
        assert "options" not in request_data

    @patch("backend.core.providers.ollama_provider.tiktoken.get_encoding")
    def test__build_request_data__with_system_prompt(
        self,
        mock_get_encoding: MagicMock,
        mock_tokenizer: MagicMock,
    ):
        """Test building request data with system prompt."""
        mock_get_encoding.return_value = mock_tokenizer

        provider = OllamaProvider(model="test-model")

        request_data = provider._build_request_data("Test prompt", system_prompt="System prompt", stream=False)

        assert request_data["system"] == "System prompt"

    @patch("backend.core.providers.ollama_provider.tiktoken.get_encoding")
    def test__build_request_data__with_config(
        self,
        mock_get_encoding: MagicMock,
        mock_tokenizer: MagicMock,
    ):
        """Test building request data with config."""
        mock_get_encoding.return_value = mock_tokenizer

        provider = OllamaProvider(model="test-model")
        config = LLMConfig(
            temperature=0.8,
            max_tokens=200,
            top_p=0.9,
            stop=["STOP", "END"],
            extra_params={"custom_param": "value"},
        )

        request_data = provider._build_request_data("Test prompt", config=config, stream=False)

        assert request_data["options"]["temperature"] == 0.8
        assert request_data["options"]["num_predict"] == 200
        assert request_data["options"]["top_p"] == 0.9
        assert request_data["options"]["stop"] == ["STOP", "END"]
        assert request_data["options"]["custom_param"] == "value"
