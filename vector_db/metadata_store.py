"""
Metadata Store
Handles mapping between FAISS IDs and question metadata
FAISS only stores vectors - this stores all the context
"""

import json
import os
from typing import List, Dict, Optional
from datetime import datetime
from utils.logger import get_logger

logger = get_logger(__name__)


class MetadataStore:
    """
    Stores metadata for each question indexed in FAISS
    Maps FAISS ID -> Question Metadata
    """

    def __init__(self, storage_dir: str = "data/metadata"):
        self.storage_dir = storage_dir
        os.makedirs(storage_dir, exist_ok=True)
        self.metadata = {}  # celebrity_name -> {faiss_id: metadata}

    def _get_metadata_path(self, celebrity_name: str) -> str:
        """Get file path for celebrity's metadata"""
        safe_name = celebrity_name.lower().replace(" ", "_")
        return os.path.join(self.storage_dir, f"{safe_name}_metadata.json")

    def load_metadata(self, celebrity_name: str) -> bool:
        """
        Load metadata from disk

        Args:
            celebrity_name: Name of the celebrity

        Returns:
            True if loaded successfully, False otherwise
        """
        metadata_path = self._get_metadata_path(celebrity_name)

        if not os.path.exists(metadata_path):
            logger.warning(f"No metadata found for {celebrity_name}")
            self.metadata[celebrity_name] = {}
            return False

        try:
            logger.info(f"Loading metadata for {celebrity_name}")
            with open(metadata_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # Convert string keys back to integers
            self.metadata[celebrity_name] = {int(k): v for k, v in data.items()}

            logger.info(f"Loaded metadata for {len(self.metadata[celebrity_name])} questions")
            return True

        except Exception as e:
            logger.error(f"Error loading metadata: {e}")
            self.metadata[celebrity_name] = {}
            return False

    def save_metadata(self, celebrity_name: str):
        """
        Save metadata to disk

        Args:
            celebrity_name: Name of the celebrity
        """
        if celebrity_name not in self.metadata:
            logger.error(f"No metadata found for {celebrity_name}")
            return

        metadata_path = self._get_metadata_path(celebrity_name)

        try:
            logger.info(f"Saving metadata for {celebrity_name}")

            # Convert int keys to strings for JSON
            data = {str(k): v for k, v in self.metadata[celebrity_name].items()}

            with open(metadata_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

            logger.info(f"Saved metadata to {metadata_path}")

        except Exception as e:
            logger.error(f"Error saving metadata: {e}")
            raise

    def add_metadata(
        self,
        celebrity_name: str,
        faiss_ids: List[int],
        questions: List[str],
        sources: List[Dict]
    ):
        """
        Add metadata for new questions

        Args:
            celebrity_name: Name of the celebrity
            faiss_ids: List of FAISS IDs
            questions: List of question texts
            sources: List of source metadata dicts containing:
                - source_type: 'youtube', 'podcast', or 'article'
                - source_url: URL to the source
                - source_title: Title of the source
                - timestamp: Optional timestamp in the source
                - date: Date of the interview/article
        """
        if celebrity_name not in self.metadata:
            self.metadata[celebrity_name] = {}

        if len(faiss_ids) != len(questions) or len(faiss_ids) != len(sources):
            raise ValueError("Length mismatch: faiss_ids, questions, and sources must have same length")

        for faiss_id, question, source in zip(faiss_ids, questions, sources):
            metadata = {
                "celebrity_name": celebrity_name,
                "question_text": question,
                "source_type": source.get("source_type"),
                "source_url": source.get("source_url"),
                "source_title": source.get("source_title"),
                "timestamp": source.get("timestamp"),
                "date": source.get("date"),
                "indexed_at": datetime.utcnow().isoformat()
            }

            self.metadata[celebrity_name][faiss_id] = metadata

        logger.info(f"Added metadata for {len(faiss_ids)} questions")

    def get_metadata(self, celebrity_name: str, faiss_id: int) -> Optional[Dict]:
        """
        Get metadata for a specific FAISS ID

        Args:
            celebrity_name: Name of the celebrity
            faiss_id: FAISS ID

        Returns:
            Metadata dict or None if not found
        """
        if celebrity_name not in self.metadata:
            return None

        return self.metadata[celebrity_name].get(faiss_id)

    def get_batch_metadata(
        self,
        celebrity_name: str,
        faiss_ids: List[int]
    ) -> List[Optional[Dict]]:
        """
        Get metadata for multiple FAISS IDs

        Args:
            celebrity_name: Name of the celebrity
            faiss_ids: List of FAISS IDs

        Returns:
            List of metadata dicts (None for missing IDs)
        """
        if celebrity_name not in self.metadata:
            return [None] * len(faiss_ids)

        return [
            self.metadata[celebrity_name].get(faiss_id)
            for faiss_id in faiss_ids
        ]

    def get_all_metadata(self, celebrity_name: str) -> Dict[int, Dict]:
        """Get all metadata for a celebrity"""
        return self.metadata.get(celebrity_name, {})

    def delete_metadata(self, celebrity_name: str):
        """Delete metadata from memory and disk"""
        if celebrity_name in self.metadata:
            del self.metadata[celebrity_name]

        metadata_path = self._get_metadata_path(celebrity_name)
        if os.path.exists(metadata_path):
            os.remove(metadata_path)

        logger.info(f"Deleted metadata for {celebrity_name}")

    def metadata_exists(self, celebrity_name: str) -> bool:
        """Check if metadata exists on disk"""
        return os.path.exists(self._get_metadata_path(celebrity_name))

    def get_question_count(self, celebrity_name: str) -> int:
        """Get number of questions indexed for a celebrity"""
        if celebrity_name not in self.metadata:
            return 0
        return len(self.metadata[celebrity_name])

    def get_sources_summary(self, celebrity_name: str) -> Dict[str, int]:
        """
        Get summary of source types for a celebrity

        Returns:
            Dict mapping source_type to count
        """
        if celebrity_name not in self.metadata:
            return {}

        summary = {}
        for metadata in self.metadata[celebrity_name].values():
            source_type = metadata.get("source_type", "unknown")
            summary[source_type] = summary.get(source_type, 0) + 1

        return summary


if __name__ == "__main__":
    # Test metadata store
    store = MetadataStore(storage_dir="test_metadata")

    celebrity = "Test Celebrity"

    # Add some test metadata
    faiss_ids = [0, 1, 2]
    questions = [
        "What inspired you to become an actor?",
        "How do you prepare for a role?",
        "What's your favorite movie?"
    ]
    sources = [
        {
            "source_type": "youtube",
            "source_url": "https://youtube.com/watch?v=test1",
            "source_title": "Interview 1",
            "timestamp": "00:05:30",
            "date": "2024-01-15"
        },
        {
            "source_type": "podcast",
            "source_url": "https://podcast.com/episode1",
            "source_title": "Podcast Episode 1",
            "timestamp": None,
            "date": "2024-02-20"
        },
        {
            "source_type": "article",
            "source_url": "https://magazine.com/interview",
            "source_title": "Magazine Interview",
            "timestamp": None,
            "date": "2024-03-10"
        }
    ]

    store.add_metadata(celebrity, faiss_ids, questions, sources)

    # Save
    store.save_metadata(celebrity)

    # Test retrieval
    metadata = store.get_metadata(celebrity, 1)
    print("Metadata for ID 1:", metadata)

    # Test summary
    summary = store.get_sources_summary(celebrity)
    print("\nSources summary:", summary)

    # Cleanup
    store.delete_metadata(celebrity)
    os.rmdir("test_metadata")
