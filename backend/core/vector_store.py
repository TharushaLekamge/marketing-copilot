"""Vector store abstraction for storing and retrieving document embeddings."""

import json
import sqlite3
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional
from uuid import UUID

import faiss
import numpy as np


@dataclass
class VectorDocument:
    """Represents a document chunk with its embedding and metadata."""

    id: str  # Unique identifier for this vector (e.g., "{asset_id}_{chunk_index}")
    asset_id: UUID
    project_id: UUID
    chunk_index: int
    text: str
    embedding: List[float]
    metadata: Optional[dict] = None


@dataclass
class SearchResult:
    """Represents a search result with similarity score."""

    document: VectorDocument
    score: float  # Similarity score (higher is more similar)


class VectorStoreError(Exception):
    """Base exception for vector store operations."""

    pass


class VectorStore(ABC):
    """Abstract interface for vector storage and retrieval."""

    @abstractmethod
    def add_documents(self, documents: List[VectorDocument]) -> None:
        """Add documents to the vector store.

        Args:
            documents: List of documents with embeddings to add

        Raises:
            VectorStoreError: If documents cannot be added
        """
        raise NotImplementedError

    @abstractmethod
    def search(
        self,
        query_embedding: List[float],
        top_k: int = 10,
        project_id: Optional[UUID] = None,
        asset_id: Optional[UUID] = None,
    ) -> List[SearchResult]:
        """Search for similar documents.

        Args:
            query_embedding: Query embedding vector
            top_k: Number of results to return
            project_id: Optional filter by project ID
            asset_id: Optional filter by asset ID

        Returns:
            List of search results sorted by similarity (highest first)

        Raises:
            VectorStoreError: If search fails
        """
        raise NotImplementedError

    @abstractmethod
    def delete_by_asset(self, asset_id: UUID) -> None:
        """Delete all vectors for a specific asset.

        Args:
            asset_id: ID of the asset to delete vectors for

        Raises:
            VectorStoreError: If deletion fails
        """
        raise NotImplementedError

    @abstractmethod
    def delete_by_project(self, project_id: UUID) -> None:
        """Delete all vectors for a specific project.

        Args:
            project_id: ID of the project to delete vectors for

        Raises:
            VectorStoreError: If deletion fails
        """
        raise NotImplementedError

    @abstractmethod
    def get_document_count(self, project_id: Optional[UUID] = None) -> int:
        """Get the total number of documents in the store.

        Args:
            project_id: Optional filter by project ID

        Returns:
            Number of documents
        """
        raise NotImplementedError

    @abstractmethod
    def clear(self) -> None:
        """Clear all documents from the vector store.

        Raises:
            VectorStoreError: If clearing fails
        """
        raise NotImplementedError


class FAISSSQLiteVectorStore(VectorStore):
    """FAISS + SQLite implementation of vector store.

    Uses FAISS for efficient similarity search and SQLite for metadata storage.
    """

    def __init__(
        self,
        db_path: str | Path,
        dimension: int = 384,  # Default for all-MiniLM-L6-v2
        index_type: str = "flat",  # "flat" for exact search, "ivf" for approximate
    ):
        """Initialize FAISS + SQLite vector store.

        Args:
            db_path: Path to SQLite database file
            dimension: Dimension of embedding vectors
            index_type: Type of FAISS index ("flat" or "ivf")
        """
        self.db_path = Path(db_path)
        self.dimension = dimension
        self.index_type = index_type

        # Ensure parent directory exists
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        # Initialize SQLite database
        self._init_database()

        # Initialize FAISS index
        self._init_faiss_index()

    def _init_database(self) -> None:
        """Initialize SQLite database schema."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Create vectors table
        # Store embedding as BLOB (numpy array serialized)
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS vectors (
                id TEXT PRIMARY KEY,
                asset_id TEXT NOT NULL,
                project_id TEXT NOT NULL,
                chunk_index INTEGER NOT NULL,
                text TEXT NOT NULL,
                embedding BLOB NOT NULL,
                metadata TEXT,
                faiss_index INTEGER NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

        # Create indexes for faster lookups
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_asset_id ON vectors(asset_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_project_id ON vectors(project_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_faiss_index ON vectors(faiss_index)")

        conn.commit()
        conn.close()

    def _init_faiss_index(self) -> None:
        """Initialize FAISS index."""
        if self.index_type == "flat":
            # Flat index for exact search (L2 distance)
            self.index = faiss.IndexFlatL2(self.dimension)
        elif self.index_type == "ivf":
            # IVF index for approximate search (faster for large datasets)
            quantizer = faiss.IndexFlatL2(self.dimension)
            # Use 100 clusters (adjust based on dataset size)
            nlist = 100
            self.index = faiss.IndexIVFFlat(quantizer, self.dimension, nlist)
            self.index.nprobe = 10  # Number of clusters to search
        else:
            raise ValueError(f"Unknown index type: {self.index_type}")

        # Load existing vectors from database
        self._load_vectors_from_db()

    def _load_vectors_from_db(self) -> None:
        """Load existing vectors from SQLite into FAISS index."""
        # Try to load saved FAISS index first
        if self._load_faiss_index():
            return

        # If no saved index, rebuild from database
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT embedding, faiss_index
            FROM vectors
            ORDER BY faiss_index
            """
        )
        rows = cursor.fetchall()

        if not rows:
            conn.close()
            return

        # Reconstruct FAISS index from stored embeddings
        vectors = []
        for embedding_blob, _ in rows:
            # Deserialize numpy array from BLOB
            embedding = np.frombuffer(embedding_blob, dtype=np.float32)
            vectors.append(embedding)

        if vectors:
            vectors_array = np.array(vectors, dtype=np.float32)

            # Reinitialize FAISS index
            if self.index_type == "flat":
                self.index = faiss.IndexFlatL2(self.dimension)
            elif self.index_type == "ivf":
                quantizer = faiss.IndexFlatL2(self.dimension)
                nlist = 100
                self.index = faiss.IndexIVFFlat(quantizer, self.dimension, nlist)
                self.index.nprobe = 10

            # Train IVF index if needed
            if self.index_type == "ivf" and not self.index.is_trained:
                self.index.train(vectors_array)

            # Add vectors to index
            self.index.add(vectors_array)

            # Save index to disk
            self._save_faiss_index()

        conn.close()

    def _save_faiss_index(self) -> None:
        """Save FAISS index to disk."""
        index_path = self.db_path.parent / f"{self.db_path.stem}.faiss"
        faiss.write_index(self.index, str(index_path))

    def _load_faiss_index(self) -> bool:
        """Load FAISS index from disk if it exists.

        Returns:
            True if index was loaded, False otherwise
        """
        index_path = self.db_path.parent / f"{self.db_path.stem}.faiss"
        if index_path.exists():
            self.index = faiss.read_index(str(index_path))
            return True
        return False

    def add_documents(self, documents: List[VectorDocument]) -> None:
        """Add documents to the vector store.

        Args:
            documents: List of documents with embeddings to add

        Raises:
            VectorStoreError: If documents cannot be added
        """
        if not documents:
            return

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            # Prepare vectors for FAISS (numpy array)
            vectors = np.array([doc.embedding for doc in documents], dtype=np.float32)

            # Validate dimension
            if vectors.shape[1] != self.dimension:
                raise VectorStoreError(
                    f"Embedding dimension mismatch: expected {self.dimension}, " f"got {vectors.shape[1]}"
                )

            # Get current FAISS index size (this will be the starting index for new vectors)
            start_idx = self.index.ntotal

            # Add vectors to FAISS index
            if self.index_type == "ivf" and not self.index.is_trained:
                # Train IVF index if not trained
                self.index.train(vectors)
            self.index.add(vectors)

            # Insert metadata and embeddings into SQLite
            for i, doc in enumerate(documents):
                faiss_index = start_idx + i
                metadata_json = json.dumps(doc.metadata) if doc.metadata else None

                # Serialize embedding as numpy array BLOB
                embedding_blob = np.array(doc.embedding, dtype=np.float32).tobytes()

                cursor.execute(
                    """
                    INSERT OR REPLACE INTO vectors
                    (id, asset_id, project_id, chunk_index, text, embedding, metadata, faiss_index)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        doc.id,
                        str(doc.asset_id),
                        str(doc.project_id),
                        doc.chunk_index,
                        doc.text,
                        embedding_blob,
                        metadata_json,
                        faiss_index,
                    ),
                )

            conn.commit()

            # Save FAISS index to disk
            self._save_faiss_index()

        except Exception as e:
            conn.rollback()
            raise VectorStoreError(f"Failed to add documents: {e}") from e
        finally:
            conn.close()

    def search(
        self,
        query_embedding: List[float],
        top_k: int = 10,
        project_id: Optional[UUID] = None,
        asset_id: Optional[UUID] = None,
    ) -> List[SearchResult]:
        """Search for similar documents.

        Args:
            query_embedding: Query embedding vector
            top_k: Number of results to return
            project_id: Optional filter by project ID
            asset_id: Optional filter by asset ID

        Returns:
            List of search results sorted by similarity (highest first)

        Raises:
            VectorStoreError: If search fails
        """
        if self.index.ntotal == 0:
            return []

        # Convert query to numpy array
        query_vector = np.array([query_embedding], dtype=np.float32)

        # Validate dimension
        if query_vector.shape[1] != self.dimension:
            raise VectorStoreError(
                f"Query embedding dimension mismatch: expected {self.dimension}, " f"got {query_vector.shape[1]}"
            )

        # Search in FAISS
        k = min(top_k * 3, self.index.ntotal)  # Get more results for filtering
        distances, indices = self.index.search(query_vector, k)

        # Get metadata from SQLite
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            if len(indices[0]) == 0:
                return []

            # Build query with optional filters
            query = """
                SELECT id, asset_id, project_id, chunk_index, text, metadata, faiss_index
                FROM vectors
                WHERE faiss_index IN ({})
            """.format(",".join("?" * len(indices[0])))

            params = list(indices[0])

            # Add filters
            if project_id:
                query += " AND project_id = ?"
                params.append(str(project_id))
            if asset_id:
                query += " AND asset_id = ?"
                params.append(str(asset_id))

            cursor.execute(query, params)
            rows = cursor.fetchall()

            # Create a mapping from faiss_index to document data
            doc_map = {}
            for row in rows:
                vector_id, asset_id_str, project_id_str, chunk_index, text, metadata_json, faiss_idx = row
                metadata = json.loads(metadata_json) if metadata_json else None
                doc_map[faiss_idx] = {
                    "id": vector_id,
                    "asset_id": UUID(asset_id_str),
                    "project_id": UUID(project_id_str),
                    "chunk_index": chunk_index,
                    "text": text,
                    "metadata": metadata,
                }

            # Build results with scores
            results = []
            for i, faiss_idx in enumerate(indices[0]):
                if faiss_idx in doc_map:
                    # FAISS returns L2 distance (lower is better), convert to similarity score
                    distance = float(distances[0][i])
                    # Convert distance to similarity (1 / (1 + distance))
                    score = 1.0 / (1.0 + distance)

                    doc_data = doc_map[faiss_idx]
                    document = VectorDocument(
                        id=doc_data["id"],
                        asset_id=doc_data["asset_id"],
                        project_id=doc_data["project_id"],
                        chunk_index=doc_data["chunk_index"],
                        text=doc_data["text"],
                        embedding=[],  # Not needed in result
                        metadata=doc_data["metadata"],
                    )

                    results.append(SearchResult(document=document, score=score))

            # Sort by score (highest first) and limit to top_k
            results.sort(key=lambda x: x.score, reverse=True)
            results = results[:top_k]

            return results

        except Exception as e:
            raise VectorStoreError(f"Failed to search: {e}") from e
        finally:
            conn.close()

    def delete_by_asset(self, asset_id: UUID) -> None:
        """Delete all vectors for a specific asset.

        Args:
            asset_id: ID of the asset to delete vectors for

        Raises:
            VectorStoreError: If deletion fails
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            # Get FAISS indices to remove
            cursor.execute("SELECT faiss_index FROM vectors WHERE asset_id = ?", (str(asset_id),))
            rows = cursor.fetchall()
            faiss_indices = [row[0] for row in rows]

            if not faiss_indices:
                conn.close()
                return

            # Delete from SQLite
            cursor.execute("DELETE FROM vectors WHERE asset_id = ?", (str(asset_id),))
            conn.commit()

            # Rebuild FAISS index (FAISS doesn't support efficient deletion)
            # For MVP, we'll rebuild the entire index
            self._rebuild_faiss_index()

        except Exception as e:
            conn.rollback()
            raise VectorStoreError(f"Failed to delete by asset: {e}") from e
        finally:
            conn.close()

    def delete_by_project(self, project_id: UUID) -> None:
        """Delete all vectors for a specific project.

        Args:
            project_id: ID of the project to delete vectors for

        Raises:
            VectorStoreError: If deletion fails
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            # Delete from SQLite
            cursor.execute("DELETE FROM vectors WHERE project_id = ?", (str(project_id),))
            conn.commit()

            # Rebuild FAISS index
            self._rebuild_faiss_index()

        except Exception as e:
            conn.rollback()
            raise VectorStoreError(f"Failed to delete by project: {e}") from e
        finally:
            conn.close()

    def _rebuild_faiss_index(self) -> None:
        """Rebuild FAISS index from SQLite database.

        This is needed because FAISS doesn't support efficient deletion.
        For MVP, this is acceptable. For production, consider using
        a more sophisticated approach or a different vector database.
        """
        # Get all vectors from database
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT embedding, id
            FROM vectors
            ORDER BY id
            """
        )
        rows = cursor.fetchall()
        conn.close()

        # Reinitialize FAISS index
        if self.index_type == "flat":
            self.index = faiss.IndexFlatL2(self.dimension)
        elif self.index_type == "ivf":
            quantizer = faiss.IndexFlatL2(self.dimension)
            nlist = 100
            self.index = faiss.IndexIVFFlat(quantizer, self.dimension, nlist)
            self.index.nprobe = 10

        if not rows:
            # No vectors to rebuild
            self._save_faiss_index()
            return

        # Rebuild vectors array from stored embeddings
        vectors = []
        for embedding_blob, vector_id in rows:
            # Deserialize numpy array from BLOB
            embedding = np.frombuffer(embedding_blob, dtype=np.float32)
            vectors.append(embedding)

        if vectors:
            vectors_array = np.array(vectors, dtype=np.float32)

            # Train IVF index if needed
            if self.index_type == "ivf" and not self.index.is_trained:
                self.index.train(vectors_array)

            # Add vectors to index
            self.index.add(vectors_array)

            # Update faiss_index in database to reflect new indices
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            for i, (embedding_blob, vector_id) in enumerate(rows):
                cursor.execute(
                    "UPDATE vectors SET faiss_index = ? WHERE id = ?",
                    (i, vector_id),
                )
            conn.commit()
            conn.close()

        self._save_faiss_index()

    def get_document_count(self, project_id: Optional[UUID] = None) -> int:
        """Get the total number of documents in the store.

        Args:
            project_id: Optional filter by project ID

        Returns:
            Number of documents
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            if project_id:
                cursor.execute(
                    "SELECT COUNT(*) FROM vectors WHERE project_id = ?",
                    (str(project_id),),
                )
            else:
                cursor.execute("SELECT COUNT(*) FROM vectors")

            count = cursor.fetchone()[0]
            return count

        finally:
            conn.close()

    def clear(self) -> None:
        """Clear all documents from the vector store.

        Raises:
            VectorStoreError: If clearing fails
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            cursor.execute("DELETE FROM vectors")
            conn.commit()

            # Reset FAISS index
            self.index.reset()
            self._save_faiss_index()

        except Exception as e:
            conn.rollback()
            raise VectorStoreError(f"Failed to clear: {e}") from e
        finally:
            conn.close()


# Global vector store instance
_vector_store: VectorStore | None = None


def get_vector_store(
    db_path: str | Path | None = None,
    dimension: int = 384,
    index_type: str = "flat",
) -> VectorStore:
    """Get or create vector store instance.

    Args:
        db_path: Path to SQLite database file. Defaults to 'vector_store.db' in project root.
        dimension: Dimension of embedding vectors
        index_type: Type of FAISS index ("flat" or "ivf")

    Returns:
        VectorStore: Vector store instance (singleton)

    Example:
        ```python
        from backend.core.vector_store import get_vector_store

        store = get_vector_store()
        store.add_documents(documents)
        results = store.search(query_embedding, top_k=5)
        ```
    """
    global _vector_store
    if _vector_store is None:
        if db_path is None:
            # Default to 'vector_store.db' in project root
            from pathlib import Path

            project_root = Path(__file__).resolve().parent.parent.parent
            db_path = project_root / "vector_store.db"

        _vector_store = FAISSSQLiteVectorStore(db_path=db_path, dimension=dimension, index_type=index_type)
    return _vector_store
