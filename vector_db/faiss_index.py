"""
FAISS Index Manager
Handles vector storage and similarity search using FAISS
FAISS stores ONLY vectors - metadata is handled separately
"""

import faiss
import numpy as np
import os
from typing import List, Tuple, Optional
import pickle
from utils.logger import get_logger

logger = get_logger(__name__)


class FAISSIndexManager:
    """
    Manages FAISS index for semantic similarity search
    Uses IndexFlatIP (Inner Product) for cosine similarity after L2 normalization
    """

    def __init__(self, index_dir: str = "data/faiss_indexes"):
        self.index_dir = index_dir
        os.makedirs(index_dir, exist_ok=True)
        self.indexes = {}  # celebrity_name -> faiss.Index
        self.index_sizes = {}  # celebrity_name -> current_size

    def _get_index_path(self, celebrity_name: str) -> str:
        """Get file path for celebrity's FAISS index"""
        safe_name = celebrity_name.lower().replace(" ", "_")
        return os.path.join(self.index_dir, f"{safe_name}.faiss")

    def _get_size_path(self, celebrity_name: str) -> str:
        """Get file path for index size metadata"""
        safe_name = celebrity_name.lower().replace(" ", "_")
        return os.path.join(self.index_dir, f"{safe_name}_size.pkl")

    def create_index(self, celebrity_name: str, embedding_dim: int = 384):
        """
        Create a new FAISS index for a celebrity

        Args:
            celebrity_name: Name of the celebrity
            embedding_dim: Dimension of embeddings (384 for all-MiniLM-L6-v2)
        """
        logger.info(f"Creating new FAISS index for {celebrity_name}")

        # Use IndexFlatIP (Inner Product) for cosine similarity
        # We'll L2-normalize vectors before adding
        index = faiss.IndexFlatIP(embedding_dim)

        self.indexes[celebrity_name] = index
        self.index_sizes[celebrity_name] = 0

        logger.info(f"Created index with dimension {embedding_dim}")

    def load_index(self, celebrity_name: str) -> bool:
        """
        Load existing FAISS index from disk

        Args:
            celebrity_name: Name of the celebrity

        Returns:
            True if loaded successfully, False otherwise
        """
        index_path = self._get_index_path(celebrity_name)
        size_path = self._get_size_path(celebrity_name)

        if not os.path.exists(index_path):
            logger.warning(f"No index found for {celebrity_name}")
            return False

        try:
            logger.info(f"Loading FAISS index for {celebrity_name}")
            index = faiss.read_index(index_path)
            self.indexes[celebrity_name] = index

            # Load size
            if os.path.exists(size_path):
                with open(size_path, 'rb') as f:
                    self.index_sizes[celebrity_name] = pickle.load(f)
            else:
                self.index_sizes[celebrity_name] = index.ntotal

            logger.info(f"Loaded index with {self.index_sizes[celebrity_name]} vectors")
            return True

        except Exception as e:
            logger.error(f"Error loading index: {e}")
            return False

    def save_index(self, celebrity_name: str):
        """
        Save FAISS index to disk

        Args:
            celebrity_name: Name of the celebrity
        """
        if celebrity_name not in self.indexes:
            logger.error(f"No index found for {celebrity_name}")
            return

        index_path = self._get_index_path(celebrity_name)
        size_path = self._get_size_path(celebrity_name)

        try:
            logger.info(f"Saving FAISS index for {celebrity_name}")
            faiss.write_index(self.indexes[celebrity_name], index_path)

            # Save size
            with open(size_path, 'wb') as f:
                pickle.dump(self.index_sizes[celebrity_name], f)

            logger.info(f"Saved index to {index_path}")

        except Exception as e:
            logger.error(f"Error saving index: {e}")
            raise

    def add_vectors(
        self,
        celebrity_name: str,
        vectors: np.ndarray,
        normalize: bool = True
    ) -> List[int]:
        """
        Add vectors to the FAISS index

        Args:
            celebrity_name: Name of the celebrity
            vectors: Numpy array of shape (n_vectors, embedding_dim)
            normalize: Whether to L2-normalize vectors (required for cosine similarity)

        Returns:
            List of assigned IDs for the vectors
        """
        if celebrity_name not in self.indexes:
            logger.error(f"No index loaded for {celebrity_name}")
            raise ValueError(f"Index not found for {celebrity_name}")

        # Normalize vectors for cosine similarity
        if normalize:
            vectors = vectors / np.linalg.norm(vectors, axis=1, keepdims=True)

        # Get starting ID
        start_id = self.index_sizes.get(celebrity_name, 0)

        # Add to index
        self.indexes[celebrity_name].add(vectors.astype('float32'))

        # Update size
        n_vectors = len(vectors)
        self.index_sizes[celebrity_name] = start_id + n_vectors

        # Generate IDs
        ids = list(range(start_id, start_id + n_vectors))

        logger.info(f"Added {n_vectors} vectors to {celebrity_name}'s index")

        return ids

    def search(
        self,
        celebrity_name: str,
        query_vector: np.ndarray,
        k: int = 5,
        normalize: bool = True
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Search for similar vectors in the index

        Args:
            celebrity_name: Name of the celebrity
            query_vector: Query vector of shape (embedding_dim,)
            k: Number of nearest neighbors to return
            normalize: Whether to L2-normalize query vector

        Returns:
            Tuple of (distances, indices)
            - distances: similarity scores (higher = more similar for IP)
            - indices: FAISS IDs of matching vectors
        """
        if celebrity_name not in self.indexes:
            logger.error(f"No index loaded for {celebrity_name}")
            raise ValueError(f"Index not found for {celebrity_name}")

        # Normalize query for cosine similarity
        if normalize:
            query_vector = query_vector / np.linalg.norm(query_vector)

        # Reshape to (1, embedding_dim) for FAISS
        query_vector = query_vector.reshape(1, -1).astype('float32')

        # Search
        distances, indices = self.indexes[celebrity_name].search(query_vector, k)

        return distances[0], indices[0]

    def get_index_size(self, celebrity_name: str) -> int:
        """Get number of vectors in the index"""
        return self.index_sizes.get(celebrity_name, 0)

    def index_exists(self, celebrity_name: str) -> bool:
        """Check if index exists on disk"""
        return os.path.exists(self._get_index_path(celebrity_name))

    def delete_index(self, celebrity_name: str):
        """Delete index from memory and disk"""
        if celebrity_name in self.indexes:
            del self.indexes[celebrity_name]
            del self.index_sizes[celebrity_name]

        index_path = self._get_index_path(celebrity_name)
        size_path = self._get_size_path(celebrity_name)

        if os.path.exists(index_path):
            os.remove(index_path)
        if os.path.exists(size_path):
            os.remove(size_path)

        logger.info(f"Deleted index for {celebrity_name}")


if __name__ == "__main__":
    # Test FAISS index
    manager = FAISSIndexManager(index_dir="test_faiss")

    # Create index
    celebrity = "Test Celebrity"
    manager.create_index(celebrity, embedding_dim=384)

    # Add some random vectors
    test_vectors = np.random.randn(10, 384).astype('float32')
    ids = manager.add_vectors(celebrity, test_vectors)
    print(f"Added vectors with IDs: {ids}")

    # Save index
    manager.save_index(celebrity)

    # Search
    query = np.random.randn(384).astype('float32')
    distances, indices = manager.search(celebrity, query, k=3)
    print(f"\nSearch results:")
    print(f"Distances: {distances}")
    print(f"Indices: {indices}")

    # Cleanup
    manager.delete_index(celebrity)
    os.rmdir("test_faiss")
