"""Embedding generation utilities for document processing."""

from typing import List

from sentence_transformers import SentenceTransformer


# Default embedding model (lightweight, general-purpose)
DEFAULT_MODEL_NAME = "all-MiniLM-L6-v2"


class EmbeddingGenerator:
    """Generates embeddings for text using sentence-transformers."""

    def __init__(self, model_name: str = DEFAULT_MODEL_NAME) -> None:
        """Initialize the embedding generator.

        Args:
            model_name: Name of the sentence-transformers model to use
        """
        self.model_name = model_name
        self._model: SentenceTransformer | None = None

    @property
    def model(self) -> SentenceTransformer:
        """Lazy-load the model to defer heavy imports."""
        if self._model is None:
            self._model = SentenceTransformer(self.model_name)
        return self._model

    def generate_embedding(self, text: str) -> List[float]:
        """Generate an embedding vector for a single text.

        Args:
            text: Text to generate embedding for

        Returns:
            List[float]: Embedding vector (dimension depends on model)
        """
        if not text.strip():
            # Return zero vector for empty text
            dimension = self.get_embedding_dimension()
            return [0.0] * dimension

        embedding = self.model.encode(text, normalize_embeddings=True)
        return embedding.tolist()

    def generate_embeddings_batch(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for multiple texts efficiently.

        Args:
            texts: List of texts to generate embeddings for

        Returns:
            List[List[float]]: List of embedding vectors
        """
        if not texts:
            return []

        # Filter out empty texts and track indices
        non_empty_texts = []
        indices = []
        for i, text in enumerate(texts):
            if text.strip():
                non_empty_texts.append(text)
                indices.append(i)

        if not non_empty_texts:
            # Return zero vectors for all empty texts
            dimension = self.get_embedding_dimension()
            return [[0.0] * dimension] * len(texts)

        # Generate embeddings for non-empty texts
        embeddings = self.model.encode(
            non_empty_texts, normalize_embeddings=True, show_progress_bar=False
        )

        # Create result list with zero vectors for empty texts
        result: List[List[float]] = []
        embedding_idx = 0
        for i in range(len(texts)):
            if i in indices:
                result.append(embeddings[embedding_idx].tolist())
                embedding_idx += 1
            else:
                dimension = self.get_embedding_dimension()
                result.append([0.0] * dimension)

        return result

    def get_embedding_dimension(self) -> int:
        """Get the dimension of embeddings produced by this model.

        Returns:
            int: Embedding dimension
        """
        return self.model.get_sentence_embedding_dimension()


# Global instance for convenience (lazy-loaded)
_default_generator: EmbeddingGenerator | None = None


def get_embedding_generator(model_name: str | None = None) -> EmbeddingGenerator:
    """Get or create the default embedding generator.

    Args:
        model_name: Optional model name to use (defaults to DEFAULT_MODEL_NAME)

    Returns:
        EmbeddingGenerator: The embedding generator instance
    """
    global _default_generator
    if _default_generator is None or (
        model_name is not None and _default_generator.model_name != model_name
    ):
        _default_generator = EmbeddingGenerator(model_name or DEFAULT_MODEL_NAME)
    return _default_generator


def generate_embedding(text: str, model_name: str | None = None) -> List[float]:
    """Generate an embedding for a single text (convenience function).

    Args:
        text: Text to generate embedding for
        model_name: Optional model name to use

    Returns:
        List[float]: Embedding vector
    """
    generator = get_embedding_generator(model_name)
    return generator.generate_embedding(text)


def generate_embeddings_batch(
    texts: List[str], model_name: str | None = None
) -> List[List[float]]:
    """Generate embeddings for multiple texts (convenience function).

    Args:
        texts: List of texts to generate embeddings for
        model_name: Optional model name to use

    Returns:
        List[List[float]]: List of embedding vectors
    """
    generator = get_embedding_generator(model_name)
    return generator.generate_embeddings_batch(texts)

