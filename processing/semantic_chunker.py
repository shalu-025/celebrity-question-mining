"""
Semantic Chunker
Groups similar content using embedding-based similarity
Reduces redundancy and improves organization
"""

import numpy as np
from typing import List, Dict, Optional
import logging
from sklearn.cluster import AgglomerativeClustering
from embeddings.embedder import get_embedder

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SemanticChunker:
    """
    Groups questions semantically to reduce redundancy
    Uses embedding similarity to cluster similar questions
    """

    def __init__(self, similarity_threshold: float = 0.85):
        """
        Initialize semantic chunker

        Args:
            similarity_threshold: Cosine similarity threshold for merging (0-1)
                                 Higher = more strict (fewer merges)
        """
        self.similarity_threshold = similarity_threshold
        self.embedder = get_embedder()
        logger.info(f"Semantic chunker initialized (threshold: {similarity_threshold})")

    def deduplicate_questions(
        self,
        questions: List[Dict],
        keep_all_sources: bool = True
    ) -> List[Dict]:
        """
        Remove duplicate or highly similar questions
        Keeps unique questions and merges sources

        Args:
            questions: List of question dicts with 'text', 'timestamp', source info
            keep_all_sources: If True, merge sources for duplicate questions

        Returns:
            List of deduplicated questions with merged sources
        """
        if not questions:
            return []

        if len(questions) == 1:
            return questions

        logger.info(f"Deduplicating {len(questions)} questions")

        # Extract question texts
        texts = [q["text"] for q in questions]

        # Get embeddings
        embeddings = self.embedder.embed_batch(texts)

        # Compute pairwise similarity matrix
        similarity_matrix = np.dot(embeddings, embeddings.T)

        # Find groups of similar questions
        groups = []
        used = set()

        for i in range(len(questions)):
            if i in used:
                continue

            # Find all questions similar to this one
            group = [i]
            for j in range(i + 1, len(questions)):
                if j not in used and similarity_matrix[i, j] >= self.similarity_threshold:
                    group.append(j)
                    used.add(j)

            groups.append(group)
            used.add(i)

        # Create deduplicated list
        deduplicated = []

        for group in groups:
            # Take the first question as representative
            representative = questions[group[0]].copy()

            if keep_all_sources and len(group) > 1:
                # Merge sources from all similar questions
                all_sources = []
                for idx in group:
                    source_info = {
                        "source_url": questions[idx].get("source_url"),
                        "source_title": questions[idx].get("source_title"),
                        "timestamp": questions[idx].get("timestamp"),
                        "date": questions[idx].get("date")
                    }
                    all_sources.append(source_info)

                representative["all_sources"] = all_sources
                representative["duplicate_count"] = len(group)

            deduplicated.append(representative)

        logger.info(f"Deduplicated to {len(deduplicated)} unique questions")
        return deduplicated

    def cluster_questions(
        self,
        questions: List[Dict],
        n_clusters: Optional[int] = None
    ) -> Dict[int, List[Dict]]:
        """
        Cluster questions into semantic groups
        Useful for understanding themes in interviews

        Args:
            questions: List of question dicts
            n_clusters: Number of clusters (if None, auto-determined)

        Returns:
            Dict mapping cluster_id -> list of questions
        """
        if not questions or len(questions) < 2:
            return {0: questions}

        logger.info(f"Clustering {len(questions)} questions")

        # Extract texts and get embeddings
        texts = [q["text"] for q in questions]
        embeddings = self.embedder.embed_batch(texts)

        # Determine number of clusters
        if n_clusters is None:
            # Auto-determine: roughly sqrt(n) clusters
            n_clusters = max(2, int(np.sqrt(len(questions))))

        # Perform clustering
        clustering = AgglomerativeClustering(
            n_clusters=min(n_clusters, len(questions)),
            metric='cosine',
            linkage='average'
        )

        labels = clustering.fit_predict(embeddings)

        # Group questions by cluster
        clusters = {}
        for idx, label in enumerate(labels):
            if label not in clusters:
                clusters[label] = []
            clusters[label].append(questions[idx])

        logger.info(f"Created {len(clusters)} clusters")
        return clusters

    def merge_similar_questions(
        self,
        questions: List[str],
        merge_threshold: float = 0.90
    ) -> Dict[str, List[str]]:
        """
        Merge very similar question phrasings
        Returns representative question -> list of variants

        Args:
            questions: List of question strings
            merge_threshold: Similarity threshold for merging

        Returns:
            Dict mapping representative question -> list of similar variants
        """
        if not questions:
            return {}

        # Get embeddings
        embeddings = self.embedder.embed_batch(questions)

        # Compute similarity matrix
        similarity_matrix = np.dot(embeddings, embeddings.T)

        # Find groups
        merged = {}
        used = set()

        for i in range(len(questions)):
            if i in used:
                continue

            # Find similar questions
            variants = [questions[i]]
            for j in range(i + 1, len(questions)):
                if j not in used and similarity_matrix[i, j] >= merge_threshold:
                    variants.append(questions[j])
                    used.add(j)

            # Use first as representative
            merged[questions[i]] = variants
            used.add(i)

        logger.info(f"Merged {len(questions)} questions into {len(merged)} groups")
        return merged

    def filter_by_semantic_distance(
        self,
        questions: List[Dict],
        min_distance: float = 0.15
    ) -> List[Dict]:
        """
        Filter questions to ensure minimum semantic distance
        Removes questions that are too similar to already-selected ones

        Args:
            questions: List of question dicts
            min_distance: Minimum cosine distance (1 - similarity)

        Returns:
            Filtered list of questions
        """
        if not questions or len(questions) <= 1:
            return questions

        logger.info(f"Filtering {len(questions)} questions by semantic distance")

        # Get embeddings
        texts = [q["text"] for q in questions]
        embeddings = self.embedder.embed_batch(texts)

        # Greedily select diverse questions
        selected = [0]  # Always keep first
        selected_embeddings = [embeddings[0]]

        for i in range(1, len(questions)):
            # Compute similarity to all selected
            similarities = [
                np.dot(embeddings[i], emb)
                for emb in selected_embeddings
            ]

            # Keep if sufficiently different from all selected
            max_similarity = max(similarities)
            if (1 - max_similarity) >= min_distance:
                selected.append(i)
                selected_embeddings.append(embeddings[i])

        filtered = [questions[i] for i in selected]

        logger.info(f"Filtered to {len(filtered)} diverse questions")
        return filtered


# Global instance
_chunker = None

def get_semantic_chunker(similarity_threshold: float = 0.85) -> SemanticChunker:
    """Get global semantic chunker instance"""
    global _chunker
    if _chunker is None:
        _chunker = SemanticChunker(similarity_threshold)
    return _chunker


if __name__ == "__main__":
    # Test semantic chunker
    chunker = get_semantic_chunker()

    # Test questions with duplicates
    test_questions = [
        {"text": "What inspired you to become an actor?", "source_url": "url1"},
        {"text": "Why did you choose acting as a career?", "source_url": "url2"},  # Similar to above
        {"text": "How do you prepare for a role?", "source_url": "url3"},
        {"text": "What's your preparation process for roles?", "source_url": "url4"},  # Similar to above
        {"text": "What's your favorite movie?", "source_url": "url5"},
    ]

    # Deduplicate
    deduplicated = chunker.deduplicate_questions(test_questions)

    print(f"Original: {len(test_questions)} questions")
    print(f"Deduplicated: {len(deduplicated)} questions")

    for q in deduplicated:
        print(f"\n- {q['text']}")
        if 'duplicate_count' in q:
            print(f"  (merged {q['duplicate_count']} similar questions)")
