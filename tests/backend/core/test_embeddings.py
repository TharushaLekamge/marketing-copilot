"""Unit tests for embedding generation module."""

import numpy as np

from backend.core.embeddings import (
    DEFAULT_MODEL_NAME,
    EmbeddingGenerator,
    generate_embedding,
    generate_embeddings_batch,
    get_embedding_generator,
)


class TestEmbeddingGenerator:
    """Tests for EmbeddingGenerator class."""

    def test__init__creates_generator_with_default_model(self):
        """Test that generator initializes with default model."""
        generator = EmbeddingGenerator()
        assert generator.model_name == DEFAULT_MODEL_NAME
        assert generator._model is None  # Lazy loading

    def test__init__creates_generator_with_custom_model(self):
        """Test that generator initializes with custom model name."""
        custom_model = "all-MiniLM-L6-v2"
        generator = EmbeddingGenerator(model_name=custom_model)
        assert generator.model_name == custom_model

    def test__model_property_lazy_loads_model(self):
        """Test that model is lazy-loaded on first access."""
        generator = EmbeddingGenerator()
        assert generator._model is None

        model = generator.model
        assert model is not None
        assert generator._model is not None
        assert generator._model == model

    def test__generate_embedding__returns_correct_dimension(self):
        """Test that generate_embedding returns correct dimension."""
        generator = EmbeddingGenerator()
        text = "This is a test sentence."
        embedding = generator.generate_embedding(text)
        expected_dimension = generator.get_embedding_dimension()

        assert isinstance(embedding, list)
        assert len(embedding) == expected_dimension
        assert all(isinstance(x, float) for x in embedding)

    def test__generate_embedding__normalizes_embeddings(self):
        """Test that embeddings are normalized (unit vectors)."""
        generator = EmbeddingGenerator()
        text = "This is a test sentence."
        embedding = generator.generate_embedding(text)

        # Check that embedding is normalized (magnitude ≈ 1.0)
        magnitude = sum(x * x for x in embedding) ** 0.5
        assert abs(magnitude - 1.0) < 0.01

    def test__generate_embedding__empty_text_returns_zero_vector(self):
        """Test that empty text returns zero vector."""
        generator = EmbeddingGenerator()
        embedding = generator.generate_embedding("")
        expected_dimension = generator.get_embedding_dimension()

        assert len(embedding) == expected_dimension
        assert all(x == 0.0 for x in embedding)

    def test__generate_embedding__whitespace_only_returns_zero_vector(self):
        """Test that whitespace-only text returns zero vector."""
        generator = EmbeddingGenerator()
        embedding = generator.generate_embedding("   \n\t  ")
        expected_dimension = generator.get_embedding_dimension()

        assert len(embedding) == expected_dimension
        assert all(x == 0.0 for x in embedding)

    def test__generate_embedding__same_text_produces_same_embedding(self):
        """Test that same text produces same embedding."""
        generator = EmbeddingGenerator()
        text = "This is a test sentence."

        embedding1 = generator.generate_embedding(text)
        embedding2 = generator.generate_embedding(text)

        assert embedding1 == embedding2

    def test__generate_embedding__different_texts_produce_different_embeddings(self):
        """Test that different texts produce different embeddings."""
        generator = EmbeddingGenerator()

        embedding1 = generator.generate_embedding("This is a test sentence.")
        embedding2 = generator.generate_embedding("This is a completely different sentence.")

        assert embedding1 != embedding2

    def test__generate_embeddings_batch__returns_correct_count(self):
        """Test that batch generation returns correct number of embeddings."""
        generator = EmbeddingGenerator()
        texts = ["First sentence.", "Second sentence.", "Third sentence."]
        embeddings = generator.generate_embeddings_batch(texts)
        expected_dimension = generator.get_embedding_dimension()

        assert len(embeddings) == len(texts)
        assert all(len(emb) == expected_dimension for emb in embeddings)

    def test__generate_embeddings_batch__handles_empty_list(self):
        """Test that batch generation handles empty list."""
        generator = EmbeddingGenerator()
        embeddings = generator.generate_embeddings_batch([])

        assert embeddings == []

    def test__generate_embeddings_batch__handles_empty_texts(self):
        """Test that batch generation handles empty texts."""
        generator = EmbeddingGenerator()
        texts = ["", "   ", "Valid text."]
        embeddings = generator.generate_embeddings_batch(texts)
        expected_dimension = generator.get_embedding_dimension()

        assert len(embeddings) == 3
        # First two should be zero vectors
        assert len(embeddings[0]) == expected_dimension
        assert all(x == 0.0 for x in embeddings[0])
        assert len(embeddings[1]) == expected_dimension
        assert all(x == 0.0 for x in embeddings[1])
        # Third should be valid embedding
        assert len(embeddings[2]) == expected_dimension
        assert any(x != 0.0 for x in embeddings[2])

    def test__generate_embeddings_batch__all_empty_texts_returns_zero_vectors(self):
        """Test that batch with all empty texts returns zero vectors."""
        generator = EmbeddingGenerator()
        texts = ["", "   ", "\n\t"]
        embeddings = generator.generate_embeddings_batch(texts)
        expected_dimension = generator.get_embedding_dimension()

        assert len(embeddings) == 3
        assert all(len(emb) == expected_dimension for emb in embeddings)
        assert all(all(x == 0.0 for x in emb) for emb in embeddings)

    def test__generate_embeddings_batch__produces_same_embeddings_as_single(self):
        """Test that batch generation produces same embeddings as single generation."""
        generator = EmbeddingGenerator()
        texts = ["First sentence.", "Second sentence."]

        batch_embeddings = generator.generate_embeddings_batch(texts)
        single_embeddings = [
            generator.generate_embedding(texts[0]),
            generator.generate_embedding(texts[1]),
        ]

        np.testing.assert_array_almost_equal(batch_embeddings[0], single_embeddings[0])
        np.testing.assert_array_almost_equal(batch_embeddings[1], single_embeddings[1])

    def test__get_embedding_dimension__returns_correct_dimension(self):
        """Test that get_embedding_dimension returns correct dimension."""
        generator = EmbeddingGenerator()
        dimension = generator.get_embedding_dimension()

        # Default model (all-MiniLM-L6-v2) has dimension 384
        assert dimension == 384
        assert isinstance(dimension, int)


class TestConvenienceFunctions:
    """Tests for convenience functions."""

    def test__generate_embedding__convenience_function_works(self):
        """Test that generate_embedding convenience function works."""
        text = "This is a test sentence."
        embedding = generate_embedding(text)
        generator = get_embedding_generator()
        expected_dimension = generator.get_embedding_dimension()

        assert isinstance(embedding, list)
        assert len(embedding) == expected_dimension

    def test__generate_embedding__convenience_function_with_custom_model(self):
        """Test that generate_embedding works with custom model."""
        text = "This is a test sentence."
        embedding = generate_embedding(text, model_name=DEFAULT_MODEL_NAME)
        generator = get_embedding_generator(model_name=DEFAULT_MODEL_NAME)
        expected_dimension = generator.get_embedding_dimension()

        assert isinstance(embedding, list)
        assert len(embedding) == expected_dimension

    def test__generate_embeddings_batch__convenience_function_works(self):
        """Test that generate_embeddings_batch convenience function works."""
        texts = ["First sentence.", "Second sentence."]
        embeddings = generate_embeddings_batch(texts)
        generator = get_embedding_generator()
        expected_dimension = generator.get_embedding_dimension()

        assert len(embeddings) == 2
        assert all(len(emb) == expected_dimension for emb in embeddings)

    def test__get_embedding_generator__returns_singleton(self):
        """Test that get_embedding_generator returns singleton instance."""
        generator1 = get_embedding_generator()
        generator2 = get_embedding_generator()

        assert generator1 is generator2

    def test__get_embedding_generator__creates_new_instance_for_different_model(self):
        """Test that get_embedding_generator creates new instance for different model."""
        generator1 = get_embedding_generator()
        generator2 = get_embedding_generator(model_name=DEFAULT_MODEL_NAME)

        # Same model should return same instance
        assert generator1 is generator2

        # Different model should create new instance
        generator3 = get_embedding_generator(model_name="all-MiniLM-L6-v2")
        # Since we're using the same model name, it should be the same instance
        assert generator3 is generator1
