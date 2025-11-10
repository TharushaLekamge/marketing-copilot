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
from backend.core.semantic_search import SemanticSearchOrchestrator

logger = logging.getLogger(__name__)


@pytest.fixture
def mock_kernel():
    """Create a mock Semantic Kernel instance."""
    kernel = MagicMock()

    # Mock function results - value should be a list with ChatMessageContent objects
    short_form_content = MagicMock()
    short_form_content.content = "Short form content here"
    short_form_result = MagicMock()
    short_form_result.value = [short_form_content]

    long_form_content = MagicMock()
    long_form_content.content = "Long form content here"
    long_form_result = MagicMock()
    long_form_result.value = [long_form_content]

    cta_content = MagicMock()
    cta_content.content = "CTA content here"
    cta_result = MagicMock()
    cta_result.value = [cta_content]

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
def mock_openai_service():
    """Create a mock OpenAIChatCompletion service."""
    return MagicMock()


@pytest.fixture
def sample_project_id():
    """Create a sample project ID."""
    return uuid4()


class TestContentGenerationOrchestratorInit:
    """Tests for ContentGenerationOrchestrator initialization."""

    @patch("backend.core.generation.Kernel")
    @patch("backend.core.generation.OpenAIChatCompletion")
    @patch("backend.core.generation.settings")
    def test__init__uses_default_settings(
        self,
        mock_settings: MagicMock,
        mock_openai_class: MagicMock,
        mock_kernel_class: MagicMock,
    ):
        """Test initialization with default settings."""
        mock_kernel = MagicMock()
        mock_kernel_class.return_value = mock_kernel

        mock_openai_service = MagicMock()
        mock_openai_class.return_value = mock_openai_service

        # Mock settings
        mock_settings.openai_api_key = "test-api-key"
        mock_settings.openai_chat_model_id = "gpt-3.5-turbo-instruct"

        # Mock add_function to return mock functions
        def mock_add_function(*args, **kwargs):
            func = MagicMock()
            func.name = kwargs.get("function_name", "unknown")
            return func

        mock_kernel.add_function = Mock(side_effect=mock_add_function)

        orchestrator = ContentGenerationOrchestrator()

        # Verify Kernel was created
        mock_kernel_class.assert_called_once()

        # Verify OpenAIChatCompletion was created with default settings
        mock_openai_class.assert_called_once()
        call_args = mock_openai_class.call_args
        assert call_args.kwargs["api_key"] == "test-api-key"
        assert call_args.kwargs["ai_model_id"] == "gpt-3.5-turbo-instruct"

        # Verify service was added to kernel
        mock_kernel.add_service.assert_called_once_with(mock_openai_service)

        # Verify instance attributes
        assert orchestrator.kernel == mock_kernel
        assert orchestrator.api_key == "test-api-key"
        assert orchestrator.model == "gpt-3.5-turbo-instruct"
        assert orchestrator.short_form_func is not None
        assert orchestrator.long_form_func is not None
        assert orchestrator.cta_func is not None

    @patch("backend.core.generation.Kernel")
    @patch("backend.core.generation.OpenAIChatCompletion")
    def test__init__uses_custom_parameters(
        self,
        mock_openai_class: MagicMock,
        mock_kernel_class: MagicMock,
    ):
        """Test initialization with custom parameters."""
        mock_kernel = MagicMock()
        mock_kernel_class.return_value = mock_kernel

        mock_openai_service = MagicMock()
        mock_openai_class.return_value = mock_openai_service

        # Mock add_function
        def mock_add_function(*args, **kwargs):
            func = MagicMock()
            func.name = kwargs.get("function_name", "unknown")
            return func

        mock_kernel.add_function = Mock(side_effect=mock_add_function)

        custom_api_key = "custom-api-key"
        custom_model = "gpt-4"

        orchestrator = ContentGenerationOrchestrator(
            api_key=custom_api_key,
            model=custom_model,
        )

        # Verify OpenAIChatCompletion was created with custom settings
        call_args = mock_openai_class.call_args
        assert call_args.kwargs["api_key"] == custom_api_key
        assert call_args.kwargs["ai_model_id"] == custom_model

        # Verify instance attributes
        assert orchestrator.api_key == custom_api_key
        assert orchestrator.model == custom_model


class TestContentGenerationOrchestratorGenerateVariants:
    """Tests for ContentGenerationOrchestrator.generate_variants."""

    @pytest.mark.asyncio
    @patch("backend.core.generation.build_project_context")
    @patch("backend.core.generation.get_content_generation_system_prompt")
    @patch("backend.core.generation.Kernel")
    @patch("backend.core.generation.OpenAIChatCompletion")
    @patch("backend.core.generation.settings")
    async def test__generate_variants__success(
        self,
        mock_settings: MagicMock,
        mock_openai_class: MagicMock,
        mock_kernel_class: MagicMock,
        mock_get_system_prompt: MagicMock,
        mock_build_context: MagicMock,
        sample_project_id: UUID,
    ):
        """Test successful content generation."""
        # Setup mocks
        mock_kernel = MagicMock()
        mock_kernel_class.return_value = mock_kernel

        mock_openai_service = MagicMock()
        mock_openai_class.return_value = mock_openai_service

        # Mock settings
        mock_settings.openai_api_key = "test-api-key"
        mock_settings.openai_chat_model_id = "gpt-3.5-turbo-instruct"

        # Mock function results - value should be a list with ChatMessageContent objects
        short_form_content = MagicMock()
        short_form_content.content = "Check out our new product! #innovation"
        short_form_result = MagicMock()
        short_form_result.value = [short_form_content]

        long_form_content = MagicMock()
        long_form_content.content = "We're excited to introduce our latest innovation..."
        long_form_result = MagicMock()
        long_form_result.value = [long_form_content]

        cta_content = MagicMock()
        cta_content.content = "Click here to learn more!"
        cta_result = MagicMock()
        cta_result.value = [cta_content]

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
        assert result["metadata"]["model"] == "gpt-3.5-turbo-instruct"
        assert result["metadata"]["provider"] == "openai"
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
    @patch("backend.core.generation.OpenAIChatCompletion")
    @patch("backend.core.generation.settings")
    async def test__generate_variants__minimal_parameters(
        self,
        mock_settings: MagicMock,
        mock_openai_class: MagicMock,
        mock_kernel_class: MagicMock,
        mock_get_system_prompt: MagicMock,
        mock_build_context: MagicMock,
    ):
        """Test generation with minimal parameters."""
        # Setup mocks
        mock_kernel = MagicMock()
        mock_kernel_class.return_value = mock_kernel

        mock_openai_service = MagicMock()
        mock_openai_class.return_value = mock_openai_service

        # Mock settings
        mock_settings.openai_api_key = "test-api-key"
        mock_settings.openai_chat_model_id = "gpt-3.5-turbo-instruct"

        # Mock function results - value should be a list with ChatMessageContent objects
        short_form_content = MagicMock()
        short_form_content.content = "Short content"
        short_form_result = MagicMock()
        short_form_result.value = [short_form_content]

        long_form_content = MagicMock()
        long_form_content.content = "Long content"
        long_form_result = MagicMock()
        long_form_result.value = [long_form_content]

        cta_content = MagicMock()
        cta_content.content = "CTA content"
        cta_result = MagicMock()
        cta_result.value = [cta_content]

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
    @patch("backend.core.generation.OpenAIChatCompletion")
    @patch("backend.core.generation.settings")
    async def test__generate_variants__kernel_error(
        self,
        mock_settings: MagicMock,
        mock_openai_class: MagicMock,
        mock_kernel_class: MagicMock,
    ):
        """Test generation when kernel.invoke raises an error."""
        # Setup mocks
        mock_kernel = MagicMock()
        mock_kernel_class.return_value = mock_kernel

        mock_openai_service = MagicMock()
        mock_openai_class.return_value = mock_openai_service

        # Mock settings
        mock_settings.openai_api_key = "test-api-key"
        mock_settings.openai_chat_model_id = "gpt-3.5-turbo-instruct"

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
    @patch("backend.core.generation.OpenAIChatCompletion")
    @patch("backend.core.generation.settings")
    async def test__generate_variants__with_brand_tone_only(
        self,
        mock_settings: MagicMock,
        mock_openai_class: MagicMock,
        mock_kernel_class: MagicMock,
        mock_get_system_prompt: MagicMock,
        mock_build_context: MagicMock,
    ):
        """Test generation with only brand_tone specified."""
        # Setup mocks
        mock_kernel = MagicMock()
        mock_kernel_class.return_value = mock_kernel

        mock_openai_service = MagicMock()
        mock_openai_class.return_value = mock_openai_service

        # Mock settings
        mock_settings.openai_api_key = "test-api-key"
        mock_settings.openai_chat_model_id = "gpt-3.5-turbo-instruct"

        # Mock function results - value should be a list with ChatMessageContent objects
        short_form_content = MagicMock()
        short_form_content.content = "Branded short content"
        short_form_result = MagicMock()
        short_form_result.value = [short_form_content]

        long_form_content = MagicMock()
        long_form_content.content = "Branded long content"
        long_form_result = MagicMock()
        long_form_result.value = [long_form_content]

        cta_content = MagicMock()
        cta_content.content = "Branded CTA"
        cta_result = MagicMock()
        cta_result.value = [cta_content]

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

    @pytest.mark.asyncio
    @patch("backend.core.generation.build_rag_context")
    @patch("backend.core.generation.SemanticSearchOrchestrator")
    @patch("backend.core.generation.build_project_context")
    @patch("backend.core.generation.get_content_generation_system_prompt")
    @patch("backend.core.generation.Kernel")
    @patch("backend.core.generation.OpenAIChatCompletion")
    @patch("backend.core.generation.settings")
    async def test__generate_variants__with_rag_enabled(
        self,
        mock_settings: MagicMock,
        mock_openai_class: MagicMock,
        mock_kernel_class: MagicMock,
        mock_get_system_prompt: MagicMock,
        mock_build_context: MagicMock,
        mock_semantic_search_class: MagicMock,
        mock_build_rag_context: MagicMock,
        sample_project_id: UUID,
    ):
        """Test generation with RAG enabled."""
        # Setup mocks
        mock_kernel = MagicMock()
        mock_kernel_class.return_value = mock_kernel

        mock_openai_service = MagicMock()
        mock_openai_class.return_value = mock_openai_service

        # Mock settings
        mock_settings.openai_api_key = "test-api-key"
        mock_settings.openai_chat_model_id = "gpt-3.5-turbo-instruct"

        # Mock function results
        short_form_content = MagicMock()
        short_form_content.content = "Short form with RAG context"
        short_form_result = MagicMock()
        short_form_result.value = [short_form_content]

        long_form_content = MagicMock()
        long_form_content.content = "Long form with RAG context"
        long_form_result = MagicMock()
        long_form_result.value = [long_form_content]

        cta_content = MagicMock()
        cta_content.content = "CTA with RAG context"
        cta_result = MagicMock()
        cta_result.value = [cta_content]

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

        # Mock semantic search
        mock_semantic_search = MagicMock(spec=SemanticSearchOrchestrator)
        mock_semantic_search_class.return_value = mock_semantic_search

        search_results = [
            {
                "text": "This is relevant content from project documents.",
                "score": 0.85,
                "asset_id": str(uuid4()),
                "project_id": str(sample_project_id),
                "chunk_index": 0,
                "metadata": {"source": "test.pdf"},
            }
        ]
        mock_semantic_search.search_with_context = AsyncMock(return_value=search_results)

        # Mock RAG context building
        mock_build_rag_context.return_value = "[1] Source: test.pdf Asset ID: ...\nThis is relevant content from project documents."

        # Mock project context
        mock_build_context.return_value = "Project: Test Project"

        # Mock system prompt
        mock_get_system_prompt.return_value = "You are a helpful assistant."

        orchestrator = ContentGenerationOrchestrator()

        brief = "Launch our new product"
        objective = "Increase brand awareness"
        result = await orchestrator.generate_variants(
            brief=brief,
            project_id=sample_project_id,
            project_name="Test Project",
            objective=objective,
            use_rag=True,
            rag_top_k=5,
        )

        # Verify results
        assert result["short_form"] == "Short form with RAG context"
        assert result["long_form"] == "Long form with RAG context"
        assert result["cta"] == "CTA with RAG context"
        assert result["metadata"]["chunks_retrieved"] == 1
        assert result["metadata"]["rag_enabled"] is True

        # Verify semantic search was called with combined brief + objective
        expected_query = f"{brief} {objective}"
        mock_semantic_search.search_with_context.assert_called_once_with(
            query=expected_query,
            project_id=sample_project_id,
            top_k=5,
            include_metadata=True,
        )

        # Verify RAG context was built
        mock_build_rag_context.assert_called_once_with(search_results)

        # Verify system prompt includes merged context
        mock_get_system_prompt.assert_called_once()
        call_args = mock_get_system_prompt.call_args
        assert call_args.kwargs["project_context"] is not None
        assert "Relevant Content from Project Documents" in call_args.kwargs["project_context"]

        # Verify kernel.invoke was called with enhanced brief (brief + objective)
        assert mock_kernel.invoke.call_count == 3
        invoke_calls = mock_kernel.invoke.call_args_list
        for call in invoke_calls:
            call_kwargs = call.kwargs
            assert "arguments" in call_kwargs
            args = call_kwargs["arguments"]
            # Verify enhanced brief includes objective
            assert objective in args["brief"]
            assert brief in args["brief"]

    @pytest.mark.asyncio
    @patch("backend.core.generation.build_project_context")
    @patch("backend.core.generation.get_content_generation_system_prompt")
    @patch("backend.core.generation.Kernel")
    @patch("backend.core.generation.OpenAIChatCompletion")
    @patch("backend.core.generation.settings")
    async def test__generate_variants__with_rag_disabled(
        self,
        mock_settings: MagicMock,
        mock_openai_class: MagicMock,
        mock_kernel_class: MagicMock,
        mock_get_system_prompt: MagicMock,
        mock_build_context: MagicMock,
        sample_project_id: UUID,
    ):
        """Test generation with RAG disabled."""
        # Setup mocks
        mock_kernel = MagicMock()
        mock_kernel_class.return_value = mock_kernel

        mock_openai_service = MagicMock()
        mock_openai_class.return_value = mock_openai_service

        # Mock settings
        mock_settings.openai_api_key = "test-api-key"
        mock_settings.openai_chat_model_id = "gpt-3.5-turbo-instruct"

        # Mock function results
        short_form_content = MagicMock()
        short_form_content.content = "Short form without RAG"
        short_form_result = MagicMock()
        short_form_result.value = [short_form_content]

        long_form_content = MagicMock()
        long_form_content.content = "Long form without RAG"
        long_form_result = MagicMock()
        long_form_result.value = [long_form_content]

        cta_content = MagicMock()
        cta_content.content = "CTA without RAG"
        cta_result = MagicMock()
        cta_result.value = [cta_content]

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

        # Mock project context
        mock_build_context.return_value = "Project: Test Project"
        mock_get_system_prompt.return_value = "You are a helpful assistant."

        orchestrator = ContentGenerationOrchestrator()

        result = await orchestrator.generate_variants(
            brief="Test brief",
            project_id=sample_project_id,
            use_rag=False,
        )

        # Verify results
        assert result["short_form"] == "Short form without RAG"
        assert result["long_form"] == "Long form without RAG"
        assert result["cta"] == "CTA without RAG"
        assert result["metadata"]["chunks_retrieved"] is None
        assert result["metadata"]["rag_enabled"] is False

    @pytest.mark.asyncio
    @patch("backend.core.generation.build_rag_context")
    @patch("backend.core.generation.SemanticSearchOrchestrator")
    @patch("backend.core.generation.build_project_context")
    @patch("backend.core.generation.get_content_generation_system_prompt")
    @patch("backend.core.generation.Kernel")
    @patch("backend.core.generation.OpenAIChatCompletion")
    @patch("backend.core.generation.settings")
    async def test__generate_variants__rag_retrieval_failure_continues(
        self,
        mock_settings: MagicMock,
        mock_openai_class: MagicMock,
        mock_kernel_class: MagicMock,
        mock_get_system_prompt: MagicMock,
        mock_build_context: MagicMock,
        mock_semantic_search_class: MagicMock,
        mock_build_rag_context: MagicMock,
        sample_project_id: UUID,
    ):
        """Test that generation continues if RAG retrieval fails."""
        # Setup mocks
        mock_kernel = MagicMock()
        mock_kernel_class.return_value = mock_kernel

        mock_openai_service = MagicMock()
        mock_openai_class.return_value = mock_openai_service

        # Mock settings
        mock_settings.openai_api_key = "test-api-key"
        mock_settings.openai_chat_model_id = "gpt-3.5-turbo-instruct"

        # Mock function results
        short_form_content = MagicMock()
        short_form_content.content = "Short form"
        short_form_result = MagicMock()
        short_form_result.value = [short_form_content]

        long_form_content = MagicMock()
        long_form_content.content = "Long form"
        long_form_result = MagicMock()
        long_form_result.value = [long_form_content]

        cta_content = MagicMock()
        cta_content.content = "CTA"
        cta_result = MagicMock()
        cta_result.value = [cta_content]

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

        # Mock semantic search to raise exception
        mock_semantic_search = MagicMock(spec=SemanticSearchOrchestrator)
        mock_semantic_search_class.return_value = mock_semantic_search
        mock_semantic_search.search_with_context = AsyncMock(side_effect=Exception("Search failed"))

        # Mock project context
        mock_build_context.return_value = "Project: Test Project"
        mock_get_system_prompt.return_value = "You are a helpful assistant."

        orchestrator = ContentGenerationOrchestrator()

        result = await orchestrator.generate_variants(
            brief="Test brief",
            project_id=sample_project_id,
            use_rag=True,
        )

        # Verify results - generation should succeed despite RAG failure
        assert result["short_form"] == "Short form"
        assert result["long_form"] == "Long form"
        assert result["cta"] == "CTA"
        assert result["metadata"]["chunks_retrieved"] == 0
        assert result["metadata"]["rag_enabled"] is True

        # Verify semantic search was called
        mock_semantic_search.search_with_context.assert_called_once()

        # Verify RAG context was NOT built (because search failed)
        mock_build_rag_context.assert_not_called()


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
        """Test convenience function with custom api_key and model."""
        # Setup mock orchestrator
        mock_orchestrator = MagicMock()
        mock_orchestrator_class.return_value = mock_orchestrator

        expected_result = {
            "short_form": "Short content",
            "long_form": "Long content",
            "cta": "CTA content",
            "metadata": {"model": "gpt-4"},
        }

        mock_orchestrator.generate_variants = AsyncMock(return_value=expected_result)

        # Call convenience function with custom config
        result = await generate_content_variants(
            brief="Test brief",
            api_key="custom-api-key",
            model="gpt-4",
        )

        # Verify orchestrator was created with custom config
        call_args = mock_orchestrator_class.call_args
        assert call_args.kwargs["api_key"] == "custom-api-key"
        assert call_args.kwargs["model"] == "gpt-4"

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
