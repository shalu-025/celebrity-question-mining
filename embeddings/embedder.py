"""
Embedder Module
Handles text-to-vector conversion using sentence-transformers
Uses: all-MiniLM-L6-v2 model (lightweight, fast, good for semantic similarity)
"""

from sentence_transformers import SentenceTransformer
import numpy as np
from typing import List, Union
from utils.logger import get_logger

logger = get_logger(__name__)


class QuestionEmbedder:
    """
    Singleton embedder for converting questions to semantic vectors
    MUST use same model for storage and retrieval
    """

    _instance = None
    _model = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(QuestionEmbedder, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        if self._model is None:
            logger.info("Loading sentence-transformer model: all-MiniLM-L6-v2")
            self._model = SentenceTransformer('all-MiniLM-L6-v2')
            logger.info(f"Model loaded. Embedding dimension: {self.embedding_dim}")

    @property
    def embedding_dim(self) -> int:
        """Return embedding dimension (384 for all-MiniLM-L6-v2)"""
        return self._model.get_sentence_embedding_dimension()

    def embed_single(self, text: str) -> np.ndarray:
        """
        Embed a single text string

        Args:
            text: Text to embed

        Returns:
            numpy array of shape (embedding_dim,)
        """
        if not text or not text.strip():
            raise ValueError("Cannot embed empty text")

        embedding = self._model.encode(text, convert_to_numpy=True)
        return embedding

    def embed_batch(self, texts: List[str], show_progress: bool = False) -> np.ndarray:
        """
        Embed multiple texts in batch (more efficient)

        Args:
            texts: List of text strings
            show_progress: Show progress bar

        Returns:
            numpy array of shape (len(texts), embedding_dim)
        """
        if not texts:
            raise ValueError("Cannot embed empty list")

        # Filter out empty texts
        valid_texts = [t for t in texts if t and t.strip()]
        if len(valid_texts) != len(texts):
            logger.warning(f"Filtered {len(texts) - len(valid_texts)} empty texts")

        embeddings = self._model.encode(
            valid_texts,
            convert_to_numpy=True,
            show_progress_bar=show_progress
        )
        return embeddings

    def compute_similarity(self, text1: str, text2: str) -> float:
        """
        Compute cosine similarity between two texts

        Args:
            text1: First text
            text2: Second text

        Returns:
            Similarity score (0 to 1)
        """
        emb1 = self.embed_single(text1)
        emb2 = self.embed_single(text2)

        # Cosine similarity
        similarity = np.dot(emb1, emb2) / (np.linalg.norm(emb1) * np.linalg.norm(emb2))
        return float(similarity)


# Global singleton instance
_embedder_instance = None

def get_embedder() -> QuestionEmbedder:
    """
    Get the global embedder instance (singleton pattern)
    Ensures same model is used throughout the system
    """
    global _embedder_instance
    if _embedder_instance is None:
        _embedder_instance = QuestionEmbedder()
    return _embedder_instance


if __name__ == "__main__":
    # Test the embedder
    embedder = get_embedder()

    # Test single embedding
    test_question = "What inspired you to become an actor?"
    embedding = embedder.embed_single(test_question)
    print(f"Single embedding shape: {embedding.shape}")
    print(f"First 5 values: {embedding[:5]}")

    # Test batch embedding
    test_questions = [
        "What inspired you to become an actor?",
        "How do you prepare for a role?",
        "What's your favorite movie you've worked on?"
    ]
    embeddings = embedder.embed_batch(test_questions)
    print(f"\nBatch embeddings shape: {embeddings.shape}")

    # Test similarity
    q1 = "What inspired you to become an actor?"
    q2 = "Why did you choose acting as a career?"
    q3 = "What's your favorite food?"

    sim_12 = embedder.compute_similarity(q1, q2)
    sim_13 = embedder.compute_similarity(q1, q3)

    print(f"\nSimilarity between related questions: {sim_12:.4f}")
    print(f"Similarity between unrelated questions: {sim_13:.4f}")
