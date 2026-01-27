"""
Retrieval Search Module
Performs semantic search with STRICT similarity threshold
Returns ONLY matches above threshold (not just top-K)
"""

import numpy as np
from typing import List, Dict, Optional, Tuple
import logging
from embeddings.embedder import get_embedder
from vector_db.faiss_index import FAISSIndexManager
from vector_db.metadata_store import MetadataStore

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class QuestionRetriever:
    """
    Retrieves similar questions from FAISS index
    CRITICAL: Uses similarity threshold, not just top-K
    """

    def __init__(
        self,
        similarity_threshold: float = 0.50,
        index_dir: str = "data/faiss_indexes",
        metadata_dir: str = "data/metadata"
    ):
        """
        Initialize retriever

        Args:
            similarity_threshold: Minimum cosine similarity (0-1) to return a match
                                 ~0.50 is recommended for questions
        """
        self.similarity_threshold = similarity_threshold
        self.embedder = get_embedder()
        self.faiss_manager = FAISSIndexManager(index_dir)
        self.metadata_store = MetadataStore(metadata_dir)

        logger.info(f"Retriever initialized (threshold: {similarity_threshold})")

    def retrieve(
        self,
        celebrity_name: str,
        user_question: str,
        top_k: int = 20  # Fetch more candidates, then filter by threshold
    ) -> List[Dict]:
        """
        Retrieve questions similar to user query

        CRITICAL BEHAVIOR:
        - Returns ALL questions above similarity_threshold
        - If 1 matches → returns 1
        - If 5 match → returns 5
        - If none match → returns empty list

        Args:
            celebrity_name: Name of the celebrity
            user_question: User's question
            top_k: Number of candidates to fetch (internal, for efficiency)

        Returns:
            List of matching question dicts, sorted by similarity
        """
        logger.info(f"Searching for: '{user_question}'")
        logger.info(f"Celebrity: {celebrity_name}")

        # Step 1: Load index and metadata
        if not self.faiss_manager.load_index(celebrity_name):
            logger.warning(f"No index found for {celebrity_name}")
            return []

        if not self.metadata_store.load_metadata(celebrity_name):
            logger.warning(f"No metadata found for {celebrity_name}")
            return []

        # Check index size
        index_size = self.faiss_manager.get_index_size(celebrity_name)
        if index_size == 0:
            logger.warning(f"Index is empty for {celebrity_name}")
            return []

        logger.info(f"Index size: {index_size} questions")

        # Step 2: Embed user question
        query_embedding = self.embedder.embed_single(user_question)

        # Step 3: Search FAISS index
        # Fetch top_k candidates (more than we need, to ensure we get all above threshold)
        k = min(top_k, index_size)
        distances, indices = self.faiss_manager.search(
            celebrity_name,
            query_embedding,
            k=k
        )

        logger.info(f"FAISS returned {len(distances)} candidates")

        # Step 4: Filter by similarity threshold
        # FAISS IndexFlatIP returns cosine similarity (higher = more similar)
        matches = []

        for similarity, faiss_id in zip(distances, indices):
            if similarity >= self.similarity_threshold:
                # Get metadata
                metadata = self.metadata_store.get_metadata(celebrity_name, int(faiss_id))

                if metadata:
                    metadata['similarity_score'] = float(similarity)
                    matches.append(metadata)

        # Step 5: Sort by similarity (descending)
        matches.sort(key=lambda x: x['similarity_score'], reverse=True)

        logger.info(f"Found {len(matches)} matches above threshold {self.similarity_threshold}")

        if not matches:
            logger.info("No matches above similarity threshold")

        return matches

    def retrieve_with_context(
        self,
        celebrity_name: str,
        user_question: str
    ) -> Dict:
        """
        Retrieve matches with additional context

        Returns:
            Dict containing:
                - matches: List of matching questions
                - count: Number of matches
                - threshold_used: Similarity threshold used
                - max_similarity: Highest similarity score
                - query: Original user question
        """
        matches = self.retrieve(celebrity_name, user_question)

        max_similarity = matches[0]['similarity_score'] if matches else 0.0

        return {
            'matches': matches,
            'count': len(matches),
            'threshold_used': self.similarity_threshold,
            'max_similarity': max_similarity,
            'query': user_question,
            'celebrity': celebrity_name
        }

    def explain_no_results(
        self,
        celebrity_name: str,
        user_question: str
    ) -> Dict:
        """
        Explain why no results were found
        Helpful for debugging and user feedback

        Returns:
            Dict with diagnostic information
        """
        # Get top result even if below threshold
        if not self.faiss_manager.load_index(celebrity_name):
            return {
                'reason': 'no_index',
                'message': f"No data indexed for {celebrity_name}"
            }

        index_size = self.faiss_manager.get_index_size(celebrity_name)
        if index_size == 0:
            return {
                'reason': 'empty_index',
                'message': f"Index exists but is empty for {celebrity_name}"
            }

        # Get closest match (ignore threshold)
        query_embedding = self.embedder.embed_single(user_question)
        distances, indices = self.faiss_manager.search(
            celebrity_name,
            query_embedding,
            k=1
        )

        if len(distances) > 0:
            closest_similarity = float(distances[0])
            closest_metadata = self.metadata_store.get_metadata(celebrity_name, int(indices[0]))

            return {
                'reason': 'below_threshold',
                'message': f"Closest match has similarity {closest_similarity:.3f}, below threshold {self.similarity_threshold}",
                'closest_match': closest_metadata,
                'closest_similarity': closest_similarity,
                'threshold': self.similarity_threshold
            }

        return {
            'reason': 'unknown',
            'message': "Unable to retrieve results"
        }

    def adjust_threshold(self, new_threshold: float):
        """
        Adjust similarity threshold

        Args:
            new_threshold: New threshold value (0-1)
        """
        if not 0 <= new_threshold <= 1:
            raise ValueError("Threshold must be between 0 and 1")

        old_threshold = self.similarity_threshold
        self.similarity_threshold = new_threshold

        logger.info(f"Threshold adjusted: {old_threshold} -> {new_threshold}")

    def get_similar_questions(
        self,
        celebrity_name: str,
        question_text: str,
        exclude_source: Optional[str] = None
    ) -> List[Dict]:
        """
        Find similar questions to a given question
        Useful for deduplication and finding related questions

        Args:
            celebrity_name: Name of the celebrity
            question_text: Question to find similar ones for
            exclude_source: Optional source URL to exclude

        Returns:
            List of similar questions
        """
        matches = self.retrieve(celebrity_name, question_text)

        # Filter out the exact same question and excluded source
        filtered = []
        for match in matches:
            if match['question_text'] != question_text:
                if exclude_source is None or match['source_url'] != exclude_source:
                    filtered.append(match)

        return filtered


if __name__ == "__main__":
    # Test retriever
    retriever = QuestionRetriever(similarity_threshold=0.50)

    celebrity = "Test Celebrity"
    test_question = "What inspired you to become an actor?"

    # This would require an existing index to test
    print(f"Retriever initialized")
    print(f"Similarity threshold: {retriever.similarity_threshold}")
    print(f"Test query: {test_question}")

    # Explain why no results (since we don't have data yet)
    explanation = retriever.explain_no_results(celebrity, test_question)
    print(f"\nExplanation: {explanation}")
