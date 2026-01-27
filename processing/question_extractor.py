"""
Question Extractor
Extracts ONLY interviewer questions from transcripts

🔴 CRITICAL: Uses ONLY rule-based heuristics (NO LLM)
Per system constraints, LLM must NOT be used for extraction
"""

import re
from typing import List, Dict, Optional
import os
from utils.logger import get_logger

logger = get_logger(__name__)


class QuestionExtractor:
    """
    Extracts interviewer questions from interview transcripts
    Step 1: Heuristic filtering (fast, cheap)
    Step 2: LLM refinement (accurate, moderate cost)
    """

    # Interrogative words that typically start questions
    INTERROGATIVE_WORDS = [
        'what', 'why', 'how', 'when', 'where', 'who', 'which',
        'can', 'could', 'would', 'should', 'do', 'does', 'did',
        'is', 'are', 'was', 'were', 'will', 'have', 'has', 'had'
    ]

    def __init__(self, openai_api_key: Optional[str] = None, use_llm: bool = False):
        """
        Initialize question extractor

        🔴 CRITICAL: LLM refinement is DISABLED by design
        Only rule-based heuristics are used per system constraints

        Args:
            openai_api_key: DEPRECATED - Not used
            use_llm: DEPRECATED - Always False (LLM forbidden for extraction)
        """
        # ENFORCE: NO LLM for question extraction
        self.use_llm = False

        if use_llm:
            logger.warning("❌ LLM refinement requested but FORBIDDEN by constraints")
            logger.warning("🔒 Using heuristics-only extraction")

        logger.info("✅ Question extractor initialized (heuristics-only, NO LLM)")

    def extract_questions_heuristic(self, text: str) -> List[str]:
        """
        Extract potential questions using heuristics

        Rules:
        1. Sentence ends with '?'
        2. Sentence starts with OR contains interrogative word
        3. Reasonable length (5-200 words)

        Args:
            text: Transcript text

        Returns:
            List of potential question strings
        """
        # Split into sentences, keeping the delimiter to check for '?'
        # Use lookahead to keep the punctuation with the sentence
        sentences = re.split(r'(?<=[.!?])\s+', text)

        potential_questions = []

        for sentence in sentences:
            sentence = sentence.strip()

            if not sentence:
                continue

            # Check if ends with question mark
            has_question_mark = sentence.endswith('?')

            # Check if starts with interrogative word
            words = sentence.lower().split()
            first_word = words[0] if words else ""
            starts_with_interrogative = first_word in self.INTERROGATIVE_WORDS

            # Also check if contains an interrogative word (for questions like
            # "The West Delhi Cricket Academy, how would you best explain...")
            contains_interrogative = any(word in self.INTERROGATIVE_WORDS for word in words)

            # Check length
            word_count = len(words)
            reasonable_length = 5 <= word_count <= 200

            # Accept if:
            # - Has question mark, OR
            # - Starts with interrogative word, OR
            # - Contains interrogative word AND has question mark
            is_question = (
                has_question_mark or
                starts_with_interrogative or
                (contains_interrogative and has_question_mark)
            )

            if reasonable_length and is_question:
                # Clean up the question
                question = sentence.strip()
                if not question.endswith('?'):
                    question += '?'

                potential_questions.append(question)

        logger.info(f"Heuristic extraction: {len(potential_questions)} potential questions")
        return potential_questions

    def refine_questions_with_llm(
        self,
        potential_questions: List[str],
        batch_size: int = 20
    ) -> List[str]:
        """
        🔴 DISABLED: LLM refinement is FORBIDDEN
        Per system constraints, LLM cannot be used for question extraction

        Args:
            potential_questions: List of potential questions from heuristics
            batch_size: DEPRECATED - Not used

        Returns:
            Original potential_questions (unrefined)
        """
        logger.info("🚫 LLM refinement is DISABLED (heuristics-only mode)")
        logger.info(f"Returning {len(potential_questions)} heuristic-extracted questions")
        return potential_questions

    def extract_from_segments(
        self,
        segments: List[Dict],
        speaker_aware: bool = True
    ) -> List[Dict]:
        """
        Extract questions from timestamped segments
        Better for creating timestamped question links

        Args:
            segments: List of segment dicts with 'text', 'start', 'end', 'speaker' (optional)
            speaker_aware: If True, only extract from 'interviewer' segments

        Returns:
            List of question dicts with text and timestamp
        """
        questions_with_timestamps = []

        for segment in segments:
            text = segment.get("text", "")
            speaker = segment.get("speaker", "unknown")

            # If speaker-aware, only process interviewer segments
            if speaker_aware and speaker != "interviewer" and speaker != "unknown":
                continue

            # Extract questions from this segment
            potential_questions = self.extract_questions_heuristic(text)

            for question in potential_questions:
                questions_with_timestamps.append({
                    "text": question,
                    "timestamp": segment.get("start", 0),
                    "speaker": speaker
                })

        # Refine with LLM if enabled
        if self.use_llm and questions_with_timestamps:
            question_texts = [q["text"] for q in questions_with_timestamps]
            refined_texts = self.refine_questions_with_llm(question_texts)

            # Filter to only keep refined questions
            refined_set = set(refined_texts)
            questions_with_timestamps = [
                q for q in questions_with_timestamps
                if q["text"] in refined_set
            ]

        logger.info(f"Extracted {len(questions_with_timestamps)} questions from segments")
        return questions_with_timestamps

    def extract_from_transcript(
        self,
        transcript_data: Dict,
        use_segments: bool = True
    ) -> List[Dict]:
        """
        Extract questions from full transcript data

        Args:
            transcript_data: Dict from WhisperTranscriber
            use_segments: If True, use segment-based extraction (better for timestamps)

        Returns:
            List of question dicts with text and timestamp
        """
        if use_segments and "segments" in transcript_data:
            # Use segment-based extraction
            segments = transcript_data["segments"]

            # Try to identify speakers if not already done
            if segments and "speaker" not in segments[0]:
                # Simple alternating speaker assumption
                for i, seg in enumerate(segments):
                    seg["speaker"] = "interviewer" if i % 2 == 0 else "celebrity"

            # speaker_aware=False to avoid filtering out questions due to naive alternation
            return self.extract_from_segments(segments, speaker_aware=False)

        else:
            # Fall back to full text extraction
            text = transcript_data.get("text", "")
            potential_questions = self.extract_questions_heuristic(text)

            if self.use_llm:
                refined_questions = self.refine_questions_with_llm(potential_questions)
            else:
                refined_questions = potential_questions

            # Return without timestamps
            return [{"text": q, "timestamp": 0, "speaker": "unknown"} for q in refined_questions]


# Global instance
_extractor = None

def get_question_extractor(use_llm: bool = False) -> QuestionExtractor:
    """
    Get global question extractor instance

    🔴 CRITICAL: use_llm is ALWAYS False (LLM forbidden for extraction)
    """
    global _extractor
    if _extractor is None:
        # ENFORCE: NO LLM allowed
        _extractor = QuestionExtractor(use_llm=False)
    return _extractor


if __name__ == "__main__":
    # Test question extractor
    extractor = get_question_extractor(use_llm=False)  # Disable LLM for testing

    # Test text
    sample_text = """
    So tell me, what inspired you to become an actor?
    Well, I always loved movies. I used to watch them all the time.
    That's fascinating. How do you prepare for a difficult role?
    I do a lot of research. I read about the character.
    What's your favorite movie you've worked on?
    Definitely the last one.
    """

    questions = extractor.extract_questions_heuristic(sample_text)
    print("Extracted questions:")
    for q in questions:
        print(f"  - {q}")
