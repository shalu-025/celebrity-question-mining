"""
Whisper Transcriber
Handles audio transcription using Faster-Whisper (local, open-source)
Faster-Whisper is more stable than openai-whisper, especially on Mac
Supports long audio via chunking

🔴 CRITICAL: Uses ONLY local Whisper (NO cloud API)
Uses faster-whisper for stability on Mac with Python 3.13+
"""

from faster_whisper import WhisperModel
import os
from typing import Dict, List, Optional
import logging
from pydub import AudioSegment

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class WhisperTranscriber:
    """
    Transcribes audio using Faster-Whisper model (local)
    More stable than openai-whisper, especially on Mac
    """

    def __init__(self, model_size: str = "base"):
        """
        Initialize Faster-Whisper transcriber

        Args:
            model_size: Whisper model size - 'tiny', 'base', 'small', 'medium', 'large'
                       'base' is recommended for speed/accuracy balance
        """
        logger.info(f"🔒 Loading LOCAL Faster-Whisper model: {model_size}")

        # Use CPU with int8 for better stability on Mac
        self.model = WhisperModel(
            model_size,
            device="cpu",
            compute_type="int8"  # More stable than float16/float32 on CPU
        )

        logger.info("✅ Whisper model loaded successfully (Faster-Whisper, local)")

    def transcribe_audio(
        self,
        audio_path: str,
        language: str = "en"
    ) -> Dict:
        """
        Transcribe audio file with timestamps

        Args:
            audio_path: Path to audio file
            language: Language code (default: 'en' for English)

        Returns:
            Dict containing:
                - text: Full transcript
                - segments: List of segments with timestamps and text
                - language: Detected/specified language
        """
        if not os.path.exists(audio_path):
            raise FileNotFoundError(f"Audio file not found: {audio_path}")

        logger.info(f"Transcribing audio: {audio_path}")

        try:
            # Transcribe with faster-whisper
            # Returns generator of segments
            segments_generator, info = self.model.transcribe(
                audio_path,
                language=language,
                beam_size=5,
                vad_filter=True,  # Voice activity detection
                word_timestamps=False  # Disable for stability
            )

            # Convert generator to list and extract data
            segments = []
            full_text = []

            for segment in segments_generator:
                segments.append({
                    "start": segment.start,
                    "end": segment.end,
                    "text": segment.text.strip()
                })
                full_text.append(segment.text.strip())

            transcript_data = {
                "text": " ".join(full_text),
                "segments": segments,
                "language": info.language
            }

            logger.info(
                f"✅ Transcription complete. "
                f"Duration: {segments[-1]['end']:.2f}s, "
                f"Segments: {len(segments)}"
                if segments else "No segments"
            )

            return transcript_data

        except Exception as e:
            logger.error(f"❌ Error transcribing audio: {e}")
            raise

    def transcribe_with_chunking(
        self,
        audio_path: str,
        chunk_length_ms: int = 300000,  # 5 minutes
        language: str = "en"
    ) -> Dict:
        """
        Transcribe long audio by splitting into chunks
        Useful for very long interviews/podcasts (>30 minutes)

        Args:
            audio_path: Path to audio file
            chunk_length_ms: Length of each chunk in milliseconds
            language: Language code

        Returns:
            Dict containing combined transcript and segments
        """
        logger.info(f"Transcribing long audio with chunking: {audio_path}")

        # Load audio
        audio = AudioSegment.from_file(audio_path)
        duration_ms = len(audio)

        logger.info(f"Audio duration: {duration_ms / 1000:.2f}s")

        # If audio is short enough, use regular transcription
        if duration_ms <= chunk_length_ms:
            return self.transcribe_audio(audio_path, language)

        # Split into chunks
        all_segments = []
        full_text = []

        num_chunks = (duration_ms // chunk_length_ms) + 1

        for i in range(num_chunks):
            start_ms = i * chunk_length_ms
            end_ms = min((i + 1) * chunk_length_ms, duration_ms)

            logger.info(f"Processing chunk {i+1}/{num_chunks} ({start_ms/1000:.2f}s - {end_ms/1000:.2f}s)")

            # Extract chunk
            chunk = audio[start_ms:end_ms]

            # Save temporary chunk
            temp_path = f"{audio_path}_chunk_{i}.wav"
            chunk.export(temp_path, format="wav")

            try:
                # Transcribe chunk
                result = self.transcribe_audio(temp_path, language)

                # Adjust timestamps to absolute time
                for segment in result["segments"]:
                    segment["start"] += start_ms / 1000
                    segment["end"] += start_ms / 1000
                    all_segments.append(segment)

                full_text.append(result["text"])

            finally:
                # Clean up temp file
                if os.path.exists(temp_path):
                    os.remove(temp_path)

        return {
            "text": " ".join(full_text),
            "segments": all_segments,
            "language": language
        }

    def extract_speaker_segments(
        self,
        transcript_data: Dict,
        interview_format: bool = True
    ) -> List[Dict]:
        """
        Attempt to identify speaker changes in transcript
        Simple heuristic-based approach

        Args:
            transcript_data: Transcript data from transcribe_audio()
            interview_format: If True, assumes alternating speakers

        Returns:
            List of segments with speaker labels
        """
        segments = transcript_data.get("segments", [])

        if not segments:
            return []

        labeled_segments = []

        if interview_format:
            # Simple alternating speaker assumption
            # Interviewer typically starts
            for i, segment in enumerate(segments):
                speaker = "interviewer" if i % 2 == 0 else "celebrity"
                labeled_segments.append({
                    **segment,
                    "speaker": speaker
                })
        else:
            # All segments labeled as unknown
            for segment in segments:
                labeled_segments.append({
                    **segment,
                    "speaker": "unknown"
                })

        return labeled_segments

    def get_timestamped_url(
        self,
        base_url: str,
        timestamp_seconds: float,
        url_type: str = "youtube"
    ) -> str:
        """
        Generate timestamped URL for a source

        Args:
            base_url: Base URL of the video/podcast
            timestamp_seconds: Timestamp in seconds
            url_type: 'youtube' or 'other'

        Returns:
            Timestamped URL
        """
        if url_type == "youtube":
            # YouTube timestamp format: ?t=123
            separator = "&" if "?" in base_url else "?"
            return f"{base_url}{separator}t={int(timestamp_seconds)}"
        else:
            # Generic timestamp
            return f"{base_url}#t={int(timestamp_seconds)}"


# Global instance
_transcriber = None

def get_transcriber(model_size: str = "small") -> WhisperTranscriber:
    """
    Get global transcriber instance (singleton)

    🔴 CRITICAL: ALWAYS uses local Whisper (NO cloud API)
    Uses Faster-Whisper for stability on Mac

    Args:
        model_size: Whisper model size ('tiny', 'base', 'small', 'medium', 'large')

    Returns:
        Local WhisperTranscriber instance
    """
    global _transcriber

    if _transcriber is None:
        # ENFORCE: ONLY local Whisper allowed
        logger.info(f"🔒 Using LOCAL Faster-Whisper transcriber (model: {model_size})")
        logger.info("🚫 Cloud transcription is DISABLED by design")
        _transcriber = WhisperTranscriber(model_size)

    return _transcriber


if __name__ == "__main__":
    # Test transcriber
    transcriber = get_transcriber("base")

    # Create a test audio file (you would need an actual audio file to test)
    # This is just to show the interface
    print("✅ Faster-Whisper transcriber initialized successfully")
    print(f"Available methods:")
    print("- transcribe_audio(audio_path, language='en')")
    print("- transcribe_with_chunking(audio_path, chunk_length_ms=300000)")
    print("- extract_speaker_segments(transcript_data, interview_format=True)")
    print("- get_timestamped_url(base_url, timestamp_seconds, url_type='youtube')")
