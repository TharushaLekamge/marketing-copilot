"""Unit tests for content generation orchestration."""

import logging
from unittest.mock import AsyncMock, MagicMock, Mock, patch
from uuid import UUID, uuid4

import pytest

from backend.core.generation import (
    ContentGenerationOrchestrator,
    GenerationError,
    generate_content_variants,
)

logger = logging.getLogger(__name__)


@pytest.fixture
def mock_kernel():
    """Create a mock Semantic Kernel instance."""
    kernel = MagicMock()

    # Mock function results
    short_form_result = MagicMock()
    short_form_result.value = "Short form content here"

    long_form_result = MagicMock()
    long_form_result.value = "Long form content here"

    cta_result = MagicMock()
    cta_result.value = "CTA content here"

    # Mock invoke to return different results based on function
    async def mock_invoke(*args, **kwargs):
        function = kwargs.get("function")
        if hasattr(function, "name") and function.name == "generate_short_form":
            return short_form_result
        elif hasattr(function, "name") and function.name == "generate_long_form":
            return long_form_result
        elif hasattr(function, "name") and function.name == "generate_cta":
            return cta_result
        return short_form_result  # default

    kernel.invoke = AsyncMock(side_effect=mock_invoke)

    # Mock add_service
    kernel.add_service = Mock()

    # Mock add_function to return mock functions
    def mock_add_function(*args, **kwargs):
        func = MagicMock()
        func.name = kwargs.get("function_name", "unknown")
        return func

    kernel.add_function = Mock(side_effect=mock_add_function)

    return kernel


@pytest.fixture
def mock_ollama_service():
    """Create a mock OllamaChatCompletion service."""
    return MagicMock()


@pytest.fixture
def sample_project_id():
    """Create a sample project ID."""
    return uuid4()


class TestContentGenerationOrchestratorInit:
    """Tests for ContentGenerationOrchestrator initialization."""

    @patch("backend.core.generation.Kernel")
    @patch("backend.core.generation.OllamaChatCompletion")
    def test__init__uses_default_settings(
        self,
        mock_ollama_class: MagicMock,
        mock_kernel_class: MagicMock,
    ):
        """Test initialization with default settings."""
        mock_kernel = MagicMock()
        mock_kernel_class.return_value = mock_kernel

        mock_ollama_service = MagicMock()
        mock_ollama_class.return_value = mock_ollama_service

        # Mock add_function to return mock functions
        def mock_add_function(*args, **kwargs):
            func = MagicMock()
            func.name = kwargs.get("function_name", "unknown")
            return func

        mock_kernel.add_function = Mock(side_effect=mock_add_function)

        orchestrator = ContentGenerationOrchestrator()

        # Verify Kernel was created
        mock_kernel_class.assert_called_once()

        # Verify OllamaChatCompletion was created with default settings
        mock_ollama_class.assert_called_once()
        call_args = mock_ollama_class.call_args
        assert call_args.kwargs["host"] == "http://localhost:11434"
        assert call_args.kwargs["ai_model_id"] == "qwen3vl:4b"

        # Verify service was added to kernel
        mock_kernel.add_service.assert_called_once_with(mock_ollama_service)

        # Verify functions were registered
        assert mock_kernel.add_function.call_count == 3

        # Verify instance attributes
        assert orchestrator.kernel == mock_kernel
        assert orchestrator.base_url == "http://localhost:11434"
        assert orchestrator.model == "qwen3vl:4b"
        assert orchestrator.short_form_func is not None
        assert orchestrator.long_form_func is not None
        assert orchestrator.cta_func is not None

    @patch("backend.core.generation.Kernel")
    @patch("backend.core.generation.OllamaChatCompletion")
    def test__init__uses_custom_parameters(
        self,
        mock_ollama_class: MagicMock,
        mock_kernel_class: MagicMock,
    ):
        """Test initialization with custom parameters."""
        mock_kernel = MagicMock()
        mock_kernel_class.return_value = mock_kernel

        mock_ollama_service = MagicMock()
        mock_ollama_class.return_value = mock_ollama_service

        # Mock add_function
        def mock_add_function(*args, **kwargs):
            func = MagicMock()
            func.name = kwargs.get("function_name", "unknown")
            return func

        mock_kernel.add_function = Mock(side_effect=mock_add_function)

        custom_base_url = "http://custom-ollama:11434"
        custom_model = "custom-model"

        orchestrator = ContentGenerationOrchestrator(
            base_url=custom_base_url,
            model=custom_model,
        )

        # Verify OllamaChatCompletion was created with custom settings
        call_args = mock_ollama_class.call_args
        assert call_args.kwargs["host"] == custom_base_url
        assert call_args.kwargs["ai_model_id"] == custom_model

        # Verify instance attributes
        assert orchestrator.base_url == custom_base_url
        assert orchestrator.model == custom_model


class TestContentGenerationOrchestratorGenerateVariants:
    """Tests for ContentGenerationOrchestrator.generate_variants."""

    @pytest.mark.asyncio
    @patch("backend.core.generation.build_project_context")
    @patch("backend.core.generation.get_content_generation_system_prompt")
    @patch("backend.core.generation.Kernel")
    @patch("backend.core.generation.OllamaChatCompletion")
    async def test__generate_variants__success(
        self,
        mock_ollama_class: MagicMock,
        mock_kernel_class: MagicMock,
        mock_get_system_prompt: MagicMock,
        mock_build_context: MagicMock,
        sample_project_id: UUID,
    ):
        """Test successful content generation."""
        # Setup mocks
        mock_kernel = MagicMock()
        mock_kernel_class.return_value = mock_kernel

        mock_ollama_service = MagicMock()
        mock_ollama_class.return_value = mock_ollama_service

        # Mock function results
        short_form_result = MagicMock()
        short_form_result.value = "Check out our new product! #innovation"

        long_form_result = MagicMock()
        long_form_result.value = "We're excited to introduce our latest innovation..."

        cta_result = MagicMock()
        cta_result.value = "Click here to learn more!"

        # Track which function is being invoked
        invoke_calls = []

        async def mock_invoke(*args, **kwargs):
            function = kwargs.get("function")
            invoke_calls.append(function)
            if len(invoke_calls) == 1:
                return short_form_result
            elif len(invoke_calls) == 2:
                return long_form_result
            else:
                return cta_result

        mock_kernel.invoke = AsyncMock(side_effect=mock_invoke)

        # Mock add_function to return identifiable functions
        def mock_add_function(*args, **kwargs):
            func = MagicMock()
            func.name = kwargs.get("function_name", "unknown")
            return func

        mock_kernel.add_function = Mock(side_effect=mock_add_function)

        # Mock prompt template functions
        mock_build_context.return_value = "Project: Test Project"
        mock_get_system_prompt.return_value = "You are a helpful assistant."

        # Create orchestrator
        orchestrator = ContentGenerationOrchestrator()

        # Generate variants
        brief = "Launch our new product"
        result = await orchestrator.generate_variants(
            brief=brief,
            project_id=sample_project_id,
            project_name="Test Project",
            project_description="A test project",
            brand_tone="Professional and friendly",
            asset_summaries=[{"filename": "test.pdf", "content_type": "application/pdf"}],
        )

        # Verify results
        assert result["short_form"] == "Check out our new product! #innovation"
        assert result["long_form"] == "We're excited to introduce our latest innovation..."
        assert result["cta"] == "Click here to learn more!"
        assert result["metadata"]["model"] == "qwen3vl:4b"
        assert result["metadata"]["base_url"] == "http://localhost:11434"
        assert result["metadata"]["project_id"] == str(sample_project_id)

        # Verify context building was called
        mock_build_context.assert_called_once_with(
            project_name="Test Project",
            project_description="A test project",
            asset_summaries=[{"filename": "test.pdf", "content_type": "application/pdf"}],
        )

        # Verify system prompt was called
        mock_get_system_prompt.assert_called_once()

        # Verify kernel.invoke was called 3 times
        assert mock_kernel.invoke.call_count == 3

    @pytest.mark.asyncio
    @patch("backend.core.generation.build_project_context")
    @patch("backend.core.generation.get_content_generation_system_prompt")
    @patch("backend.core.generation.Kernel")
    @patch("backend.core.generation.OllamaChatCompletion")
    async def test__generate_variants__minimal_parameters(
        self,
        mock_ollama_class: MagicMock,
        mock_kernel_class: MagicMock,
        mock_get_system_prompt: MagicMock,
        mock_build_context: MagicMock,
    ):
        """Test generation with minimal parameters."""
        # Setup mocks
        mock_kernel = MagicMock()
        mock_kernel_class.return_value = mock_kernel

        mock_ollama_service = MagicMock()
        mock_ollama_class.return_value = mock_ollama_service

        # Mock function results
        short_form_result = MagicMock()
        short_form_result.value = "Short content"

        long_form_result = MagicMock()
        long_form_result.value = "Long content"

        cta_result = MagicMock()
        cta_result.value = "CTA content"

        invoke_count = 0

        async def mock_invoke(*args, **kwargs):
            nonlocal invoke_count
            invoke_count += 1
            if invoke_count == 1:
                return short_form_result
            elif invoke_count == 2:
                return long_form_result
            else:
                return cta_result

        mock_kernel.invoke = AsyncMock(side_effect=mock_invoke)

        def mock_add_function(*args, **kwargs):
            func = MagicMock()
            func.name = kwargs.get("function_name", "unknown")
            return func

        mock_kernel.add_function = Mock(side_effect=mock_add_function)

        mock_build_context.return_value = ""
        mock_get_system_prompt.return_value = "You are a helpful assistant."

        orchestrator = ContentGenerationOrchestrator()

        result = await orchestrator.generate_variants(brief="Test brief")

        # Verify results
        assert result["short_form"] == "Short content"
        assert result["long_form"] == "Long content"
        assert result["cta"] == "CTA content"
        assert result["metadata"]["project_id"] is None

        # Verify context building was called with None values
        mock_build_context.assert_called_once_with(
            project_name=None,
            project_description=None,
            asset_summaries=None,
        )

    @pytest.mark.asyncio
    @patch("backend.core.generation.Kernel")
    @patch("backend.core.generation.OllamaChatCompletion")
    async def test__generate_variants__kernel_error(
        self,
        mock_ollama_class: MagicMock,
        mock_kernel_class: MagicMock,
    ):
        """Test generation when kernel.invoke raises an error."""
        # Setup mocks
        mock_kernel = MagicMock()
        mock_kernel_class.return_value = mock_kernel

        mock_ollama_service = MagicMock()
        mock_ollama_class.return_value = mock_ollama_service

        # Mock kernel.invoke to raise an error
        mock_kernel.invoke = AsyncMock(side_effect=Exception("Kernel error"))

        def mock_add_function(*args, **kwargs):
            func = MagicMock()
            func.name = kwargs.get("function_name", "unknown")
            return func

        mock_kernel.add_function = Mock(side_effect=mock_add_function)

        orchestrator = ContentGenerationOrchestrator()

        # Generate variants should raise GenerationError
        with pytest.raises(GenerationError, match="Failed to generate content variants"):
            await orchestrator.generate_variants(brief="Test brief")

    @pytest.mark.asyncio
    @patch("backend.core.generation.build_project_context")
    @patch("backend.core.generation.get_content_generation_system_prompt")
    @patch("backend.core.generation.Kernel")
    @patch("backend.core.generation.OllamaChatCompletion")
    async def test__generate_variants__with_brand_tone_only(
        self,
        mock_ollama_class: MagicMock,
        mock_kernel_class: MagicMock,
        mock_get_system_prompt: MagicMock,
        mock_build_context: MagicMock,
    ):
        """Test generation with only brand_tone specified."""
        # Setup mocks
        mock_kernel = MagicMock()
        mock_kernel_class.return_value = mock_kernel

        mock_ollama_service = MagicMock()
        mock_ollama_class.return_value = mock_ollama_service

        # Mock function results
        short_form_result = MagicMock()
        short_form_result.value = "Branded short content"

        long_form_result = MagicMock()
        long_form_result.value = "Branded long content"

        cta_result = MagicMock()
        cta_result.value = "Branded CTA"

        invoke_count = 0

        async def mock_invoke(*args, **kwargs):
            nonlocal invoke_count
            invoke_count += 1
            if invoke_count == 1:
                return short_form_result
            elif invoke_count == 2:
                return long_form_result
            else:
                return cta_result

        mock_kernel.invoke = AsyncMock(side_effect=mock_invoke)

        def mock_add_function(*args, **kwargs):
            func = MagicMock()
            func.name = kwargs.get("function_name", "unknown")
            return func

        mock_kernel.add_function = Mock(side_effect=mock_add_function)

        mock_build_context.return_value = ""
        mock_get_system_prompt.return_value = "You are a helpful assistant."

        orchestrator = ContentGenerationOrchestrator()

        result = await orchestrator.generate_variants(
            brief="Test brief",
            brand_tone="Professional and friendly",
        )

        # Verify results
        assert result["short_form"] == "Branded short content"
        assert result["long_form"] == "Branded long content"
        assert result["cta"] == "Branded CTA"

        # Verify system prompt was called with brand_tone
        mock_get_system_prompt.assert_called_once_with(
            brand_tone="Professional and friendly",
            project_context=None,
        )


class TestGenerateContentVariants:
    """Tests for the generate_content_variants convenience function."""

    @pytest.mark.asyncio
    @patch("backend.core.generation.ContentGenerationOrchestrator")
    async def test__generate_content_variants__success(
        self,
        mock_orchestrator_class: MagicMock,
    ):
        """Test the convenience function."""
        # Setup mock orchestrator
        mock_orchestrator = MagicMock()
        mock_orchestrator_class.return_value = mock_orchestrator

        expected_result = {
            "short_form": "Short content",
            "long_form": "Long content",
            "cta": "CTA content",
            "metadata": {"model": "test-model"},
        }

        mock_orchestrator.generate_variants = AsyncMock(return_value=expected_result)

        # Call convenience function
        result = await generate_content_variants(
            brief="Test brief",
            project_id=uuid4(),
            brand_tone="Professional",
        )

        # Verify orchestrator was created
        mock_orchestrator_class.assert_called_once()

        # Verify generate_variants was called
        mock_orchestrator.generate_variants.assert_called_once()
        call_kwargs = mock_orchestrator.generate_variants.call_args.kwargs
        assert call_kwargs["brief"] == "Test brief"
        assert call_kwargs["brand_tone"] == "Professional"
        assert call_kwargs["project_name"] is None
        assert call_kwargs["project_description"] is None
        assert call_kwargs["asset_summaries"] is None

        # Verify result
        assert result == expected_result

    @pytest.mark.asyncio
    @patch("backend.core.generation.ContentGenerationOrchestrator")
    async def test__generate_content_variants__with_custom_config(
        self,
        mock_orchestrator_class: MagicMock,
    ):
        """Test convenience function with custom base_url and model."""
        # Setup mock orchestrator
        mock_orchestrator = MagicMock()
        mock_orchestrator_class.return_value = mock_orchestrator

        expected_result = {
            "short_form": "Short content",
            "long_form": "Long content",
            "cta": "CTA content",
            "metadata": {"model": "custom-model"},
        }

        mock_orchestrator.generate_variants = AsyncMock(return_value=expected_result)

        # Call convenience function with custom config
        result = await generate_content_variants(
            brief="Test brief",
            base_url="http://custom:11434",
            model="custom-model",
        )

        # Verify orchestrator was created with custom config
        call_args = mock_orchestrator_class.call_args
        assert call_args.kwargs["base_url"] == "http://custom:11434"
        assert call_args.kwargs["model"] == "custom-model"

        # Verify result
        assert result == expected_result

    @pytest.mark.asyncio
    @patch("backend.core.generation.ContentGenerationOrchestrator")
    async def test__generate_content_variants__propagates_error(
        self,
        mock_orchestrator_class: MagicMock,
    ):
        """Test that convenience function propagates GenerationError."""
        # Setup mock orchestrator
        mock_orchestrator = MagicMock()
        mock_orchestrator_class.return_value = mock_orchestrator

        mock_orchestrator.generate_variants = AsyncMock(side_effect=GenerationError("Test error"))

        # Call convenience function should raise error
        with pytest.raises(GenerationError, match="Test error"):
            await generate_content_variants(brief="Test brief")
