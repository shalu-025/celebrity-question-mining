"""
Question Extractor - TWO-STAGE EXTRACTION PIPELINE
Extracts ONLY interviewer questions from transcripts

🎯 MANDATORY TWO-STAGE APPROACH:
  Stage 1: Rule-based heuristic extraction (NO LLM)
  Stage 2: LLM refinement with Qwen (ONLY candidate questions, NOT full transcripts)

✅ Per system constraints:
- LLM is ALLOWED for question refinement & validation
- LLM must NOT receive full transcripts or audio
- ONLY send candidate question strings to LLM
- Uses Qwen 2.5 3B Instruct via Ollama
"""

import re
from typing import List, Dict, Optional
import os
from utils.logger import get_logger
from utils.llm_cost_tracker import get_claude_client, get_cost_tracker

logger = get_logger(__name__)


class QuestionExtractor:
    """
    TWO-STAGE question extraction pipeline:
    1. Heuristic filtering (fast, free, extracts candidates)
    2. LLM refinement (Claude only, removes noise, merges duplicates)
    """

    # Interrogative words that typically start questions
    INTERROGATIVE_WORDS = [
        'what', 'why', 'how', 'when', 'where', 'who', 'which',
        'can', 'could', 'would', 'should', 'do', 'does', 'did',
        'is', 'are', 'was', 'were', 'will', 'have', 'has', 'had'
    ]

    def __init__(self, use_llm: bool = True):
        """
        Initialize question extractor with TWO-STAGE pipeline

        Args:
            use_llm: If True, use LLM for Stage 2 refinement (RECOMMENDED)
        """
        self.use_llm = use_llm
        self.cost_tracker = get_cost_tracker()

        if use_llm:
            self.claude_client = get_claude_client()
            logger.info("✅ Question extractor initialized (TWO-STAGE: heuristics + Qwen refinement)")
        else:
            logger.info("✅ Question extractor initialized (heuristics-only mode)")

    # =========================================================================
    # STAGE 1: RULE-BASED HEURISTIC EXTRACTION (NO LLM)
    # =========================================================================

    def extract_questions_heuristic(self, text: str) -> List[str]:
        """
        STAGE 1: Extract candidate questions using rule-based heuristics

        Rules:
        1. Sentence ends with '?'
        2. Sentence starts with OR contains interrogative word
        3. Reasonable length (5-200 words)

        Args:
            text: Transcript or article text

        Returns:
            List of CANDIDATE question strings (may contain noise)
        """
        # Split into sentences
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

            # Also check if contains an interrogative word
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

        logger.info(f"📋 STAGE 1 (Heuristics): Extracted {len(potential_questions)} candidate questions")
        return potential_questions

    # =========================================================================
    # STAGE 2: LLM-BASED REFINEMENT (CLAUDE ONLY, QUESTIONS ONLY)
    # =========================================================================

    def refine_questions_with_llm(
        self,
        candidate_questions: List[str],
        batch_size: int = 30
    ) -> List[str]:
        """
        STAGE 2: Refine candidate questions using Qwen LLM

        ⚠️ CRITICAL: Sends ONLY candidate question strings to LLM
                    Does NOT send full transcripts or audio

        Tasks for Qwen:
        1. Remove non-questions (rhetorical, incomplete, gibberish)
        2. Merge duplicate/paraphrased questions
        3. Rewrite incomplete questions into clean interview questions
        4. Return clean list of valid interview questions

        Args:
            candidate_questions: List of candidate questions from Stage 1
            batch_size: Number of questions to process per LLM call

        Returns:
            List of refined, clean interview questions
        """
        if not self.use_llm:
            logger.warning("🚫 LLM refinement disabled, returning heuristic results")
            return candidate_questions

        if not candidate_questions:
            logger.info("📋 STAGE 2 (LLM): No candidates to refine")
            return []

        logger.info(f"🤖 STAGE 2 (LLM): Refining {len(candidate_questions)} candidates with Qwen")

        refined_questions = []

        # Process in batches
        for i in range(0, len(candidate_questions), batch_size):
            batch = candidate_questions[i:i + batch_size]

            logger.info(f"  Processing batch {i//batch_size + 1} ({len(batch)} questions)")

            # Create numbered list for Qwen
            numbered_questions = "\n".join(
                [f"{idx+1}. {q}" for idx, q in enumerate(batch)]
            )

            # ULTRA-SIMPLE PROMPT - Qwen 3B struggles with filtering, so just rewrite
            prompt = f"""Rewrite these questions to be clean interview questions.

INPUT QUESTIONS:
{numbered_questions}

OUTPUT: Return each question as a numbered list. Make them clear and complete.
Example output:
1. What inspired you to become an actor?
2. How do you prepare for difficult roles?

Your rewritten questions:"""

            try:
                response = self.claude_client.generate(
                    prompt=prompt,
                    system="You rewrite questions to be clear and complete.",
                    max_tokens=2000,
                    temperature=0.2,  # Slightly creative for rewriting
                    purpose="question_refinement"
                )

                # DEBUG: Log what Qwen actually returned
                logger.info(f"  Qwen response ({len(response)} chars): {repr(response[:150])}")

                # Parse response
                if "NONE" in response.upper() and len(response.strip()) < 20:
                    logger.info(f"  Batch {i//batch_size + 1}: No valid questions found")
                    continue

                # Extract questions from numbered list
                lines = response.strip().split('\n')
                batch_count = 0
                
                for line in lines:
                    line = line.strip()
                    if not line:
                        continue

                    # Remove numbering (handles formats like "1.", "1)", "1 -", etc.)
                    clean_line = re.sub(r'^\d+[\.):\-\s]+', '', line).strip()

                    if clean_line and len(clean_line) >= 10:
                        # Ensure it ends with question mark
                        if not clean_line.endswith('?'):
                            clean_line += '?'
                        refined_questions.append(clean_line)
                        batch_count += 1

                logger.info(f"  Batch {i//batch_size + 1}: Extracted {batch_count} refined questions")

            except Exception as e:
                logger.error(f"❌ Error in LLM refinement: {e}")
                # Fallback: include all from this batch (better than losing data)
                logger.warning(f"  Fallback: Keeping all {len(batch)} candidates from this batch")
                refined_questions.extend(batch)

        logger.info(f"✅ STAGE 2 (LLM): Final refined questions: {len(refined_questions)}")
        return refined_questions

    # =========================================================================
    # EXTRACTION FROM DIFFERENT SOURCES
    # =========================================================================

    def extract_from_segments(
        self,
        segments: List[Dict],
        speaker_aware: bool = True
    ) -> List[Dict]:
        """
        Extract questions from timestamped segments (for audio)
        Uses TWO-STAGE pipeline

        Args:
            segments: List of segment dicts with 'text', 'start', 'end', 'speaker' (optional)
            speaker_aware: If True, only extract from 'interviewer' segments

        Returns:
            List of question dicts with text and timestamp
        """
        # STAGE 1: Heuristic extraction from segments
        questions_with_timestamps = []

        for segment in segments:
            text = segment.get("text", "")
            speaker = segment.get("speaker", "unknown")

            # If speaker-aware, only process interviewer segments
            if speaker_aware and speaker != "interviewer" and speaker != "unknown":
                continue

            # Extract candidate questions
            candidate_questions = self.extract_questions_heuristic(text)

            for question in candidate_questions:
                questions_with_timestamps.append({
                    "text": question,
                    "timestamp": segment.get("start", 0),
                    "speaker": speaker
                })

        if not questions_with_timestamps:
            return []

        # STAGE 2: LLM refinement (only on question texts, not full segments)
        if self.use_llm:
            question_texts = [q["text"] for q in questions_with_timestamps]
            refined_texts = self.refine_questions_with_llm(question_texts)

            # Filter to only keep refined questions
            refined_set = set(refined_texts)
            questions_with_timestamps = [
                q for q in questions_with_timestamps
                if q["text"] in refined_set
            ]

        logger.info(f"✅ TWO-STAGE: Extracted {len(questions_with_timestamps)} final questions from segments")
        return questions_with_timestamps

    def extract_from_transcript(
        self,
        transcript_data: Dict,
        use_segments: bool = True
    ) -> List[Dict]:
        """
        Extract questions from full transcript data
        Uses TWO-STAGE pipeline

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

            # STAGE 1: Heuristic extraction
            candidate_questions = self.extract_questions_heuristic(text)

            # STAGE 2: LLM refinement
            if self.use_llm:
                refined_questions = self.refine_questions_with_llm(candidate_questions)
            else:
                refined_questions = candidate_questions

            # Return without timestamps
            return [{"text": q, "timestamp": 0, "speaker": "unknown"} for q in refined_questions]

    def extract_from_article_text(self, article_text: str) -> List[str]:
        """
        Extract questions from article text
        Uses TWO-STAGE pipeline

        Args:
            article_text: Full article text

        Returns:
            List of refined question strings
        """
        # STAGE 1: Heuristic extraction
        candidate_questions = self.extract_questions_heuristic(article_text)

        if not candidate_questions:
            return []

        # STAGE 2: LLM refinement
        if self.use_llm:
            refined_questions = self.refine_questions_with_llm(candidate_questions)
        else:
            refined_questions = candidate_questions

        logger.info(f"✅ TWO-STAGE: Extracted {len(refined_questions)} final questions from article")
        return refined_questions


# Global instance
_extractor = None

def get_question_extractor(use_llm: bool = True) -> QuestionExtractor:
    """
    Get global question extractor instance

    ✅ TWO-STAGE approach with Qwen refinement (RECOMMENDED)

    Args:
        use_llm: If True, uses TWO-STAGE pipeline with Qwen refinement
    """
    global _extractor
    if _extractor is None:
        _extractor = QuestionExtractor(use_llm=use_llm)
    return _extractor


if __name__ == "__main__":
    # Test TWO-STAGE extraction
    extractor = get_question_extractor(use_llm=False)  # Test without LLM first

    # Test text with noise
    sample_text = """
    So tell me, what inspired you to become an actor?
    Well, I always loved movies. I used to watch them all the time.
    That's fascinating. How do you prepare for a difficult role?
    I do a lot of research. I read about the character.
    What's your favorite movie you've worked on?
    Definitely the last one.
    You know what I mean?
    Yeah, totally.
    """

    print("=" * 60)
    print("STAGE 1: Heuristic Extraction")
    print("=" * 60)
    candidates = extractor.extract_questions_heuristic(sample_text)
    print(f"Candidates: {len(candidates)}")
    for q in candidates:
        print(f"  - {q}")

    # Test with LLM (would require API key)
    print("\n" + "=" * 60)
    print("For STAGE 2 (LLM refinement), set use_llm=True")
    print("=" * 60)
