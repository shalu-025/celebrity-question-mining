"""
OpenAI Whisper API Transcriber
Cloud-based transcription using OpenAI's Whisper API
More stable alternative to local Whisper, especially on Mac with Python 3.13

🔴🔴🔴 CRITICAL: THIS MODULE IS DISABLED 🔴🔴🔴
Per system constraints, cloud transcription is FORBIDDEN.
Use transcription/whisper_transcriber.py (local Whisper) instead.
"""

raise RuntimeError(
    "❌ CONSTRAINT VIOLATION: OpenAI Whisper API is FORBIDDEN\n"
    "This system uses ONLY local Whisper transcription.\n"
    "DO NOT import or use this module.\n"
    "Use: from transcription.whisper_transcriber import get_transcriber"
)

from openai import OpenAI
import os
from typing import Dict, Optional
import logging
from pydub import AudioSegment

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class OpenAITranscriber:
    """
    Transcribes audio using OpenAI's Whisper API (cloud)
    More stable than local Whisper, especially on Mac
    """

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize OpenAI transcriber

        Args:
            api_key: OpenAI API key (defaults to OPENAI_API_KEY env var)
        """
        api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OpenAI API key required")

        self.client = OpenAI(api_key=api_key)
        logger.info("OpenAI Whisper API transcriber initialized")

    def _compress_audio_if_needed(self, audio_path: str, max_size_mb: float = 23.0) -> str:
        """
        Compress audio file if it exceeds the size limit (OpenAI limit is 25MB)

        Args:
            audio_path: Path to audio file
            max_size_mb: Maximum file size in MB (default 23MB for safety margin)

        Returns:
            Path to compressed file (or original if no compression needed)
        """
        file_size_mb = os.path.getsize(audio_path) / (1024 * 1024)

        if file_size_mb <= max_size_mb:
            return audio_path

        logger.info(f"Compressing audio from {file_size_mb:.2f}MB to fit under {max_size_mb}MB")

        # Load audio
        audio = AudioSegment.from_file(audio_path)

        # Get base path without extension for compressed file
        base_path = os.path.splitext(audio_path)[0]
        compressed_path = f"{base_path}_compressed.mp3"

        # Try progressively lower bitrates until file is small enough
        bitrates = ["64k", "48k", "32k"]

        for bitrate in bitrates:
            audio.export(
                compressed_path,
                format="mp3",
                bitrate=bitrate,
                parameters=["-ar", "16000", "-ac", "1"]  # 16kHz mono
            )

            compressed_size_mb = os.path.getsize(compressed_path) / (1024 * 1024)
            logger.info(f"Compressed with {bitrate} bitrate to {compressed_size_mb:.2f}MB")

            if compressed_size_mb <= max_size_mb:
                return compressed_path

        # If still too large, warn but return the most compressed version
        if compressed_size_mb > max_size_mb:
            logger.warning(f"Audio still {compressed_size_mb:.2f}MB after max compression. May fail API upload.")

        return compressed_path

    def transcribe_audio(
        self,
        audio_path: str,
        language: str = "en"
    ) -> Dict:
        """
        Transcribe audio file using OpenAI Whisper API

        Args:
            audio_path: Path to audio file
            language: Language code (default: 'en' for English)

        Returns:
            Dict containing:
                - text: Full transcript
                - segments: List of segments (placeholder for compatibility)
        """
        if not os.path.exists(audio_path):
            raise FileNotFoundError(f"Audio file not found: {audio_path}")

        logger.info(f"Transcribing audio with OpenAI API: {audio_path}")

        try:
            # Compress if needed
            transcribe_path = self._compress_audio_if_needed(audio_path)

            with open(transcribe_path, "rb") as audio_file:
                response = self.client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_file,
                    language=language,
                    response_format="verbose_json",
                    timestamp_granularities=["segment"]
                )

            # Clean up compressed file if created
            if transcribe_path != audio_path and os.path.exists(transcribe_path):
                os.remove(transcribe_path)

            # Extract segments from response
            segments = []
            if hasattr(response, 'segments') and response.segments:
                for segment in response.segments:
                    segments.append({
                        "start": getattr(segment, 'start', 0),
                        "end": getattr(segment, 'end', 0),
                        "text": getattr(segment, 'text', '').strip()
                    })

            transcript_data = {
                "text": response.text.strip(),
                "segments": segments,
                "language": language
            }

            logger.info(f"Transcription complete. Text length: {len(response.text)} chars")

            return transcript_data

        except Exception as e:
            logger.error(f"Error transcribing audio with OpenAI API: {e}")
            raise

    def transcribe_with_chunking(
        self,
        audio_path: str,
        chunk_length_ms: int = 300000,
        language: str = "en"
    ) -> Dict:
        """
        For compatibility with WhisperTranscriber interface
        OpenAI API handles chunking internally, so this just calls transcribe_audio
        """
        return self.transcribe_audio(audio_path, language)

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
            separator = "&" if "?" in base_url else "?"
            return f"{base_url}{separator}t={int(timestamp_seconds)}"
        else:
            return f"{base_url}#t={int(timestamp_seconds)}"


# Global instance
_openai_transcriber = None

def get_openai_transcriber() -> OpenAITranscriber:
    """Get global OpenAI transcriber instance (singleton)"""
    global _openai_transcriber
    if _openai_transcriber is None:
        _openai_transcriber = OpenAITranscriber()
    return _openai_transcriber


if __name__ == "__main__":
    transcriber = get_openai_transcriber()
    print("OpenAI Whisper API transcriber initialized successfully")
